"""
Advanced RAG techniques implementation.
"""
import logging
from typing import List, Dict, Any
from operator import itemgetter
 
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_core.load import dumps, loads
 
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
        template = f"""You are an expert search query optimization assistant specializing in information retrieval from document databases.
 
**TASK:** Generate exactly {config.num_queries} diverse reformulations of the user's question to maximize retrieval coverage.
 
**STRATEGY:** Create variations that:
1. Use different vocabulary and synonyms (e.g., "fix" → "resolve", "repair", "troubleshoot")
2. Vary specificity levels (broader context vs. specific details)
3. Rephrase from different angles (technical, practical, conceptual)
4. Address implicit sub-questions within the main question
5. Use different question formats (what, how, why, when, where)
 
**CONSTRAINTS:**
- Each query must be self-contained and grammatically complete
- Maintain the core intent of the original question
- Output exactly {config.num_queries} queries, one per line
- Do NOT include numbering, bullets, or explanations
- Each query should be 5-20 words
 
**ORIGINAL QUESTION:** {{question}}
 
**OUTPUT (one query per line):**"""
 
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
            docs = retriever.invoke(query)
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
        template = f"""You are an advanced search query generation specialist optimizing retrieval through query diversification.
 
**TASK:** Generate exactly {config.num_queries} complementary search queries that explore different facets of the user's information need.
 
**STRATEGY:** Create queries that:
1. Target different aspects or components of the topic
2. Explore related concepts and prerequisites
3. Address potential follow-up questions
4. Use domain-specific terminology variations
5. Cover both overview and specific details
 
**GUIDELINES:**
- Queries can overlap but should emphasize different angles
- Maintain semantic relevance to the original question
- Use natural, search-friendly phrasing
- Each query: 5-15 words
- Output exactly {config.num_queries} queries, one per line
- NO numbering, bullets, or explanations
 
**USER QUESTION:** {{question}}
 
**GENERATED QUERIES (one per line):**"""
 
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
            docs = retriever.invoke(query)
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
        decomposition_template = f"""You are an expert question decomposition specialist skilled in breaking complex queries into atomic sub-questions.
 
**TASK:** Decompose the complex question into exactly {config.max_sub_questions} independent, answerable sub-questions.
 
**DECOMPOSITION PRINCIPLES:**
1. **Atomic:** Each sub-question should address ONE specific aspect
2. **Independent:** Sub-questions can be answered without referencing others
3. **Sequential:** Order sub-questions logically (foundational → specific)
4. **Complete:** Together, sub-questions should cover all aspects needed to answer the main question
5. **Answerable:** Each should be directly answerable from document content
 
**EXAMPLE:**
Main Question: "How do I optimize React performance in large applications?"
Sub-questions:
- What are the main causes of performance issues in React applications?
- Which React performance optimization techniques are most effective?
- How do you implement code splitting and lazy loading in React?
 
**YOUR TURN:**
Main Question: {{question}}
 
**OUTPUT (exactly {config.max_sub_questions} sub-questions, one per line, no numbering):**"""
 
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
        answer_template = """You are a precise question-answering assistant working within a recursive decomposition framework.
 
**YOUR TASK:** Answer the current sub-question using:
1. Document context provided below
2. Previously answered sub-questions (if any)
 
**CURRENT SUB-QUESTION:**
{question}
 
**PREVIOUS Q&A PAIRS (context from earlier sub-questions):**
{q_a_pairs}
 
**DOCUMENT CONTEXT (retrieved information):**
{context}
 
**INSTRUCTIONS:**
- Provide a concise, factual answer (2-4 sentences)
- Reference specific details from the document context
- Build upon previous answers when relevant
- If information is insufficient, state what's missing
- Use clear, declarative statements
 
**YOUR ANSWER:**"""
 
        answer_prompt = ChatPromptTemplate.from_template(answer_template)
 
        q_a_pairs = ""
        all_docs = []
 
        for sub_q in sub_questions:
            # Retrieve documents
            docs = retriever.invoke(sub_q)
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
                """You are an expert question abstraction specialist. Your task is to generate a broader, more general "step-back" question that provides foundational context for answering the specific original question.
 
**PRINCIPLES:**
1. **Generalize:** Remove specific details while keeping the core domain
2. **Broaden Scope:** Ask about concepts, principles, or categories rather than instances
3. **Foundation First:** Target background knowledge needed to understand the specific question
4. **Maintain Relevance:** Stay within the same domain/topic area
 
**EXAMPLES:**""",
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
            normal_docs = retriever.invoke(question)
 
        step_back_docs = retriever.invoke(step_back_question)
 
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
        template = """You are an expert technical writer generating a hypothetical document excerpt that would perfectly answer the user's question.
 
**TASK:** Write a detailed, well-structured document passage (150-250 words) that would ideally contain the answer to the question below.
 
**WRITING STYLE:**
- Professional and informative tone
- Use domain-specific terminology naturally
- Include concrete examples and specific details
- Structure with clear topic sentences
- Write as if extracted from comprehensive documentation
 
**QUESTION:** {question}
 
**HYPOTHETICAL DOCUMENT PASSAGE:**"""
 
        prompt = ChatPromptTemplate.from_template(template)
 
        generate_docs = (
            prompt
            | self.llm
            | StrOutputParser()
        )
 
        hypothetical_doc = generate_docs.invoke({"question": question})
        logger.debug(f"Generated hypothetical document: {hypothetical_doc[:100]}...")
 
        # Retrieve using hypothetical document
        docs = retriever.invoke(hypothetical_doc)
 
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
 