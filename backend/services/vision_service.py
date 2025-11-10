"""
GPT-4o Vision service for analyzing images and extracting content.
"""
import logging
import base64
from typing import Dict, List, Optional, Literal
import httpx
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class GPT4VisionService:
    """Service for analyzing images using GPT-4o and GPT-4o-mini."""

    # Predefined prompts for different analysis tasks
    PROMPTS = {
        "comprehensive": """Analyze this image comprehensively and provide:
1. A detailed description of what the image shows (2-3 sentences)
2. All text content visible in the image (exact transcription)
3. Key visual elements (objects, diagrams, charts, etc.)
4. Context clues (what type of document/content this appears to be)

Format your response as:
Description: [detailed description]
Text Content: [all text found]
Key Elements: [comma-separated list]
Context: [type and purpose]""",

        "ocr": """Extract ALL text visible in this image.
Provide exact transcription preserving formatting and structure where possible.
If no text is found, respond with 'No text detected'.""",

        "description": """Describe this image in 2-3 detailed sentences.
Focus on the main content, purpose, and any notable features.""",

        "diagram_analysis": """Analyze this diagram/chart and describe:
1. Type of diagram (flowchart, architecture, UML, chart, etc.)
2. Main components and their relationships
3. Flow or hierarchy if applicable
4. Key insights or conclusions shown

Be specific and technical.""",

        "search_optimized": """Analyze this image and create a search-optimized description that would help someone find this image later.
Include:
- What the image shows
- Key concepts or topics
- Visual elements and their purpose
- Any text or labels
- Document type or context

Write in a natural, paragraph form suitable for semantic search."""
    }

    def __init__(
        self,
        api_key: str,
        default_model: Literal["gpt-4o", "gpt-4o-mini"] = "gpt-4o-mini",
        max_tokens: int = 1000,
        temperature: float = 0.0,
    ):
        """
        Initialize GPT-4o Vision service.

        Args:
            api_key: OpenAI API key
            default_model: Default model to use (gpt-4o or gpt-4o-mini)
            max_tokens: Maximum tokens for response
            temperature: Temperature for generation (0.0 for deterministic)
        """
        self.client = AsyncOpenAI(
            api_key=api_key,
            http_client=httpx.AsyncClient(verify=False)
        )
        self.default_model = default_model
        self.max_tokens = max_tokens
        self.temperature = temperature

        logger.info(f"Initialized GPT4VisionService with model: {default_model}")

    async def analyze_image(
        self,
        image_data: bytes,
        task: Literal["comprehensive", "ocr", "description", "diagram_analysis", "search_optimized"] = "comprehensive",
        custom_prompt: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Analyze an image using GPT-4o Vision.

        Args:
            image_data: Image data as bytes
            task: Predefined task type, or use custom_prompt
            custom_prompt: Custom prompt (overrides task)
            model: Model to use (overrides default)

        Returns:
            Dictionary with analysis results
        """
        try:
            # Encode image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')

            # Determine prompt
            prompt = custom_prompt if custom_prompt else self.PROMPTS.get(task, self.PROMPTS["comprehensive"])

            # Determine model
            model_to_use = model if model else self.default_model

            # Call GPT-4o Vision
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": "high"  # high detail for better text extraction
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            result_text = response.choices[0].message.content

            # Parse comprehensive response
            if task == "comprehensive" and not custom_prompt:
                parsed = self._parse_comprehensive_response(result_text)
                return parsed

            # For other tasks, return raw response
            return {
                "task": task,
                "result": result_text,
                "model": model_to_use,
                "tokens_used": response.usage.total_tokens if response.usage else 0
            }

        except Exception as e:
            logger.error(f"Error analyzing image with GPT-4o Vision: {str(e)}")
            return {
                "error": str(e),
                "task": task,
                "result": ""
            }

    def _parse_comprehensive_response(self, text: str) -> Dict[str, str]:
        """
        Parse comprehensive analysis response into structured format.

        Args:
            text: Raw response text

        Returns:
            Parsed response dictionary
        """
        result = {
            "description": "",
            "text_content": "",
            "key_elements": "",
            "context": ""
        }

        # Simple parsing by looking for section headers
        sections = {
            "Description:": "description",
            "Text Content:": "text_content",
            "Key Elements:": "key_elements",
            "Context:": "context"
        }

        current_section = None
        lines = text.split('\n')

        for line in lines:
            line = line.strip()

            # Check if this line starts a new section
            section_found = False
            for header, key in sections.items():
                if line.startswith(header):
                    current_section = key
                    # Extract content after header
                    content = line[len(header):].strip()
                    result[key] = content
                    section_found = True
                    break

            # If not a header and we have a current section, append to it
            if not section_found and current_section and line:
                if result[current_section]:
                    result[current_section] += " " + line
                else:
                    result[current_section] = line

        return result

    async def create_image_context_for_indexing(
        self,
        image_data: bytes,
        image_index: int = 0,
        document_context: Optional[str] = None
    ) -> str:
        """
        Create rich context string for an image suitable for embedding and indexing.

        This method generates a comprehensive, search-optimized description
        that can be embedded alongside text content.

        Args:
            image_data: Image data as bytes
            image_index: Index of image in document (for reference)
            document_context: Optional context about the document this image belongs to

        Returns:
            Formatted context string ready for embedding
        """
        try:
            # Get comprehensive analysis
            analysis = await self.analyze_image(image_data, task="search_optimized")

            if "error" in analysis:
                return f"[Image {image_index + 1}]: Error analyzing image - {analysis['error']}"

            # Build context string
            context_parts = [f"[Image {image_index + 1}]"]

            if document_context:
                context_parts.append(f"Document Context: {document_context}")

            # Add the search-optimized description
            context_parts.append(analysis.get("result", ""))

            # Try to also get text content specifically
            ocr_result = await self.analyze_image(image_data, task="ocr")
            if ocr_result.get("result") and ocr_result["result"] != "No text detected":
                context_parts.append(f"Text in image: {ocr_result['result']}")

            return "\n".join(context_parts)

        except Exception as e:
            logger.error(f"Error creating image context: {str(e)}")
            return f"[Image {image_index + 1}]: Unable to analyze"

    async def answer_question_about_images(
        self,
        question: str,
        images: List[bytes],
        context: Optional[str] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Answer a question about one or more images.

        This is useful for visual questions where the user wants to know
        something specific about images retrieved from the vector store.

        Args:
            question: User's question
            images: List of image data
            context: Optional text context from retrieved documents
            model: Model to use (defaults to gpt-4o for better quality)

        Returns:
            Answer to the question
        """
        try:
            # Use gpt-4o by default for question answering (better quality)
            model_to_use = model if model else "gpt-4o"

            # Build prompt
            prompt = f"Question: {question}"
            if context:
                prompt = f"Context from documents:\n{context}\n\n{prompt}"

            # Encode all images
            image_contents = []
            for image_data in images[:5]:  # Limit to 5 images for token efficiency
                base64_image = base64.b64encode(image_data).decode('utf-8')
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                })

            # Build message content (text + images)
            message_content = [{"type": "text", "text": prompt}]
            message_content.extend(image_contents)

            # Call GPT-4o Vision
            response = await self.client.chat.completions.create(
                model=model_to_use,
                messages=[
                    {
                        "role": "user",
                        "content": message_content
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )

            answer = response.choices[0].message.content
            logger.info(f"Answered question about {len(images)} images using {model_to_use}")

            return answer

        except Exception as e:
            logger.error(f"Error answering question about images: {str(e)}")
            return f"I encountered an error analyzing the images: {str(e)}"
