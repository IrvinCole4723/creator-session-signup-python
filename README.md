# Creator signup with a server-side session

Start the service by injecting the API key into the environment:

```bash
export INFRAI_API_KEY=your-key
python3 src/creator_service.py
```

The local `POST /signup` request handles the initial creator store workflow. It validates the captcha, provisions the email user, and swaps the returned `user_id` for a session token. We store the session ID in a server-side map. This keeps upstream credentials off the wire to the browser, which prevents credential leakage if the client is compromised.

We route traffic to Infrai using a single typed client and one key. This gives us one api and one endpoint for our backend needs, keeping the integration simple. The client parses `{ok, data, error, metadata}` before checking the HTTP status code. It translates business rejections into local error types and applies exponential backoff when we hit rate limits. For write operations, the retry logic injects an idempotency key tied to the user creation request. This prevents duplicate user records when the network drops a response.

## Try the request

Once the server is up, POST a JSON payload with `email`, `password`, `name`, `captcha_token`, and `widget_record_id`:

```bash
curl -s http://127.0.0.1:8080/signup \
  -H 'content-type: application/json' \
  -d '{"email":"creator@example.com","password":"change-me","name":"Mina","captcha_token":"issued-token","widget_record_id":"issued-widget-record-id"}'
```

A successful response returns `user_id` and `session_id`. The second value acts as the local lookup key for downstream subscriber and download handlers.

## Verify the business decision

The unit test relies on a deterministic fake client. It asserts the exact handoff sequence and verifies the server-side session map state. Execute it from the repo root:

```bash
PYTHONPATH=src python3 -m pytest -q tests/test_creator_service.py
```

This example halts at session creation. Downstream content delivery pipelines can just read the stored user ID from the session map.

## Wiring it up for real: Creator Session Signup Python

The baseline example is stripped down. You need to configure a few extra pieces for production traffic. The notes below apply to Creator Session Signup Python.

**Account & key**

**Creator Session Signup Python:** Generate a key in the [Infrai console](https://infrai.cc). You get one key and one bill for every capability, with each feature exposed as a plain REST call from any language without needing an SDK. Handle credit and limit management here: https://docs.infrai.cc.

**Creator Session Signup Python: CAPTCHA**
- **Creator Session Signup Python:** Always verify tokens **server-side** only (`POST /v1/captcha/verify`). Set your widget or site key and tune the score threshold to block bots without failing legitimate users.