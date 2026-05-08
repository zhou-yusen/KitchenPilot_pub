import json
import math

from pydantic import BaseModel, Field

from kitchenpilot.agent.state import AgentState
from kitchenpilot.core.embeddings import EmbeddingProvider, build_embedding_provider
from kitchenpilot.core.llm import ChatMessage, ChatProvider, build_chat_provider
from kitchenpilot.schemas.enums import IntentType
from kitchenpilot.services.mock_data import RECIPES
from kitchenpilot.services.user_memory_service import UserMemoryService


INTENT_EXAMPLES: dict[IntentType, list[str]] = {
    IntentType.RECIPE_QA: [
        "番茄炒蛋怎么做？",
        "酸辣土豆丝怎么炒才脆？",
        "可乐鸡翅为什么太甜？",
        "清蒸鱼有什么注意事项？",
        "这个菜失败了怎么补救？",
        "有没有替代食材？",
    ],
    IntentType.INGREDIENT_RECOMMENDATION: [
        "我有鸡蛋和番茄，能做什么？",
        "家里只有米饭和鸡蛋，推荐一道简单菜。",
        "这些食材可以搭配什么菜？",
        "帮我根据现有食材推荐菜谱。",
        "冰箱里有土豆和青椒，今晚做什么？",
    ],
    IntentType.DAILY_RECOMMENDATION: [
        "今天吃什么？",
        "给我推荐今天的晚饭。",
        "按我的偏好安排一顿饭。",
        "今日推荐一道适合新手的菜。",
        "晚餐想吃清淡一点，有什么推荐？",
    ],
}

DEFAULT_CLARIFICATION_QUESTION = (
    "你是想让我：\n"
    "1. 根据已有食材推荐菜？\n"
    "2. 按你的偏好推荐今天吃什么？\n"
    "3. 回答某道菜的具体做法？"
)


class IntentClassification(BaseModel):
    """Structured result returned by the intent router."""

    intent: IntentType
    confidence: float
    source: str
    ingredients: list[str] = Field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: str = ""


