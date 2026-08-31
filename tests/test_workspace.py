from pathlib import Path


def test_workspace_is_three_panes(auth_client):
    page = auth_client.get("/")
    assert page.status_code == 200
    assert "pane pane-nav" in page.text
    assert "pane pane-stage" in page.text
    assert "pane pane-inspect" in page.text
    assert "Collections" in page.text
    assert "Rooms" in page.text
    assert 'class="nav-value"' in page.text
    assert "Delicious Library" not in page.text or "Not affiliated" in page.text
    assert "Delicious Monster" in page.text  # affiliation disclaimer only


def test_workspace_js_refreshes_inventory_summary():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "function rollupInventory(" in script
    assert 'summary.textContent = `${totals.items} household items · $${formatted}`' in script
    assert "rollupInventory()" in script
    assert script.index("function rollupInventory(") < script.index("function syncNav(")
