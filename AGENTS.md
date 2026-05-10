# KitchenPilot Agent Notes

## Collaboration Boundary

- When the user asks for planning, architecture, or discussion, do not edit files unless they explicitly ask for implementation.
- Before broad refactors or generated scaffolding, state the intended file changes and wait if the user requested planning only.
- Preserve existing user changes. Do not revert or delete files unless explicitly requested.

## Project Shape

- Monorepo-style project with backend-first implementation.
- `backend/` contains the Python FastAPI service.
- `frontend/` is currently a placeholder only.
- `docs/` contains planning and architecture notes.

## Backend

- Package root: `backend/src/kitchenpilot`.
- Dependency manager: `uv`.
- Test command:

```powershell
cd backend
uv run pytest
```

- Dev server command:

```powershell
cd backend
uv run uvicorn kitchenpilot.main:app --reload
```

## Agent Layout

The agent code is organized under `backend/src/kitchenpilot/agent`:

```text
agent/
├── graph.py
├── state.py
├── router.py
├── nodes/
│   ├── intent_router.py
│   ├── recipe_qa_node.py
│   ├── recommendation_node.py
│   ├── meal_plan_node.py
│   ├── quality_check_node.py
│   └── _legacy.py
└── subgraphs/
```

- `graph.py` owns the LangGraph workflow wiring.
- `state.py` owns `AgentState` and `AgentStateModel`.
- `nodes/` owns node-level behavior.
- `router.py` is a compatibility re-export for older imports.
- `nodes/_legacy.py` still contains several moved node implementations and should be split further when refactoring.

## Current Known Issues

- Many Chinese strings are mojibake/garbled. Tests may still pass because test inputs contain the same garbled strings.
- SQLite `RecipeService`, Qdrant seed/search, embedding provider, RAG fallback, and basic retrieval rerank are implemented.
- Real Qdrant seed/search has been smoke-tested with the fixed RAG demo questions, but RAG answer quality still needs prompt and fallback improvements.
- Recommendation logic is still rule-based MVP and needs stronger personalization, scoring documentation, and broader tests.
- README may lag behind `Plan.md` and should be updated before project handoff or demo.
- Frontend is not implemented.

## Development Notes

- Prefer small, scoped changes.
- Keep imports compatible where possible; several tests still rely on public re-export paths.
- Use `rg` for code search.
- When reading Chinese text files in PowerShell, use `Get-Content <path> -Encoding UTF8` to avoid mojibake.
- Run `uv run pytest` after backend behavior or import-structure changes.
- For scoped lint verification, prefer `uv run ruff check <changed-files>` because the full repo currently has pre-existing Ruff issues.
