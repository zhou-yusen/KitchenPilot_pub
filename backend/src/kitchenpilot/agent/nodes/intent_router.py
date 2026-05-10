import json
import math

from pydantic import BaseModel, Field

from kitchenpilot.agent.state import AgentState
from kitchenpilot.core.embeddings import EmbeddingProvider, build_embedding_provider
from kitchenpilot.core.llm import ChatMessage, ChatProvider, build_chat_provider
from kitchenpilot.schemas.enums import IntentType, RecommendationType
from kitchenpilot.services.conversation_memory_service import conversation_memory_service
from kitchenpilot.services.recipe_service import RecipeService
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
    IntentType.RECOMMENDATION: [
        "我有鸡蛋和番茄，能做什么？",
        "家里只有米饭和鸡蛋，推荐一道简单菜。",
        "这些食材可以搭配什么菜？",
        "帮我根据现有食材推荐菜谱。",
        "冰箱里有土豆和青椒，今晚做什么？",
        "今天吃什么？",
        "给我推荐今天的晚饭。",
        "按我的偏好安排一顿饭。",
        "今日推荐一道适合新手的菜。",
        "晚餐想吃清淡一点，有什么推荐？",
    ],
}

DEFAULT_CLARIFICATION_QUESTION = (
    "我暂时无法判断你的具体需求。\n"
    "你可以这样问：\n"
    "1. 根据已有食材推荐菜：我有鸡蛋和土豆，推荐一道菜。\n"
    "2. 按你的偏好推荐今天吃什么：今天吃什么？\n"
    "3. 回答某道菜的具体做法：土豆丝怎么炒得脆？"
)


