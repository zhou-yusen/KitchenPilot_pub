import argparse
import json
from urllib import request


NO_PROXY_OPENER = request.build_opener(request.ProxyHandler({}))


def get_json(url: str) -> dict:
    with NO_PROXY_OPENER.open(url, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post_json(url: str, payload: dict) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with NO_PROXY_OPENER.open(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def show(title: str, value: dict) -> None:
    print(f"\n===== {title} =====")
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="串联验证 KitchenPilot 后端核心接口。")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="demo_user")
    args = parser.parse_args()

    print("KitchenPilot API 可视化验证")
    print(f"Base URL: {args.base_url}")

    show("健康检查", get_json(f"{args.base_url}/health"))
    show(
        "菜谱问答",
        post_json(
            f"{args.base_url}/api/chat",
            {"query": "土豆丝怎么炒得脆？", "user_id": args.user_id},
        ),
    )
    show(
        "食材推荐",
        post_json(
            f"{args.base_url}/api/recommend/ingredients",
            {"user_id": args.user_id, "ingredients": ["鸡蛋", "番茄", "土豆"]},
        ),
    )
    show("每日推荐", get_json(f"{args.base_url}/api/recommend/daily/{args.user_id}"))


if __name__ == "__main__":
    main()
