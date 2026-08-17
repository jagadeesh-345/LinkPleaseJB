# Known System Failure Modes & Tradeoffs

This document honestly outlines exact edge cases and conditions where failure can still occur in this system, along with the design tradeoffs made.

---

### 1. Process Crash Before Webhook Persistence
- **Scenario**: An incoming `POST /webhook` request is received by FastAPI, but the container or host process crashes before `await db.events.insert_one()` finishes writing to disk.
- **Consequence**: The event is lost from memory. Because the endpoint did not return HTTP 200, the external platform (Pseudogram) must retry sending the webhook event. If the external platform does not implement retries, the event is permanently lost.

---

### 2. Process Crash Between Remote 202 Accepted and Local DB Update
- **Scenario**: The worker successfully dispatches a DM via `POST /v1/dm/send`, receiving HTTP 202 with a `dm_id`. The application crashes or dies immediately before updating the MongoDB job document with `status: accepted` and `dm_id`.
- **Consequence**: On application restart, MongoDB still shows the job in `QUEUED` / `SENDING` status. The worker will re-attempt sending the DM. However, because the outbound request includes the deterministic `Idempotency-Key: rule_id:user_id`, the external Pseudogram API will recognize the duplicate request and return the existing `dm_id` or ignore duplicate execution.

---

### 3. Comment Deletion Race Condition with In-Flight HTTP Request
- **Scenario**: A user comments "PRICE", triggering a DM job. The worker initiates an HTTP request `POST /v1/dm/send`. Concurrently, the user deletes their comment, sending a `comment.deleted` webhook.
- **Consequence**: If the `comment.deleted` event arrives while the HTTP POST is already in flight over the wire, the deletion handler updates MongoDB to `status: cancelled`, but cannot recall or undo the HTTP request already processed by Pseudogram. The DM will still be delivered.

---

### 4. Temporary Database Unavailability
- **Scenario**: MongoDB experiences a network partition or failover while the webhook endpoint or background worker is operating.
- **Consequence**: Database-level unique constraints (`event_id` and `rule_id + user_id`) cannot be evaluated. The `/webhook` endpoint will catch database exceptions and return HTTP 500/503, prompting the webhook provider to retry delivery later when MongoDB recovers.

---

### 5. Persistent External Rate Limit Exhaustion under Heavy Load Spike
- **Scenario**: 10,000 unique comments arrive within a 1-minute window. The external API strictly enforces a rate limit of 10 requests per 60 seconds.
- **Consequence**: The application-side rate limiter and persistent queue hold the jobs safely in MongoDB in `QUEUED` status. However, processing all 10,000 jobs will take approximately 16.6 hours. If users expect instantaneous DM delivery under massive burst volume, delivery will be delayed due to external rate limit constraints.
