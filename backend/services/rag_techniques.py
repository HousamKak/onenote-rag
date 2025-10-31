"""
Advanced RAG techniques implementation.
"""
import logging
from typing import List, Dict, Any
from operator import itemgetter

from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain.load import dumps, loads

from models.rag_config import (
    MultiQueryConfig,
    RAGFusionConfig,
    DecompositionConfig,
    StepBackConfig,
    HyDEConfig,
)

logger = logging.getLogger(__name__)


class RAGTechniques:
    """Implementation of advanced RAG techniques."""

    def __init__(self, llm: ChatOpenAI):
        """
        Initialize RAG techniques.

        Args:
            llm: Language model instance
        """
        self.llm = llm

    def multi_query_retrieval(
        self,
        question: str,
        retriever: Any,
        config: MultiQueryConfig
    ) -> List[Document]:
        """
        Multi-query retrieval: Generate multiple query perspectives.

        Args:
            question: Original question
            retriever: Retriever instance
            config: Multi-query configuration

        Returns:
            List of unique retrieved documents
        """
        logger.info(f"Applying multi-query retrieval with {config.num_queries} queries")

        # Prompt for generating multiple queries
        template = f"""You are an AI language model assistant. Your task is to generate {config.num_queries}
different versions of the given user question to retrieve relevant documents from a vector
database. By generating multiple perspectives on the user question, your goal is to help
the user overcome some of the limitations of the distance-based similarity search.
Provide these alternative questions separated by newlines. Original question: {{question}}"""

        prompt = ChatPromptTemplate.from_template(template)

        # Generate queries
        generate_queries = (
            prompt
            | self.llm
            | StrOutputParser()
            | (lambda x: x.split("\n"))
        )

        queries = generate_queries.invoke({"question": question})
        queries = [q.strip() for q in queries if q.strip()]
        logger.debug(f"Generated queries: {queries}")

        # Retrieve for each query
        all_docs = []
        for query in queries:
            docs = retriever.get_relevant_documents(query)
            all_docs.append(docs)

        # Get unique documents
        unique_docs = self._get_unique_union(all_docs)
        logger.info(f"Multi-query retrieved {len(unique_docs)} unique documents")

        return unique_docs

    def rag_fusion(
        self,
        question: str,
        retriever: Any,
        config: RAGFusionConfig
    ) -> List[Document]:
        """
        RAG-Fusion: Generate related queries and apply reciprocal rank fusion.

        Args:
            question: Original question
            retriever: Retriever instance
            config: RAG-Fusion configuration

        Returns:
            List of re-ranked documents
        """
        logger.info(f"Applying RAG-Fusion with {config.num_queries} queries")

        # Prompt for generating related queries
        template = f"""You are a helpful assistant that generates multiple search queries based on a single input query.
Generate multiple search queries related to: {{question}}
Output ({config.num_queries} queries):"""

        prompt = ChatPromptTemplate.from_template(template)

        # Generate queries
        generate_queries = (
            prompt
            | self.llm
            | StrOutputParser()
            | (lambda x: x.split("\n"))
        )

        queries = generate_queries.invoke({"question": question})
        queries = [q.strip() for q in queries if q.strip()]
        logger.debug(f"Generated fusion queries: {queries}")

        # Retrieve for each query
        all_docs = []
        for query in queries:
            docs = retriever.get_relevant_documents(query)
            all_docs.append(docs)

        # Apply reciprocal rank fusion
        reranked_docs = self._reciprocal_rank_fusion(all_docs, k=config.rrf_k)
        logger.info(f"RAG-Fusion retrieved {len(reranked_docs)} documents")

        return reranked_docs

    def decomposition_recursive(
        self,
        question: str,
        retriever: Any,
        config: DecompositionConfig
    ) -> tuple[str, List[Document]]:
        """
        Query decomposition with recursive answering.

        Args:
            question: Original question
            retriever: Retriever instance
            config: Decomposition configuration

        Returns:
            Tuple of (final_answer, all_documents_used)
        """
        logger.info(f"Applying recursive decomposition")

        # Generate sub-questions
        decomposition_template = f"""You are a helpful assistant that generates multiple sub-questions related to an input question.
The goal is to break down the input into a set of sub-problems / sub-questions that can be answered in isolation.
Generate multiple search queries related to: {{question}}
Output ({config.max_sub_questions} queries):"""

        decomposition_prompt = ChatPromptTemplate.from_template(decomposition_template)

        generate_queries = (
            decomposition_prompt
            | self.llm
            | StrOutputParser()
            | (lambda x: x.split("\n"))
        )

        sub_questions = generate_queries.invoke({"question": question})
        sub_questions = [q.strip() for q in sub_questions if q.strip()][:config.max_sub_questions]
        logger.debug(f"Generated sub-questions: {sub_questions}")

        # Answer sub-questions recursively
        answer_template = """Here is the question you need to answer:

\n --- \n {question} \n --- \n

Here is any available background question + answer pairs:

\n --- \n {q_a_pairs} \n --- \n

Here is additional context relevant to the question:

\n --- \n {context} \n --- \n

Use the above context and any background question + answer pairs to answer the question: \n {question}
"""

        answer_prompt = ChatPromptTemplate.from_template(answer_template)

        q_a_pairs = ""
        all_docs = []

        for sub_q in sub_questions:
            # Retrieve documents
            docs = retriever.get_relevant_documents(sub_q)
            all_docs.extend(docs)

            # Format context
            context = "\n\n".join([doc.page_content for doc in docs])

            # Generate answer
            rag_chain = (
                answer_prompt
                | self.llm
                | StrOutputParser()
            )

            answer = rag_chain.invoke({
                "question": sub_q,
                "q_a_pairs": q_a_pairs,
                "context": context
            })

            # Update Q&A pairs
            q_a_pairs += f"\n---\nQuestion: {sub_q}\nAnswer: {answer}\n\n"

        # Final answer is the last one generated
        logger.info(f"Decomposition used {len(all_docs)} total document retrievals")
        return answer, all_docs

    def step_back_prompting(
        self,
        question: str,
        retriever: Any,
        config: StepBackConfig
    ) -> tuple[List[Document], List[Document]]:
        """
        Step-back prompting: Generate broader question for better context.

        Args:
            question: Original question
            retriever: Retriever instance
            config: Step-back configuration

        Returns:
            Tuple of (normal_docs, step_back_docs)
        """
        logger.info("Applying step-back prompting")

        # Few-shot examples for step-back
        examples = [
            {
                "input": "Could the members of The Police perform lawful arrests?",
                "output": "what can the members of The Police do?",
            },
            {
                "input": "Jan Sindel's was born in what country?",
                "output": "what is Jan Sindel's personal history?",
            },
        ]

        example_prompt = ChatPromptTemplate.from_messages([
            ("human", "{input}"),
            ("ai", "{output}"),
        ])

        few_shot_prompt = FewShotChatMessagePromptTemplate(
            example_prompt=example_prompt,
            examples=examples,
        )

        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are an expert at world knowledge. Your task is to step back and paraphrase a question to a more generic step-back question, which is easier to answer. Here are a few examples:""",
            ),
            few_shot_prompt,
            ("user", "{question}"),
        ])

        generate_step_back = prompt | self.llm | StrOutputParser()

        # Generate step-back question
        step_back_question = generate_step_back.invoke({"question": question})
        logger.debug(f"Step-back question: {step_back_question}")

        # Retrieve with both questions
        normal_docs = []
        if config.include_original:
            normal_docs = retriever.get_relevant_documents(question)

        step_back_docs = retriever.get_relevant_documents(step_back_question)

        logger.info(f"Step-back retrieved {len(normal_docs)} normal + {len(step_back_docs)} step-back docs")
        return normal_docs, step_back_docs

    def hyde(
        self,
        question: str,
        retriever: Any
    ) -> List[Document]:
        """
        HyDE: Generate hypothetical document and use for retrieval.

        Args:
            question: Original question
            retriever: Retriever instance

        Returns:
            Retrieved documents
        """
        logger.info("Applying HyDE")

        # Generate hypothetical document
        template = """Please write a scientific paper passage to answer the question
