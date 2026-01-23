# NextGen CPQ – Architecture Overview

## Design Objectives
- Build a modular, enterprise-style CPQ quoting system
- Maintain clear separation between:
  - Product configuration logic
  - Pricing and discount logic
  - API orchestration layer
- Enable future extensibility for approvals, renewals, and integrations

---

## High-Level Architecture

### 1. Domain Layer (`packages/domain`)
The domain layer contains all core CPQ business logic and is independent of any web framework.

Responsibilities:
- Product catalog models (products, SKUs, bundles, attributes)
- Configuration rules and validation
- Pricing engine and discount policies
- Quote and quote version management

This layer is designed to be reusable and independently testable.

---

### 2. API Layer (`apps/api`)
The API layer exposes CPQ functionality via HTTP endpoints.

Responsibilities:
- Accept quote configuration requests
- Invoke domain services for validation and pricing
- Return structured quote and pricing responses

The API layer remains thin and delegates all business logic to the domain layer.

---

### 3. Persistence (Initial and Future)
- Initial implementation uses in-memory storage
- Future phases may introduce:
  - PostgreSQL for product and quote persistence
  - Redis for session and draft quote management

---

### 4. UI Layer (Future)
A lightweight UI will allow users to:
- Configure products and options
- View pricing breakdowns
- Generate and manage quotes

The UI will communicate exclusively through the API layer.

---

## Extensibility Considerations
The architecture supports:
- Adding new pricing rules without modifying existing logic
- Introducing approval workflows for discounts
- Integrating with external CRM or billing systems

---

## Testing Strategy
- Unit tests for domain logic
- Rule-level tests for pricing and configuration validation
- Integration tests for API endpoints
