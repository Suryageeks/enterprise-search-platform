from langchain_core.prompts import ChatPromptTemplate
from langchain_qdrant import QdrantVectorStore
from langchain_google_genai import ChatGoogleGenerativeAI
from qdrant_client import QdrantClient, models

from app.core.config import settings
from app.schemas.rag import RagQueryResponse, RagSource
from app.services.bert_embeddings import BertEmbeddings

class RagService:
    def __init__(self) -> None:
        self.embeddings = BertEmbeddings()
        self.ensure_qdrant_collection()

        self.vector_store = QdrantVectorStore.from_existing_collection(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            embedding=self.embeddings,
        )

        self.llm = ChatGoogleGenerativeAI(
            model=settings.chat_model,
            google_api_key=settings.google_api_key,
            temperature=0,
            max_output_tokens=settings.max_output_tokens
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
                        You are an enterprise search assistant.

                        Use only the provided context to answer.
                        If the context does not contain the answer, say:
                        "I don't have enough information in the indexed documents."

                        Keep the answer clear and practical.
                    """,
                ),
                (
                    "human",
                    """
                        Question:
                        {question}

                        Context:
                        {context}
                    """,
                ),
            ]
        )

    def ensure_qdrant_collection(self) -> None:
        client = QdrantClient(url=settings.qdrant_url)

        if client.collection_exists(settings.qdrant_collection_name):
            return

        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=models.VectorParams(
                size=768,
                distance=models.Distance.COSINE,
            ),
        )

    async def query(self, question: str, top_k: int = 5) -> RagQueryResponse:
        doc_with_scores = await self.retrieve_documents(question, top_k)

        context = self.build_context(doc_with_scores)
        sources = self.build_sources(doc_with_scores)

        answer = await self.generate_answer(
            question=question,
            context=context,
        )

        return RagQueryResponse(
            answer=answer,
            sources=sources,
        )

    async def retrieve_documents(self, question: str, top_k: int):
        return await self.vector_store.asimilarity_search_with_score(
            query=question,
            k=top_k,
        )

    def build_context(self, docs_with_scores) -> str:
        context_parts: list[str] = []

        for doc, _score in docs_with_scores:
            context_parts.append(doc.page_content)

        return "\n\n---\n\n".join(context_parts)
        
    def build_sources(self, docs_with_scores) -> list[RagSource]:
        sources: list[RagSource] = []

        for doc, score in docs_with_scores:
            metadata = doc.metadata or {}
            source = RagSource(
                doc_id=metadata.get("doc_id"),
                file_name=metadata.get("file_name"),
                chunk_index=metadata.get("chunk_index"),
                score=float(score),
                text_preview=doc.page_content[:250],
            )
            sources.append(source)

        return sources
    
    async def generate_answer(self, question: str, context: str) -> str:
        prompt_value = self.prompt.invoke(
            {
                "question": question,
                "context": context
            }
        )

        response = await self.llm.ainvoke(prompt_value)

        return str(response.content)

rag_service = RagService()
