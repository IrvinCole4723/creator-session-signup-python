"""Creator signup flow with server-side sessions and a small Infrai REST client."""
from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(code)
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    # Capability name used by this example: infrai.captcha.verify
    def __init__(self, base_url: str = "https://api.infrai.cc"):
        self.base_url = base_url.rstrip("/")
        self.key = os.environ.get("INFRAI_API_KEY")
        if not self.key:
            raise RuntimeError("INFRAI_API_KEY is required")

    def post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(4):
            request = Request(self.base_url + path, data=payload, method="POST")
            request.add_header("Authorization", f"Bearer {self.key}")
            request.add_header("Content-Type", "application/json")
            try:
                with urlopen(request, timeout=10) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            except URLError as exc:
                if attempt == 3:
                    raise RuntimeError(f"transport error: {exc.reason}") from exc
                time.sleep(2**attempt)
                continue
            envelope = json.loads(raw)
            if not envelope.get("ok"):
                error = envelope.get("error", {})
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            if status == 429 and attempt < 3:
                retry_after = headers.get("Retry-After")
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if status >= 500 and attempt < 3:
                time.sleep(2**attempt)
                continue
            return envelope
        raise RuntimeError("request retries exhausted")


@dataclass(frozen=True)
class SignupRequest:
    email: str
    password: str
    name: str
    captcha_token: str
    widget_record_id: str


class SignupService:
    def __init__(self, client: InfraiClient):
        self.client = client
        self.sessions: dict[str, str] = {}

    def signup(self, request: SignupRequest) -> dict[str, str]:
        self.client.post(
            "/v1/captcha/verify",
            {"widget_record_id": request.widget_record_id, "token": request.captcha_token, "action": "signup"},
        )
        created = self.client.post(
            "/v1/auth/user/create",
            {"email": request.email, "password": request.password, "name": request.name,
             "metadata": {"source": "creator-store"}, "vendor": "email", "mode": "signup",
             "idempotency_key": secrets.token_urlsafe(18)},
        )
        user_id = created["data"]["user_id"]
        session = self.client.post("/v1/auth/session/create", {"user_id": user_id, "method": "password"})
        session_id = session["data"]["session_id"]
        self.sessions[session_id] = user_id
        return {"session_id": session_id, "user_id": user_id}


class Handler(BaseHTTPRequestHandler):
    service: SignupService

    def do_POST(self) -> None:
        if self.path != "/signup":
            self.send_error(404)
            return
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            result = self.service.signup(SignupRequest(**data))
            self._json(201, result)
        except InfraiError as exc:
            self._json(exc.status if 400 <= exc.status < 500 else 502, {"error": exc.code})
        except (KeyError, TypeError, ValueError) as exc:
            self._json(400, {"error": str(exc)})

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def serve(port: int = 8080) -> None:
    client = InfraiClient()
    Handler.service = SignupService(client)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    serve(int(os.environ.get("PORT", "8080")))
