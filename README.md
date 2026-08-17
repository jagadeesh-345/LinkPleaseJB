# LinkPlease — Pseudogram Automation Backend

This is the backend service for LinkPlease, automating Instagram DMs based on comment keywords. Built for the LinkPlease Tech Intern Assignment.

## ?? Live Deployment
- **Base URL:** [https://linkpleasejb-production-55a4.up.railway.app](https://linkpleasejb-production-55a4.up.railway.app)
- **API Docs (Swagger):** [https://linkpleasejb-production-55a4.up.railway.app/docs](https://linkpleasejb-production-55a4.up.railway.app/docs)

## ?? Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MongoDB (Motor Async Driver)
- **Deployment:** Railway.app

## ? Features Implemented (Parts A, B, & C)
* **High-Throughput Webhook (`/webhook`):** Non-blocking architecture that guarantees a `200 OK` response within milliseconds.
* **Idempotency & Duplicate Prevention:** Utilizes strict MongoDB unique indexes to block duplicate `event_id` payloads and ensure a user is never DMed twice for the same rule.
* **Background Worker:** A custom async worker handles the actual HTTP calls to the Pseudogram API, decoupling external network latency from webhook ingestion.
* **Rate Limiting:** Asynchronous sliding-window rate limiter respects the strict 10 requests / 60 seconds limit, with exponential backoff on `429` and `500` errors.
* **HMAC Security:** Cryptographically verifies `X-PseudoGram-Signature` to reject forged webhook requests.
* **Status Reconciliation:** Continually verifies "accepted" DMs to update final terminal states (Delivered vs Failed).
* **Comment Deletions:** Gracefully cancels pending/queued DM jobs if a user deletes their comment before dispatch.
* **Real-time Stats (`/stats`):** Queries live aggregate counts directly from the database for perfect accuracy under load.

See `FAILURES.md` for documented edge cases and systemic constraints.
