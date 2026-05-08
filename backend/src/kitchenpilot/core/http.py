import httpx


def auth_headers(api_key: str) -> dict[str, str]:
    """Build JSON headers with an optional bearer token."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def post_json(
    url: str,
    payload: dict[str, object],
    *,
    timeout: float,
    trust_env: bool,
    headers: dict[str, str] | None = None,
) -> dict[str, object]:
    """Send a JSON POST request and return a dictionary response."""
    with httpx.Client(timeout=timeout, trust_env=trust_env) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("LLM endpoint returned an unexpected payload.")
    return data
