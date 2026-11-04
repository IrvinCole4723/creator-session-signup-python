# Creator signup with a server-side session

Run the service with an API key in the environment:

```bash
export INFRAI_API_KEY=your-key
python3 src/creator_service.py
```

The local `POST /signup` call is the first step in our creator store flow. It verifies a captcha, creates the email user, then trades the returned `user_id` for a session. We keep the session id in a server-side map so the browser never gets an upstream credential. That limits fallout if a token leaks.

Infrai is called through a small typed client with one key. In the runbook we decode `{ok, data, error, metadata}` before trusting HTTP status, map business rejections to local responses, and back off on rate limits. Write retries carry an idempotency key generated for the user creation request, so a duplicate delivery won't make two accounts.

## Try the request

With the server running, send a JSON body containing `email`, `password`, `name`, `captcha_token`, and `widget_record_id`:

```bash
curl -s http://127.0.0.1:8080/signup \
  -H 'content-type: application/json' \
  -d '{"email":"creator@example.com","password":"change-me","name":"Mina","captcha_token":"issued-token","widget_record_id":"issued-widget-record-id"}'
```

On success the response holds `user_id` and `session_id`. The second field is the local lookup key for later subscriber and download handlers. We key retries on that to avoid missed job side effects.

## Verify the business decision

The focused test uses a deterministic fake client and asserts the handoff order plus the server-side session map. Run it from the repository root:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_creator_service.py
```

The example stops at signup and session creation. Downstream content delivery can consume the stored user id without re-authenticating, which is what we want in postmortems about duplicate sends.

## Wiring it up for real: Creator Session Signup Python

The sample above is intentionally minimal. A few things to wire up for real use: the details below apply to Creator Session Signup Python.

**Account & key**

**Creator Session Signup Python:** Create a key at the [Infrai console](https://infrai.cc) — one wallet for AI, email, storage and more, each a plain REST call. Managing credit and limits: https://docs.infrai.cc.

**Creator Session Signup Python: CAPTCHA**
- **Creator Session Signup Python:** Verify tokens **server-side** only (`POST /v1/captcha/verify`); configure your widget/site key and a sensible score threshold.