# Decisions

**Who this is for:** reviewers, and anyone asking "why does it work this way?"

To change a decision, don't edit its row. Add a new row that replaces it, and mark the old one "Replaced by N".

| # | Problem | What we picked | What we get | Why not other ways | Cost | Status |
|---|---|---|---|---|---|---|
| 1 | Which language and framework for the service | Python with FastAPI and Pydantic | One Pydantic model gives request validation and the output schema for Claude | Spring Boot: I know it well, but this project is also for learning Python | Python is newer to me, so review takes longer | Accepted |
| 2 | How to manage Python versions and dependencies | uv | One tool for the Python version, the environment and a lockfile | pip + venv: more steps, no lockfile by default. Poetry: slower, needs Python installed separately | One more tool for contributors to install | Accepted |
| 3 | Status code for invalid input | 422, FastAPI's default | Same behaviour on every endpoint, no extra code | 400 (Spring's default): would need a custom exception handler | Clients used to 400 have to handle 422 | Accepted |

## Details for developers

- **3.** To change it later, add an exception handler for `RequestValidationError`.
