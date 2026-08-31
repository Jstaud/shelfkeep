def test_workspace_is_three_panes(auth_client):
    page = auth_client.get("/")
    assert page.status_code == 200
    assert "pane pane-nav" in page.text
    assert "pane pane-stage" in page.text
    assert "pane pane-inspect" in page.text
    assert "Collections" in page.text
    assert "Rooms" in page.text
    assert "Delicious Library" not in page.text or "Not affiliated" in page.text
    assert "Delicious Monster" in page.text  # affiliation disclaimer only
