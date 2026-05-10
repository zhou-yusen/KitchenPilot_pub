import re

from pydantic import BaseModel, Field

from kitchenpilot.core.config import Settings, get_settings
from kitchenpilot.core.llm import ChatMessage, ChatProvider, build_chat_provider
from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.rag.qdrant_store import QdrantRecipeStore
from kitchenpilot.schemas.enums import ChunkType
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.services.recipe_service import RecipeService


class RAGResult(BaseModel):
    """Container for a generated answer and its retrieved sources."""

    answer: str
    sources: list[SourceChunk] = Field(default_factory=list)


class RAGService:
    """Retrieve recipe chunks and answer recipe questions with optional LLM generation."""

    def __init__(
        self,
        recipe_service: RecipeService | None = None,
        chat_provider: ChatProvider | None = None,
        qdrant_store: QdrantRecipeStore | None = None,
        settings: Settings | None = None,
    ) -> None:
        """Initialize this object with recipe, chat, and retrieval collaborators."""
        self.settings = settings or get_settings()
        self.recipe_service = recipe_service or RecipeService()
        self.chat_provider = chat_provider or build_chat_provider(self.settings)
        self.qdrant_store = qdrant_store
        self._chunks = build_recipe_chunks(self.recipe_service.list_recipes())

    def retrieve(self, query: str, top_k: int = 4) -> list[SourceChunk]:
        """Return source chunks relevant to a user query."""
        if self.settings.rag_use_qdrant:
            qdrant_results = self._retrieve_from_qdrant(query, top_k)
            if qdrant_results:
                return self._rerank(query, qdrant_results)[:top_k]
        return self._rerank(query, self._retrieve_locally(query, top_k))[:top_k]

    def answer(
        self,
        query: str,
        conversation_turns: list[dict[str, object]] | None = None,
    ) -> RAGResult:
        """Generate an answer from retrieved source chunks."""
        sources = self.retrieve(query)
        if not sources:
            return RAGResult(
                answer="知识库里暂时没有找到足够依据。建议换一个具体菜名、食材或失败现象再问。",
                sources=[],
            )

        llm_answer = self._answer_with_llm(query, sources, conversation_turns or [])
        if llm_answer:
            return RAGResult(answer=llm_answer, sources=sources)

        main_recipe = sources[0].recipe_name
        evidence = "；".join(chunk.content for chunk in sources[:3])
        answer = (
            f"根据知识库中关于“{main_recipe}”的内容，建议如下：{evidence}。"
            "新手操作时优先控制火候、按步骤处理食材，并注意安全提示。"
        )
        return RAGResult(answer=answer, sources=sources)

    def _retrieve_from_qdrant(self, query: str, top_k: int) -> list[SourceChunk]:
        """Retrieve chunks from Qdrant and return an empty list when unavailable."""
        try:
            store = self.qdrant_store or QdrantRecipeStore(settings=self.settings)
            return store.search(query, top_k=top_k)
        except Exception:
            return []

    def _retrieve_locally(self, query: str, top_k: int) -> list[SourceChunk]:
        """Retrieve chunks using local lexical scoring as a fallback."""
        scored: list[SourceChunk] = []
        for chunk in self._chunks:
            score = self._score(query, chunk)
            if score > 0:
                metadata = {**chunk.metadata, "retrieval_source": "local"}
                scored.append(chunk.model_copy(update={"score": score, "metadata": metadata}))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def _answer_with_llm(
        self,
        query: str,
        sources: list[SourceChunk],
        conversation_turns: list[dict[str, object]],
    ) -> str:
        """Ask the configured chat model to answer from retrieved recipe evidence."""
        context = "\n".join(
            f"[{index}] {source.recipe_name} / {source.chunk_type}: {source.content}"
            for index, source in enumerate(sources, start=1)
        )
        recent_context = self._format_conversation_context(conversation_turns)
        messages = [
            ChatMessage(
                role="system",
                content=(
                    "你是 KitchenPilot，一个面向厨房新手的做菜助手。"
                    "只能根据给定资料和必要的最近对话上下文回答，不要编造精确用量。"
                    "优先输出可执行步骤、用量、火候和安全风险。"
                    "默认用朴素中文和编号列表，少用 Markdown 符号，不要使用加粗符号。"
                    "如果用户要求只要步骤、少解释或少符号，必须遵守。"
                    "不要展开思考过程。"
                ),
            ),
            ChatMessage(
                role="user",
                content=(
                    f"用户问题：{query}\n\n"
                    f"最近对话：\n{recent_context or '无'}\n\n"
                    f"资料：\n{context}\n\n请用中文直接回答。"
                ),
            ),
        ]
        try:
            return self.chat_provider.chat(messages).content
        except Exception:
            return ""

    @staticmethod
    def _format_conversation_context(conversation_turns: list[dict[str, object]]) -> str:
        """Compress recent turns for prompt context."""
        lines: list[str] = []
        for turn in conversation_turns[-4:]:
            query = str(turn.get("query") or "").strip()
            active_recipe = str(turn.get("active_recipe") or "").strip()
            intent = str(turn.get("intent") or "").strip()
            if query:
                lines.append(
                    f"- intent={intent}, active_recipe={active_recipe or '无'}, "
                    f"query={query}"
                )
        return "\n".join(lines)

    def _score(self, query: str, chunk: SourceChunk) -> float:
        """Calculate a simple lexical relevance score for a chunk."""
        query_terms = self._terms(query)
        content = f"{chunk.recipe_name}{chunk.content}"
        content_terms = self._terms(content)
        overlap = len(query_terms & content_terms)
        score = float(overlap)

        if chunk.recipe_name in query:
            score += 5
        for keyword in ["脆", "替代", "失败", "太甜", "新手", "注意", "怎么做", "安全"]:
            if keyword in query and keyword in content:
                score += 2
        return score

    def _rerank(self, query: str, chunks: list[SourceChunk]) -> list[SourceChunk]:
        """Prefer chunk types that match common cooking question intents."""
        preferred_types = self._preferred_chunk_types(query)
        if not preferred_types:
            return chunks

        priority = {
            chunk_type: len(preferred_types) - index
            for index, chunk_type in enumerate(preferred_types)
        }
        return sorted(
            chunks,
            key=lambda chunk: (priority.get(chunk.chunk_type, 0), chunk.score),
            reverse=True,
        )

    @staticmethod
    def _preferred_chunk_types(query: str) -> list[ChunkType]:
        """Infer preferred chunk types from simple Chinese cooking question cues."""
        if any(keyword in query for keyword in ["没有", "替代", "代替", "换成", "可不可以不用"]):
            return [ChunkType.SUBSTITUTION, ChunkType.INGREDIENTS, ChunkType.STEP]
        if any(keyword in query for keyword in ["安全", "熟", "处理", "过敏", "生熟"]):
            return [ChunkType.SAFETY, ChunkType.STEP, ChunkType.FAILURE]
        failure_keywords = ["失败", "为什么", "腥味", "太甜", "太咸", "不脆", "粘锅", "糊"]
        if any(keyword in query for keyword in failure_keywords):
            return [ChunkType.FAILURE, ChunkType.STEP, ChunkType.SAFETY]
        step_keywords = ["怎么做", "步骤", "火候", "多久", "怎么炒", "怎么煮"]
        if any(keyword in query for keyword in step_keywords):
            return [ChunkType.STEP, ChunkType.SAFETY, ChunkType.FAILURE]
        return []

    @staticmethod
    def _terms(text: str) -> set[str]:
        """Split a query into simple search terms."""
        words = set(re.findall(r"[A-Za-z0-9]+", text.lower()))
        chinese_chars = {char for char in text if "\u4e00" <= char <= "\u9fff"}
        return words | chinese_chars
