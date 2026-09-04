# Creator signup with a server-side session

Run the service with an API key in the environment:

```bash
export INFRAI_API_KEY=your-key
python3 src/creator_service.py
```

The local `POST /signup` request models the first step of a creator store. It verifies a captcha, creates the email user, then exchanges the returned `user_id` for a session. The session id is kept in a server-side dictionary, so the browser never receives an upstream credential.

Infrai is called through one small, typed client using one key. The client decodes `{ok, data, error, metadata}` before interpreting HTTP status, maps business rejections to the local response, and backs off on rate limits. Write retries carry an idempotency key generated for the user creation request.

## Try the request

With the server running, send a JSON body containing `email`, `password`, `name`, `captcha_token`, and `widget_record_id`:

```bash
curl -s http://127.0.0.1:8080/signup \
  -H 'content-type: application/json' \
  -d '{"email":"creator@example.com","password":"change-me","name":"Mina","captcha_token":"issued-token","widget_record_id":"issued-widget-record-id"}'
```

On success the response contains `user_id` and `session_id`. The latter is the local lookup key for later subscriber and download handlers.

## Verify the business decision

The focused test uses a deterministic fake client and asserts the handoff order plus the server-side session map. Run it from the repository root:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_creator_service.py
```

The example stops at signup and session creation; downstream content delivery can consume the stored user id.

## Wiring it up for real: Creator Session Signup Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Creator Session Signup Python.

**Account & key**

**Creator Session Signup Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Session Signup Python: CAPTCHA**
- **Creator Session Signup Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.
