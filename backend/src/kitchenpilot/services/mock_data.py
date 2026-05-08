from kitchenpilot.schemas.enums import Difficulty
from kitchenpilot.schemas.recipe import Recipe, RecipeIngredient, RecipeStep


RECIPES: list[Recipe] = [
    Recipe(
        id=1,
        name="番茄炒蛋",
        description="新手友好的家常快手菜，适合用番茄和鸡蛋快速完成。",
        difficulty=Difficulty.EASY,
        time_minutes=15,
        beginner_friendly=True,
        seasons=["spring", "summer", "autumn", "winter"],
        ingredients=[
            RecipeIngredient(ingredient="番茄", amount="2个"),
            RecipeIngredient(ingredient="鸡蛋", amount="2个"),
            RecipeIngredient(ingredient="盐", amount="适量", required=False),
            RecipeIngredient(ingredient="食用油", amount="适量", required=False),
            RecipeIngredient(ingredient="糖", amount="少量", required=False),
        ],
        steps=[
            RecipeStep(order=1, content="鸡蛋打散，番茄切块。"),
            RecipeStep(
                order=2,
                content="热锅倒油，先把鸡蛋炒至凝固后盛出。",
                beginner_tip="鸡蛋刚凝固就盛出，避免炒老。",
            ),
            RecipeStep(
                order=3,
                content="锅中补少量油，放入番茄炒到出汁。",
                beginner_tip="可以加少量盐帮助番茄出汁。",
            ),
            RecipeStep(order=4, content="倒回鸡蛋，加入盐调味，翻匀后出锅。"),
        ],
        common_failures=["鸡蛋炒老", "番茄不出汁", "糖放太多导致偏甜"],
        substitutions={"糖": "可以省略，或只放很少量提鲜。"},
        safety_notes=["热油下锅时避免锅中有明显水分。"],
    ),
    Recipe(
        id=2,
        name="酸辣土豆丝",
        description="口感清脆的家常素菜，关键是去除表面淀粉并大火快炒。",
        difficulty=Difficulty.EASY,
        time_minutes=20,
        beginner_friendly=True,
        seasons=["spring", "summer", "autumn", "winter"],
        ingredients=[
            RecipeIngredient(ingredient="土豆", amount="1-2个"),
            RecipeIngredient(ingredient="醋", amount="1勺"),
            RecipeIngredient(ingredient="辣椒", amount="适量", required=False),
            RecipeIngredient(ingredient="盐", amount="适量", required=False),
            RecipeIngredient(ingredient="食用油", amount="适量", required=False),
        ],
        steps=[
            RecipeStep(
                order=1,
                content="土豆切细丝，用清水反复冲洗表面淀粉。",
                beginner_tip="冲洗后沥干，口感会更脆。",
            ),
            RecipeStep(order=2, content="热锅倒油，下土豆丝大火快炒。"),
            RecipeStep(
                order=3,
                content="土豆丝断生后加入醋和盐，快速翻炒出锅。",
                beginner_tip="醋不要太晚放，否则脆感会变差。",
            ),
        ],
        common_failures=["土豆丝粘锅", "口感发软", "切丝粗细不均导致成熟度不一致"],
        substitutions={"辣椒": "不吃辣可以省略。", "醋": "可以用白醋或米醋替代。"},
        safety_notes=["切土豆丝时注意刀具安全。"],
    ),
    Recipe(
        id=3,
        name="可乐鸡翅",
        description="偏甜口的家常肉菜，新手需要注意收汁和甜度控制。",
        difficulty=Difficulty.MEDIUM,
        time_minutes=35,
        beginner_friendly=True,
        seasons=["spring", "summer", "autumn", "winter"],
        ingredients=[
            RecipeIngredient(ingredient="鸡翅", amount="8个"),
            RecipeIngredient(ingredient="可乐", amount="1罐"),
            RecipeIngredient(ingredient="生抽", amount="1勺"),
            RecipeIngredient(ingredient="姜", amount="几片", required=False),
        ],
        steps=[
            RecipeStep(
                order=1,
                content="鸡翅洗净，两面划刀。",
                risk_tip="处理生鸡肉后要清洗砧板和刀具。",
            ),
            RecipeStep(order=2, content="鸡翅焯水或煎至表面微黄。"),
            RecipeStep(order=3, content="加入可乐、生抽和姜片，小火炖煮。"),
            RecipeStep(
                order=4,
                content="汤汁变浓后收汁，确认鸡翅完全熟透后出锅。",
                risk_tip="禽肉必须充分加热。",
            ),
        ],
        common_failures=["可乐放太多导致过甜", "收汁过度糊锅", "鸡翅未熟透"],
        substitutions={"生抽": "可用少量盐加老抽替代，但味道会不同。"},
        safety_notes=["鸡翅必须充分加热，不能食用未熟禽肉。"],
    ),
    Recipe(
        id=4,
        name="红烧肉",
        description="步骤较多的经典肉菜，对火候和收汁要求更高。",
        difficulty=Difficulty.HARD,
        time_minutes=90,
        beginner_friendly=False,
        seasons=["spring", "autumn", "winter"],
        ingredients=[
            RecipeIngredient(ingredient="五花肉", amount="500g"),
            RecipeIngredient(ingredient="生抽", amount="2勺"),
            RecipeIngredient(ingredient="老抽", amount="1勺"),
            RecipeIngredient(ingredient="冰糖", amount="少量"),
            RecipeIngredient(ingredient="姜", amount="几片", required=False),
        ],
        steps=[
            RecipeStep(order=1, content="五花肉切块并焯水，去除浮沫。"),
            RecipeStep(
                order=2,
                content="炒糖色后放入五花肉翻炒上色。",
                risk_tip="炒糖色温度高，新手容易烫伤或炒焦。",
            ),
            RecipeStep(order=3, content="加入调料和热水，小火炖煮至软烂。"),
            RecipeStep(order=4, content="最后收汁，避免糊锅。"),
        ],
        common_failures=["糖色炒焦", "肉不够软烂", "收汁糊锅"],
        substitutions={"冰糖": "可用白糖少量替代。"},
        safety_notes=["炒糖色时注意高温烫伤。"],
    ),
]


USER_PROFILES: dict[str, dict[str, object]] = {
    "demo_user": {
        "liked_ingredients": ["鸡蛋", "土豆"],
        "disliked_styles": ["复杂肉菜"],
        "max_time_minutes": 30,
        "recent_recommendations": [1],
        "history": [
            {"recipe_id": 1, "rating": 5, "feedback": "简单好吃"},
            {"recipe_id": 4, "rating": 2, "feedback": "太难，收汁容易糊"},
        ],
    }
}