Question: {question}
Passage:"""

        prompt = ChatPromptTemplate.from_template(template)

        generate_docs = (
            prompt
            | self.llm
            | StrOutputParser()
        )

        hypothetical_doc = generate_docs.invoke({"question": question})
        logger.debug(f"Generated hypothetical document: {hypothetical_doc[:100]}...")

        # Retrieve using hypothetical document
        docs = retriever.get_relevant_documents(hypothetical_doc)

        logger.info(f"HyDE retrieved {len(docs)} documents")
        return docs

    def _get_unique_union(self, doc_lists: List[List[Document]]) -> List[Document]:
        """
        Get unique union of documents from multiple lists.

        Args:
            doc_lists: List of document lists

        Returns:
            List of unique documents
        """
        flattened_docs = [dumps(doc) for sublist in doc_lists for doc in sublist]
        unique_docs = list(set(flattened_docs))
        return [loads(doc) for doc in unique_docs]

    def _reciprocal_rank_fusion(
        self,
        doc_lists: List[List[Document]],
        k: int = 60
    ) -> List[Document]:
        """
        Apply reciprocal rank fusion to re-rank documents.

        Args:
            doc_lists: List of ranked document lists
            k: RRF constant

        Returns:
            Re-ranked documents
        """
        fused_scores = {}

        for docs in doc_lists:
            for rank, doc in enumerate(docs):
                doc_str = dumps(doc)
                if doc_str not in fused_scores:
                    fused_scores[doc_str] = 0
                fused_scores[doc_str] += 1 / (rank + k)

        reranked_results = [
            loads(doc)
            for doc, score in sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
        ]

        return reranked_results
