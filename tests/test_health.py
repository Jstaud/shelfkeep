def test_healthz_is_public(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_readyz_needs_db(auth_client):
    response = auth_client.get("/readyz")
    assert response.status_code == 200
    assert response.json()["database"] == "up"


def test_library_redirects_when_signed_out(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_api_is_protected(client):
    response = client.get("/api/books")
    assert response.status_code == 401
