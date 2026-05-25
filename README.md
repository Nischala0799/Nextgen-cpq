# NextGen CPQ – Quoting System

## Project Overview
NextGen CPQ is a modular, enterprise-style quoting system designed to support product configuration, pricing logic, discounts, and quote generation. The system is modeled after real-world CPQ platforms and emphasizes clean separation between configuration rules, pricing logic, and API/UI layers.

This project is intentionally designed to be extensible, maintainable, and representative of production-grade CPQ systems used in enterprise environments.

## Core Functional Scope
- Product catalog with products, SKUs, bundles, and configurable attributes
- Configuration rules for required options and incompatible selections
- Pricing engine supporting base pricing, quantity-based pricing, and term-based pricing
- Discount logic (manual and rule-based)
- Quote management with versioning and full price breakdown

## Technical Stack (Initial)
- Language: Python 3.11+
- API Framework: FastAPI
- Data Validation: Pydantic
- Testing: pytest
- Storage: In-memory (initial phase)

## Project Structure
- `packages/domain` – core CPQ domain models and business logic
- `apps/api` – FastAPI application exposing CPQ functionality
- `docs` – architecture and design notes
- `tests` – unit and integration tests

## How to Run

### Prerequisites
- Python 3.11+

### 1. Create and activate a virtual environment
```bash
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows
```

### 2. Install dependencies
```bash
pip install -e packages/domain
pip install -e apps/api
```

### 3. Start the API server
```bash
uvicorn api.main:app --reload --app-dir apps
```

The API will be available at `http://127.0.0.1:8000`.
Interactive docs (Swagger UI) at `http://127.0.0.1:8000/docs`.

### 4. Run the tests
```bash
pytest tests/
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/quotes` | Create a new quote |
| `GET` | `/quotes/{quote_id}` | Get a quote by ID |
| `POST` | `/quotes/{quote_id}/lines` | Add a line item |
| `DELETE` | `/quotes/{quote_id}/lines/{line_id}` | Remove a line item |
| `POST` | `/quotes/{quote_id}/finalize` | Finalize a quote |
| `GET` | `/health` | Health check |