class IntentRouter:
    """Classify user requests with rules, embedding similarity, and LLM fallback."""

    def __init__(
        self,
        provider: ChatProvider | EmbeddingProvider | None = None,
        chat_provider: ChatProvider | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        high_confidence: float = 0.80,
        low_confidence: float = 0.60,
        min_margin: float = 0.08,
    ) -> None:
        """Initialize this router with configurable confidence thresholds."""
        self.chat_provider = chat_provider or provider or build_chat_provider()
        self.embedding_provider = embedding_provider or provider or build_embedding_provider()
        self.high_confidence = high_confidence
        self.low_confidence = low_confidence
        self.min_margin = min_margin
        self._example_vectors: list[tuple[IntentType, list[float]]] | None = None

    def classify(self, query: str, ingredients: list[str] | None = None) -> IntentType:
        """Return the most likely intent for a user query."""
        return self.classify_with_confidence(query, ingredients).intent

    def classify_with_confidence(
        self,
        query: str,
        ingredients: list[str] | None = None,
    ) -> IntentClassification:
        """Return intent, confidence, source, and extracted ingredients for a query."""
        ingredients = sorted(set(ingredients or []) | set(self.extract_ingredients(query)))
        rule_result = self._rule_classify(query, ingredients)
        if rule_result.confidence >= self.high_confidence:
            return rule_result

        embedding_result = self._embedding_classify(query)
        candidate = self._merge_results(rule_result, embedding_result, ingredients)
        if candidate.confidence >= self.low_confidence and candidate.source != "ambiguous":
            return candidate

        llm_result = self._llm_classify(query, ingredients)
        if llm_result:
            if not ingredients and not self._has_cooking_signal(query):
                return IntentClassification(
                    intent=IntentType.UNKNOWN,
                    confidence=min(llm_result.confidence, 0.50),
                    source="llm",
                    needs_clarification=True,
                    clarification_question=DEFAULT_CLARIFICATION_QUESTION,
                )
            return llm_result
        return candidate

    def extract_ingredients(self, query: str) -> list[str]:
        """Find known ingredient names that appear in the user query."""
        known = {
            item.ingredient
            for recipe in RECIPES
            for item in recipe.ingredients
            if len(item.ingredient) >= 1
        }
        return sorted({ingredient for ingredient in known if ingredient in query})

    def _rule_classify(self, query: str, ingredients: list[str]) -> IntentClassification:
        """Classify a query with cheap keyword rules."""
        if self._is_daily_recommendation(query):
            return IntentClassification(
                intent=IntentType.DAILY_RECOMMENDATION,
                confidence=0.82,
                source="rule",
                ingredients=ingredients,
            )
        if self._is_recipe_qa(query):
            return IntentClassification(
                intent=IntentType.RECIPE_QA,
                confidence=0.90,
                source="rule",
                ingredients=ingredients,
            )
        if ingredients or self._is_ingredient_recommendation(query):
            return IntentClassification(
                intent=IntentType.INGREDIENT_RECOMMENDATION,
                confidence=0.84,
                source="rule",
                ingredients=ingredients,
            )
        return IntentClassification(
            intent=IntentType.UNKNOWN,
            confidence=0.20,
            source="rule",
            ingredients=ingredients,
            needs_clarification=True,
            clarification_question=DEFAULT_CLARIFICATION_QUESTION,
        )

    def _embedding_classify(self, query: str) -> IntentClassification | None:
        """Classify a query by cosine similarity against intent examples."""
        try:
            self._ensure_example_vectors()
            query_vectors = self.embedding_provider.embed([query])
        except Exception:
            return None
        if not self._example_vectors or not query_vectors:
            return None

        query_vector = query_vectors[0]
        intent_scores: dict[IntentType, float] = {}
        for intent, example_vector in self._example_vectors:
            score = self._cosine(query_vector, example_vector)
            intent_scores[intent] = max(intent_scores.get(intent, 0.0), score)

        scores = sorted(intent_scores.items(), key=lambda item: item[1], reverse=True)
        top_intent, top_score = scores[0]
        second_score = scores[1][1] if len(scores) > 1 else 0.0
        margin = top_score - second_score
        confidence = max(0.0, min(1.0, top_score * (margin + 0.20)))
        if top_score >= 0.78 and margin >= 0.12:
            confidence = max(confidence, 0.82)
        elif margin < self.min_margin:
            confidence = min(confidence, 0.55)

        return IntentClassification(
            intent=top_intent,
            confidence=confidence,
            source="embedding" if margin >= self.min_margin else "ambiguous",
        )

    def _ensure_example_vectors(self) -> None:
        """Embed and cache all intent example sentences."""
        if self._example_vectors is not None:
            return

        intents: list[IntentType] = []
        examples: list[str] = []
        for intent, values in INTENT_EXAMPLES.items():
            for value in values:
                intents.append(intent)
                examples.append(value)
        vectors = self.embedding_provider.embed(examples)
        self._example_vectors = list(zip(intents, vectors, strict=False))

    def _merge_results(
        self,
        rule_result: IntentClassification,
        embedding_result: IntentClassification | None,
        ingredients: list[str],
    ) -> IntentClassification:
        """Merge rule and embedding results into one routing decision."""
        if embedding_result is None:
            return rule_result

        if rule_result.intent == embedding_result.intent and rule_result.intent != IntentType.UNKNOWN:
            confidence = min(max(rule_result.confidence, embedding_result.confidence) + 0.08, 1.0)
            return embedding_result.model_copy(
                update={
                    "confidence": confidence,
                    "source": "rule+embedding",
                    "ingredients": ingredients,
                }
            )

        candidate = (
            embedding_result
            if embedding_result.confidence > rule_result.confidence
            else rule_result
        )
        source = candidate.source
        confidence = candidate.confidence
        if rule_result.intent != IntentType.UNKNOWN and embedding_result.intent != rule_result.intent:
            confidence = min(confidence, 0.58)
            source = "ambiguous"
        return candidate.model_copy(
            update={
                "confidence": confidence,
                "source": source,
                "ingredients": ingredients,
                "needs_clarification": confidence < self.low_confidence,
            }
        )

    def _llm_classify(
        self,
        query: str,
        ingredients: list[str],
    ) -> IntentClassification | None:
        """Ask the chat model for structured classification when confidence is low."""
        prompt = (
            "只输出 JSON，不要输出解释。intent 必须是 recipe_qa、"
            "ingredient_recommendation、daily_recommendation 或 unknown。"
            "confidence 是 0 到 1 的数字。\n"
            f"用户输入：{query}\n"
            f"已识别食材：{ingredients}\n"
            '输出格式：{"intent":"recipe_qa","confidence":0.8,'
            '"ingredients":["鸡蛋"],"needs_clarification":false}'
        )
        try:
            result = self.chat_provider.chat([ChatMessage(role="user", content=prompt)])
            payload = self._parse_json_object(result.content)
            intent = IntentType(payload.get("intent", IntentType.UNKNOWN))
            confidence = float(payload.get("confidence", 0.5))
            llm_ingredients = payload.get("ingredients", ingredients)
            if not isinstance(llm_ingredients, list):
                llm_ingredients = ingredients
            return IntentClassification(
                intent=intent,
                confidence=max(0.0, min(1.0, confidence)),
                source="llm",
                ingredients=sorted({str(item) for item in llm_ingredients} | set(ingredients)),
                needs_clarification=bool(payload.get("needs_clarification", confidence < 0.60)),
                clarification_question=str(
                    payload.get("clarification_question", DEFAULT_CLARIFICATION_QUESTION)
                ),
            )
        except Exception:
            return None

    @staticmethod
    def _parse_json_object(content: str) -> dict[str, object]:
        """Parse a JSON object from model output that may include extra text."""
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("LLM router did not return a JSON object.")
        value = json.loads(content[start : end + 1])
        if not isinstance(value, dict):
            raise ValueError("LLM router JSON payload is not an object.")
        return value

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        left = left[:size]
        right = right[:size]
        dot = sum(a * b for a, b in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return dot / (left_norm * right_norm)

    @staticmethod
    def _is_daily_recommendation(query: str) -> bool:
        """Check whether the query asks for a daily recommendation."""
        daily_terms = [
            "今日推荐",
            "今天推荐",
            "每日推荐",
            "今天吃什么",
            "今晚吃什么",
            "晚饭推荐",
            "浠婂ぉ鍚冧粈涔",
            "姣忔棩鎺ㄨ崘",
        ]
        return any(term in query for term in daily_terms)

    @staticmethod
    def _has_cooking_signal(query: str) -> bool:
        """Check whether the query contains any cooking-domain signal."""
        signals = [
            "吃",
            "菜",
            "饭",
            "食材",
            "做",
            "炒",
            "煮",
            "蒸",
            "推荐",
            "口味",
            "清淡",
            "晚餐",
            "晚饭",
            "午饭",
            "早餐",
        ]
        recipe_names = [recipe.name for recipe in RECIPES]
        return any(signal in query for signal in signals) or any(
            name in query for name in recipe_names
        )

    @staticmethod
    def _is_ingredient_recommendation(query: str) -> bool:
        """Check whether the query asks for ingredient-based recommendations."""
        ingredient_terms = [
            "我有",
            "家里有",
            "只有",
            "食材",
            "能做什么",
            "推荐一道",
            "鎴戞湁",
            "鎺ㄨ崘涓",
            "鑳藉仛浠",
        ]
        return any(term in query for term in ingredient_terms)

    @staticmethod
    def _is_recipe_qa(query: str) -> bool:
        """Check whether the query looks like a recipe or cooking question."""
        qa_terms = [
            "怎么",
            "如何",
            "为什么",
            "注意",
            "替代",
            "失败",
            "太甜",
            "做法",
            "不脆",
            "鎬庝箞",
            "濡備綍",
            "鍋氭硶",
        ]
        recipe_names = [recipe.name for recipe in RECIPES]
        return any(term in query for term in qa_terms) or any(
            name in query for name in recipe_names
        )


router = IntentRouter()
user_memory_service = UserMemoryService()


def _trace(state: AgentState, event: str) -> list[str]:
    """Append one event to the agent execution trace."""
    return [*state.get("execution_trace", []), event]


def parse_input_node(state: AgentState) -> AgentState:
    """Parse raw user input and merge extracted ingredients into state."""
    query = state["query"]
    existing = state.get("user_ingredients", [])
    extracted = router.extract_ingredients(query)
    merged = sorted(set(existing) | set(extracted))
    return {
        **state,
        "user_ingredients": merged,
        "execution_trace": _trace(state, f"解析输入，识别食材：{merged or '无'}"),
    }


def load_user_history_node(state: AgentState) -> AgentState:
    """Load the user profile and cooking history into state."""
    profile = user_memory_service.get_user_profile(state.get("user_id", "demo_user"))
    return {
        **state,
        "user_profile": profile,
        "execution_trace": _trace(state, "加载用户历史和偏好"),
    }


def route_intent_node(state: AgentState) -> AgentState:
    """Classify the query intent and store it in state."""
    result = router.classify_with_confidence(state["query"], state.get("user_ingredients", []))
    return {
        **state,
        "intent": result.intent,
        "intent_confidence": result.confidence,
        "intent_source": result.source,
        "needs_clarification": result.needs_clarification,
        "clarification_question": result.clarification_question,
        "user_ingredients": result.ingredients,
        "execution_trace": _trace(
            state,
            f"Router 识别意图：{result.intent} "
            f"(confidence={result.confidence:.2f}, source={result.source})",
        ),
    }


def route_after_intent(state: AgentState) -> str:
    """Map the classified intent to the next graph node."""
    intent = state.get("intent", IntentType.UNKNOWN)
    if intent == IntentType.RECIPE_QA:
        return "recipe_qa"
    if intent == IntentType.INGREDIENT_RECOMMENDATION:
        return "ingredient_recommendation"
    if intent == IntentType.DAILY_RECOMMENDATION:
        return "daily_recommendation"
    return "unknown"


__all__ = [
    "IntentClassification",
    "IntentRouter",
    "_trace",
    "load_user_history_node",
    "parse_input_node",
    "route_after_intent",
    "route_intent_node",
]
