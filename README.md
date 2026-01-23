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

## How to Run (Placeholder)
> Setup and execution instructions will be added once the initial API and domain layers are implemented.
