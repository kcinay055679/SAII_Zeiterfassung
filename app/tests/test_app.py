import pytest

from app import NAME_COOKIE, create_app


@pytest.fixture
def client(tmp_path):
    return create_app(tmp_path).test_client()


def test_health_reports_healthy(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_health_fails_when_data_dir_is_not_writable(tmp_path):
    client = create_app(tmp_path).test_client()
    tmp_path.chmod(0o500)
    try:
        response = client.get("/health")
    finally:
        tmp_path.chmod(0o700)
    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"


def test_form_stamp_redirects_and_remembers_name(client):
    response = client.post("/stamp", data={"name": "Anna", "action": "EIN"})
    assert response.status_code == 303
    assert response.headers["Location"] == "/"
    assert f"{NAME_COOKIE}=Anna" in response.headers["Set-Cookie"]
    page = client.get("/").get_data(as_text=True)
    assert "WORKING" in page


def test_json_stamp_returns_created(client):
    response = client.post("/stamp", json={"name": "Anna", "action": "EIN", "note": "Kunde Meyer"})
    assert response.status_code == 201
    assert response.get_json()["note"] == "Kunde Meyer"
    assert client.get("/events").get_json()[0]["person"] == "Anna"


def test_invalid_transition_is_409(client):
    response = client.post("/stamp", json={"name": "Anna", "action": "PAUSE"})
    assert response.status_code == 409
    assert response.get_json()["allowed"] == ["EIN"]


def test_invalid_transition_in_form_shows_error(client):
    response = client.post("/stamp", data={"name": "Anna", "action": "AUS"})
    assert response.status_code == 409
    assert "not allowed" in response.get_data(as_text=True)


def test_unknown_action_is_400(client):
    assert client.post("/stamp", json={"name": "Anna", "action": "X"}).status_code == 400


def test_only_valid_buttons_are_enabled(client):
    client.post("/stamp", data={"name": "Anna", "action": "EIN"})
    page = client.get("/").get_data(as_text=True)
    assert 'value="EIN" disabled' in page
    assert 'value="PAUSE">' in page
    assert 'value="ZURUECK" disabled' in page
    assert 'value="AUS">' in page


def test_user_input_is_escaped(client):
    payload = "<script>alert(1)</script>"
    client.post("/stamp", json={"name": payload, "action": "EIN", "note": payload})
    page = client.get("/").get_data(as_text=True)
    assert "<script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_security_headers(client):
    headers = client.get("/").headers
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert headers["X-Content-Type-Options"] == "nosniff"


def test_board_endpoint(client):
    client.post("/stamp", json={"name": "Anna", "action": "EIN"})
    assert client.get("/board").get_json()[0]["status"] == "WORKING"


def test_concurrent_health_checks_do_not_collide(tmp_path):
    """Kubernetes fires readiness and liveness probes at the same moment."""
    from concurrent.futures import ThreadPoolExecutor

    app = create_app(tmp_path)

    def probe(_):
        return app.test_client().get("/health").status_code

    with ThreadPoolExecutor(max_workers=8) as pool:
        codes = list(pool.map(probe, range(200)))
    assert set(codes) == {200}