class IntentClassification(BaseModel):
    """Structured result returned by the intent router."""

    intent: IntentType
    confidence: float
    source: str
    recommendation_type: RecommendationType | None = None
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
        recipe_service: RecipeService | None = None,
        high_confidence: float = 0.80,
        low_confidence: float = 0.60,
        min_margin: float = 0.08,
    ) -> None:
        """Initialize this router with configurable confidence thresholds."""
        self.chat_provider = chat_provider or provider or build_chat_provider()
        self.embedding_provider = embedding_provider or provider or build_embedding_provider()
        self.recipe_service = recipe_service or RecipeService()
        self.high_confidence = high_confidence
        self.low_confidence = low_confidence
        self.min_margin = min_margin
        self._example_vectors: list[tuple[IntentType, list[float]]] | None = None
        self._recipes_cache = None

    def classify(self, query: str, ingredients: list[str] | None = None) -> IntentType:
        """Return the most likely intent for a user query."""
        return self.classify_with_confidence(query, ingredients).intent

    def classify_with_confidence(
        self,
        query: str,
        ingredients: list[str] | None = None,
    ) -> IntentClassification:
        """Return intent, confidence, recommendation subtype, and extracted ingredients."""
        ingredients = sorted(set(ingredients or []) | set(self.extract_ingredients(query)))
        rule_result = self._rule_classify(query, ingredients)
        if rule_result.confidence >= self.high_confidence:
            return rule_result

        embedding_result = self._embedding_classify(query, ingredients)
        candidate = self._merge_results(rule_result, embedding_result, ingredients)
        if candidate.confidence >= self.low_confidence and candidate.source != "ambiguous":
            return candidate

        llm_result = self._llm_classify(query, ingredients)
        if llm_result:
            if not ingredients and not self._has_cooking_signal(query):
                return IntentClassification(
                    intent=IntentType.FALLBACK,
                    confidence=min(llm_result.confidence, 0.50),
                    source="llm",
                    needs_clarification=True,
                    clarification_question=DEFAULT_CLARIFICATION_QUESTION,
                )
            return llm_result
        return candidate

    def extract_ingredients(self, query: str) -> list[str]:
        """Find known ingredient names that appear in the user query."""
        known = sorted({
            item.ingredient
            for recipe in self._recipes()
            for item in recipe.ingredients
            if len(item.ingredient) >= 1
        })
        matched: set[str] = set()
        for ingredient in known:
            if ingredient in query:
                matched.add(ingredient)
                continue
            for alias in self._ingredient_aliases(ingredient):
                if alias in query:
                    matched.add(alias)
        return sorted(matched)

    def _rule_classify(self, query: str, ingredients: list[str]) -> IntentClassification:
        """Classify a query with cheap keyword rules."""
        has_recipe_name = self._has_recipe_name(query)
        if has_recipe_name and self._is_recipe_learning_request(query):
            return IntentClassification(
                intent=IntentType.RECIPE_QA,
                confidence=0.92,
                source="rule",
                ingredients=ingredients,
            )
        if self._is_daily_recommendation(query) and not self._is_ingredient_recommendation(query):
            return IntentClassification(
                intent=IntentType.RECOMMENDATION,
                recommendation_type=RecommendationType.DAILY,
                confidence=0.88,
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
        if self._is_short_cooking_question(query):
            return IntentClassification(
                intent=IntentType.FALLBACK,
                confidence=0.86,
                source="rule",
                ingredients=ingredients,
                needs_clarification=True,
                clarification_question=(
                    "你是在追问哪道菜？请先说菜名，例如："
                    "可乐鸡翅生抽要下多少？"
                ),
            )
        if ingredients or self._is_ingredient_recommendation(query):
            return IntentClassification(
                intent=IntentType.RECOMMENDATION,
                recommendation_type=RecommendationType.INGREDIENTS,
                confidence=0.88,
                source="rule",
                ingredients=ingredients,
            )
        return IntentClassification(
            intent=IntentType.FALLBACK,
            confidence=0.20,
            source="rule",
            ingredients=ingredients,
            needs_clarification=True,
            clarification_question=DEFAULT_CLARIFICATION_QUESTION,
        )

    def _embedding_classify(
        self, query: str, ingredients: list[str]
    ) -> IntentClassification | None:
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
            recommendation_type=(
                self._recommendation_type(query, ingredients)
                if top_intent == IntentType.RECOMMENDATION
                else None
            ),
            confidence=confidence,
            source="embedding" if margin >= self.min_margin else "ambiguous",
            ingredients=ingredients,
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

        if (
            rule_result.intent == embedding_result.intent
            and rule_result.intent != IntentType.FALLBACK
        ):
            confidence = min(max(rule_result.confidence, embedding_result.confidence) + 0.08, 1.0)
            return embedding_result.model_copy(
                update={
                    "confidence": confidence,
                    "source": "rule+embedding",
                    "ingredients": ingredients,
                    "recommendation_type": (
                        rule_result.recommendation_type
                        or embedding_result.recommendation_type
                    ),
                }
            )

        candidate = (
            embedding_result
            if embedding_result.confidence > rule_result.confidence
            else rule_result
        )
        source = candidate.source
        confidence = candidate.confidence
        if (
            rule_result.intent != IntentType.FALLBACK
            and embedding_result.intent != rule_result.intent
        ):
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
            "只输出 JSON，不要输出解释。intent 必须是 recipe_qa、recommendation 或 fallback。"
            "当 intent 为 recommendation 时，recommendation_type 必须是 ingredients 或 daily。"
            "confidence 是 0 到 1 的数字。\n"
            f"用户输入：{query}\n"
            f"已识别食材：{ingredients}\n"
            '输出格式：{"intent":"recommendation","recommendation_type":"ingredients",'
            '"confidence":0.8,"ingredients":["鸡蛋"],"needs_clarification":false}'
        )
        try:
            result = self.chat_provider.chat([ChatMessage(role="user", content=prompt)])
            payload = self._parse_json_object(result.content)
            intent = IntentType(payload.get("intent", IntentType.FALLBACK))
            confidence = float(payload.get("confidence", 0.5))
            recommendation_type = None
            if intent == IntentType.RECOMMENDATION:
                recommendation_type = RecommendationType(
                    payload.get("recommendation_type") or RecommendationType.INGREDIENTS
                )
            llm_ingredients = payload.get("ingredients", ingredients)
            if not isinstance(llm_ingredients, list):
                llm_ingredients = ingredients
            return IntentClassification(
                intent=intent,
                recommendation_type=recommendation_type,
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
    def _recommendation_type(
        query: str, ingredients: list[str]
    ) -> RecommendationType | None:
        """Infer the recommendation subtype from query and extracted ingredients."""
        if IntentRouter._is_daily_recommendation(query):
            return RecommendationType.DAILY
        if ingredients or IntentRouter._is_ingredient_recommendation(query):
            return RecommendationType.INGREDIENTS
        return None

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
            "偏好",
            "推荐一道菜",
            "推荐个菜",
            "推荐菜",
            "随便推荐",
            "浠婂ぉ鍚冧粈涔",
            "姣忔棩鎺ㄨ崘",
        ]
        return any(term in query for term in daily_terms)

    def _has_cooking_signal(self, query: str) -> bool:
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
        return any(signal in query for signal in signals) or self._has_recipe_name(query)

    @staticmethod
    def _is_ingredient_recommendation(query: str) -> bool:
        """Check whether the query asks for ingredient-based recommendations."""
        ingredient_terms = [
            "我有",
            "家里有",
            "只有",
            "食材",
            "能做什么",
            "鎴戞湁",
            "鑳藉仛浠",
        ]
        return any(term in query for term in ingredient_terms)

    def _is_recipe_qa(self, query: str) -> bool:
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
        return any(term in query for term in qa_terms) or self._has_recipe_name(query)

    def _has_recipe_name(self, query: str) -> bool:
        """Check whether the query mentions a known recipe name."""
        return any(recipe.name in query for recipe in self._recipes())

    def _recipes(self):
        """Return recipes from SQLite first, falling back inside RecipeService."""
        if self._recipes_cache is None:
            self._recipes_cache = self.recipe_service.list_recipes()
        return self._recipes_cache

    @staticmethod
    def _is_recipe_learning_request(query: str) -> bool:
        """Detect requests that mean the user wants to learn or make a named dish."""
        terms = ["我想学", "想学", "学做", "想做", "教我", "我要做", "准备做"]
        return any(term in query for term in terms)

    @staticmethod
    def _is_short_cooking_question(query: str) -> bool:
        """Treat short condiment/amount questions as clarification, not recommendation."""
        compact = query.strip()
        if len(compact) > 18 or not compact.endswith(("？", "?")):
            return False
        question_terms = ["用不用", "要不要", "放不放", "放多少", "多少", "几勺", "还要"]
        condiment_terms = ["盐", "生抽", "老抽", "料酒", "油", "糖", "醋", "蚝油", "调料"]
        return any(term in compact for term in question_terms) and any(
            term in compact for term in condiment_terms
        )

    @staticmethod
    def _ingredient_aliases(ingredient: str) -> set[str]:
        """Return short aliases for common ingredient names."""
        aliases: set[str] = set()
        suffixes = ["中", "块", "仁", "末", "片", "段", "丁"]
        for suffix in suffixes:
            if ingredient.endswith(suffix) and len(ingredient) > len(suffix) + 1:
                aliases.add(ingredient[: -len(suffix)])
        if ingredient.startswith("鲜") and len(ingredient) > 2:
            aliases.add(ingredient[1:])
        return aliases


