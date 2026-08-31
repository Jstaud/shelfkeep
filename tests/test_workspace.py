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


def test_workspace_js_clears_form_when_lookup_request_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_fail = script.split("Lookup failed. You can still add the book manually.")[1][:240]
    assert "resetBookForm()" in after_fail
    assert "renderLookup([])" in after_fail
    assert "applyLookupQuery(q)" in after_fail


def test_workspace_js_ignores_superseded_lookups():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "let lookupGeneration = 0" in script
    assert "const generation = ++lookupGeneration" in script
    assert "if (generation !== lookupGeneration) return" in script
    assert script.count("if (generation !== lookupGeneration) return") >= 2


def test_workspace_js_resets_book_form_after_success():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_create = script.split("state.books.unshift(book);")[1].split("} catch")[0]
    assert "resetBookForm()" in after_create
    assert "renderLookup([])" in after_create
    assert after_create.index("resetBookForm()") < after_create.index('closeSheet("add-book")')


def test_workspace_js_resets_item_form_after_success():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    item_submit = script.split('$("#item-form")')[1].split("$(\"#room-form\")")[0] if '$("#room-form")' in script.split('$("#item-form")')[1] else script.split('$("#item-form")')[1]
    # After the item POST succeeds, reset the form so the next add is blank.
    success = item_submit.split("const item = await api")[1].split("} catch")[0]
    assert "event.target.reset()" in success
    assert success.index("event.target.reset()") < success.index('closeSheet("add-item")')


def test_workspace_js_stops_camera_if_scanner_setup_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    setup_fail = script.split('alert("Camera is not available. Type the ISBN instead.")')[0][-280:]
    assert "await stopScan()" in setup_fail
    assert 'closeSheet("scanner")' in setup_fail
