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


def test_workspace_js_resets_book_form_before_fill():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "function resetBookForm(" in script
    fill_fn = script.split("function fillBookForm(")[1].split("function ")[0]
    assert "resetBookForm()" in fill_fn
    assert fill_fn.index("resetBookForm()") < fill_fn.index("Object.entries")
    assert "resetBookForm()" in script.split("if (!data.found)")[1].split("return;")[0]


def test_workspace_js_stops_camera_if_scanner_setup_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    setup_fail = script.split('alert("Camera is not available. Type the ISBN instead.")')[0][-280:]
    assert "await stopScan()" in setup_fail
    assert 'closeSheet("scanner")' in setup_fail
