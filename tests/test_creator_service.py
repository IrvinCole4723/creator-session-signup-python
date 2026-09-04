from creator_service import SignupRequest, SignupService


class FakeClient:
    def __init__(self):
        self.calls = []

    def post(self, path, body):
        self.calls.append((path, body))
        if path.endswith("captcha/verify"):
            return {"ok": True, "data": {}, "error": None, "metadata": {}}
        if path.endswith("auth/user/create"):
            return {"ok": True, "data": {"user_id": "user-7"}, "error": None, "metadata": {}}
        return {"ok": True, "data": {"session_id": "sess-9"}, "error": None, "metadata": {}}


def test_signup_links_captcha_user_and_server_session():
    client = FakeClient()
    service = SignupService(client)
    result = service.signup(SignupRequest("a@b.test", "pw", "A", "captcha", "widget-3"))
    assert result == {"session_id": "sess-9", "user_id": "user-7"}
    assert [path for path, _ in client.calls] == [
        "/v1/captcha/verify", "/v1/auth/user/create", "/v1/auth/session/create"
    ]
    assert client.calls[0][1] == {
        "widget_record_id": "widget-3", "token": "captcha", "action": "signup"
    }
    assert service.sessions["sess-9"] == "user-7"
