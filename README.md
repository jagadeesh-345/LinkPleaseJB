# LinkPlease

LinkPlease automates Instagram for creators. When a user comments a specific keyword, the system automatically sends them the correct DM.

Built as a resilient backend to handle a hostile API.

## Live URL
🚀 **Live API / Swagger Docs:** [https://linkpleasejb-production-55a4.up.railway.app/docs](https://linkpleasejb-production-55a4.up.railway.app/docs)

## Features Completed
- **Part A:** Rule creation, duplicate prevention, background queueing.
- **Part B:** Webhook HMAC signature verification, accurate live `/stats`.
- **Part C:** Delivery reconciliation, comment.deleted handling, rate-limit protection.

## Tech Stack
- FastAPI (Python)
- MongoDB
- Railway
