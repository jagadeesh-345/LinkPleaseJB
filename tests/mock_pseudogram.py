from typing import Dict, Optional
import httpx


class MockPseudogramAPI:
    """
    In-memory mock simulator for Pseudogram API.
    Used during tests to intercept HTTP calls via httpx.MockTransport or respx.
    """

    def __init__(self):
        self.dms: Dict[str, Dict] = {}
        self.fail_next_send_with: Optional[int] = None
        self.send_count = 0
        self.status_query_count = 0

    def mock_handler(self, request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        # Check API Key Header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return httpx.Response(401, json={"error": "Unauthorized: Missing API Key"})

        # Send DM Endpoint: POST /v1/dm/send
        if method == "POST" and url_path.endswith("/v1/dm/send"):
            self.send_count += 1
            if self.fail_next_send_with:
                code = self.fail_next_send_with
                self.fail_next_send_with = None
                if code == 429:
                    return httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "Rate limit exceeded"})
                elif code == 500:
                    return httpx.Response(500, json={"error": "Internal Server Error"})
                elif code == 400:
                    return httpx.Response(400, json={"error": "Invalid request payload"})

            dm_id = f"dm_{self.send_count:06d}"
            self.dms[dm_id] = {"status": "delivered"}  # Default to delivered for instant test reconciliation
            return httpx.Response(202, json={"dm_id": dm_id, "status": "queued"})

        # Check Status Endpoint: GET /v1/dm/{dm_id}
        if method == "GET" and "/v1/dm/" in url_path:
            self.status_query_count += 1
            dm_id = url_path.split("/v1/dm/")[-1]
            dm_data = self.dms.get(dm_id)
            if not dm_data:
                return httpx.Response(404, json={"error": "DM not found"})
            return httpx.Response(200, json={"dm_id": dm_id, "status": dm_data["status"]})

        return httpx.Response(404, json={"error": "Endpoint not found"})
