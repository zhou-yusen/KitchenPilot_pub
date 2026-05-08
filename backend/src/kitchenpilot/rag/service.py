import re

from pydantic import BaseModel, Field

from kitchenpilot.rag.chunks import build_recipe_chunks
from kitchenpilot.schemas.recipe import SourceChunk
from kitchenpilot.services.recipe_service import RecipeService


class RAGResult(BaseModel):
    answer: str
    sources: list[SourceChunk] = Field(default_factory=list)


class RAGService:
    def __init__(self, recipe_service: RecipeService | None = None) -> None:
        self.recipe_service = recipe_service or RecipeService()
        self._chunks = build_recipe_chunks(self.recipe_service.list_recipes())

    def retrieve(self, query: str, top_k: int = 4) -> list[SourceChunk]:
        scored: list[SourceChunk] = []
        for chunk in self._chunks:
            score = self._score(query, chunk)
            if score > 0:
                scored.append(chunk.model_copy(update={"score": score}))
        return sorted(scored, key=lambda item: item.score, reverse=True)[:top_k]

    def answer(self, query: str) -> RAGResult:
        sources = self.retrieve(query)
        if not sources:
            return RAGResult(
                answer="知识库里暂时没有找到足够依据。建议换一个具体菜名、食材或失败现象再问。",
                sources=[],
            )

        main_recipe = sources[0].recipe_name
        evidence = "；".join(chunk.content for chunk in sources[:3])
        answer = (
            f"根据知识库中关于「{main_recipe}」的内容，建议如下：{evidence}。"
            "新手操作时优先控制火候、按步骤处理食材，并注意安全提示。"
        )
        return RAGResult(answer=answer, sources=sources)

    def _score(self, query: str, chunk: SourceChunk) -> float:
        query_terms = self._terms(query)
        content = f"{chunk.recipe_name}{chunk.content}"
        content_terms = self._terms(content)
        overlap = len(query_terms & content_terms)
        score = float(overlap)

        if chunk.recipe_name in query:
            score += 5
        for keyword in ["脆", "替代", "失败", "太甜", "新手", "注意", "怎么做"]:
            if keyword in query and keyword in content:
                score += 2
        return score

    @staticmethod
    def _terms(text: str) -> set[str]:
        words = set(re.findall(r"[A-Za-z0-9]+", text.lower()))
        chinese_chars = {char for char in text if "\u4e00" <= char <= "\u9fff"}
        return words | chinese_chars

