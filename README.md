# LinkPlease 

This is the backend service for LinkPlease, automating Instagram DMs based on comment keywords. Built for the LinkPlease Tech Intern Assignment.

## 🚀 Live Deployment
- **Base URL:** [https://linkpleasejb-production-55a4.up.railway.app](https://linkpleasejb-production-55a4.up.railway.app)
- **API Docs (Swagger):** [https://linkpleasejb-production-55a4.up.railway.app/docs](https://linkpleasejb-production-55a4.up.railway.app/docs)
- **Loom Video:** [Watch the architectural overview here](https://www.loom.com/share/dc1e470b1f494427a88e525809c00a83)

## 🛠 Tech Stack
- **Framework:** FastAPI (Python)
- **Database:** MongoDB (Motor Async Driver)
- **Deployment:** Railway.app

## ⚙️ Architecture & Workflow

The system is designed around a fast-ingestion, asynchronous-processing model to ensure no webhooks are dropped and the hostile API is handled safely.

### 1. Webhook Ingestion (`POST /webhook`)
- **Fast Acknowledgment:** When an event arrives, the webhook instantly verifies the `HMAC-SHA256` signature.
- **Idempotency Check:** It attempts to save the event to MongoDB. A unique index on `event_id` ensures duplicate payloads are safely ignored at the database level.
- **Rule Matching & Queueing:** If the comment text matches an active rule, a DM Job is created. Another unique index on `(rule_id, user_id)` guarantees a user never receives the same DM twice.
- **Immediate Response:** The endpoint returns a `200 OK` within milliseconds, passing all actual dispatch work to the background worker.

### 2. Background Dispatch Worker
- **Async Polling:** A background process continually polls MongoDB for jobs in the `queued` or `retrying` state.
- **Rate Limiting:** Before dispatch, the worker acquires a token from an in-memory asynchronous sliding-window rate limiter, enforcing a strict 10 requests / 60 seconds limit.
- **Error Handling:** If the Pseudogram API returns a `429` (Rate Limit) or `500` (Internal Error), the job is bumped back to the queue with exponential backoff scheduling.

### 3. Status Reconciliation
- Jobs that return `202 Accepted` are not guaranteed to be delivered.
- A secondary loop periodically checks the `/v1/dm/{dm_id}` endpoint to reconcile `accepted` jobs into terminal states (`delivered` or `failed`).

### 4. Cancellation (Comment Deletion)
- If a `comment.deleted` event arrives, the webhook immediately marks any pending DM jobs associated with that `comment_id` as `cancelled`, preventing unwanted dispatches.

## 🌟 Features Implemented (Parts A, B, & C)
* **High-Throughput Webhook:** Non-blocking architecture.
* **Idempotency & Duplicate Prevention:** Perfect duplicate filtering using MongoDB compound indexes.
* **Background Worker:** Decoupled external network latency from webhook ingestion.
* **Rate Limiting:** Sliding-window implementation with backoff.
* **HMAC Security:** Cryptographically verified incoming requests.
* **Status Reconciliation:** Eventual consistency for "accepted" statuses.
* **Comment Deletions:** Graceful queue cancellation.
* **Real-time Stats (`/stats`):** Queries live aggregate counts for perfect accuracy.

See [`FAILURES.md`](./FAILURES.md) for documented edge cases and systemic constraints.
