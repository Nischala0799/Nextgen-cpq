# cpq-domain

This package contains the core domain models and business logic for the
NextGen CPQ quoting system.

The domain layer is intentionally framework-agnostic and is designed to be
reused by:
- `apps/api` (FastAPI layer)
- future UI or integration services

All configuration rules, pricing logic, and quote models live here.
