import argparse
import json
from urllib import request


NO_PROXY_OPENER = request.build_opener(request.ProxyHandler({}))


def post_json(url: str, payload: dict) -> dict:
    """Send a POST request with JSON and parse the JSON response."""
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with NO_PROXY_OPENER.open(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    """Run this script from the command line."""
    parser = argparse.ArgumentParser(description="调用 /api/recommend 验证统一推荐接口。")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--user-id", default="demo_user")
    parser.add_argument("--recommendation-type", default="ingredients", choices=["ingredients", "daily"])
    parser.add_argument("--ingredients", nargs="+", default=["鸡蛋", "番茄", "土豆"])
    args = parser.parse_args()

    response = post_json(
        f"{args.base_url}/api/recommend",
        {
            "user_id": args.user_id,
            "recommendation_type": args.recommendation_type,
            "ingredients": args.ingredients,
        },
    )
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