router = IntentRouter()
user_memory_service = UserMemoryService()

FOLLOW_UP_TERMS = [
    "多少",
    "几勺",
    "几克",
    "多久",
    "多长时间",
    "火候",
    "还需要",
    "还要",
    "别的调料",
    "这个",
    "这道菜",
    "它",
    "上面",
    "刚才",
    "前面",
    "要下",
    "放多少",
]


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


def load_session_memory_node(state: AgentState) -> AgentState:
    """Load recent session turns and rewrite follow-up questions when possible."""
    session_id = conversation_memory_service.ensure_session_id(state.get("session_id"))
    turns = conversation_memory_service.load(session_id)
    active_recipe = conversation_memory_service.last_active_recipe(session_id)
    query = state["query"]
    is_follow_up = bool(active_recipe and _looks_like_follow_up(query))
    rewritten_query = f"{active_recipe}：{query}" if is_follow_up else None
    return {
        **state,
        "session_id": session_id,
        "conversation_turns": turns,
        "active_recipe": active_recipe if is_follow_up else state.get("active_recipe"),
        "rewritten_query": rewritten_query,
        "is_follow_up": is_follow_up,
        "execution_trace": _trace(
            state,
            (
                f"加载 session memory：{len(turns)} 轮，追问改写为 {rewritten_query}"
                if is_follow_up
                else f"加载 session memory：{len(turns)} 轮"
            ),
        ),
    }


def route_intent_node(state: AgentState) -> AgentState:
    """Classify the query intent and store it in state."""
    if state.get("is_follow_up") and state.get("active_recipe"):
        return {
            **state,
            "intent": IntentType.RECIPE_QA,
            "recommendation_type": None,
            "intent_confidence": 0.92,
            "intent_source": "session_memory",
            "needs_clarification": False,
            "clarification_question": "",
            "execution_trace": _trace(
                state,
                "Router 使用 session memory 将追问路由到 recipe_qa "
                "(confidence=0.92, source=session_memory)",
            ),
        }
    result = router.classify_with_confidence(state["query"], state.get("user_ingredients", []))
    return {
        **state,
        "intent": result.intent,
        "recommendation_type": result.recommendation_type,
        "intent_confidence": result.confidence,
        "intent_source": result.source,
        "needs_clarification": result.needs_clarification,
        "clarification_question": result.clarification_question,
        "user_ingredients": result.ingredients,
        "execution_trace": _trace(
            state,
            f"Router 识别意图：{result.intent}"
            f"{f'/{result.recommendation_type}' if result.recommendation_type else ''} "
            f"(confidence={result.confidence:.2f}, source={result.source})",
        ),
    }


def route_after_intent(state: AgentState) -> str:
    """Map the classified intent to the next graph node."""
    intent = state.get("intent", IntentType.FALLBACK)
    if intent == IntentType.RECIPE_QA:
        return "recipe_qa"
    if intent == IntentType.RECOMMENDATION:
        return "recommendation"
    return "fallback"


def save_session_memory_node(state: AgentState) -> AgentState:
    """Persist the completed turn in in-memory session storage."""
    conversation_memory_service.save(state)
    return {
        **state,
        "execution_trace": _trace(state, "保存 session memory"),
    }


def _looks_like_follow_up(query: str) -> bool:
    """Detect short context-dependent cooking follow-ups."""
    compact = query.strip()
    if not compact:
        return False
    if any(term in compact for term in FOLLOW_UP_TERMS):
        return True
    return len(compact) <= 18 and compact.endswith(("？", "?"))


__all__ = [
    "IntentClassification",
    "IntentRouter",
    "_trace",
    "load_session_memory_node",
    "load_user_history_node",
    "parse_input_node",
    "route_after_intent",
    "route_intent_node",
    "save_session_memory_node",
]
