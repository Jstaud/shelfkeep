from pathlib import Path

COMPETITOR_NAMES = (
    "Delicious Monster",
    "Delicious Library",
    "Under My Roof",
    "Delicious",
)


def _assert_stand_alone_chrome(html: str) -> None:
    for name in COMPETITOR_NAMES:
        assert name not in html
    assert "Open Library" in html
    assert "Shelfkeep" in html


def test_workspace_is_three_panes(auth_client):
    page = auth_client.get("/")
    assert page.status_code == 200
    assert "pane pane-nav" in page.text
    assert "pane pane-stage" in page.text
    assert "pane pane-inspect" in page.text
    assert "Collections" in page.text
    assert "Rooms" in page.text
    assert "Borrowers" in page.text
    assert "Out now" in page.text
    assert 'data-media-filter="game"' in page.text
    assert 'class="nav-value"' in page.text
    _assert_stand_alone_chrome(page.text)


def test_login_and_openapi_have_no_competitor_names(client, auth_client):
    login = client.get("/login")
    assert login.status_code == 200
    for name in COMPETITOR_NAMES:
        assert name not in login.text
    assert "Shelfkeep" in login.text

    spec = auth_client.get("/openapi.json")
    assert spec.status_code == 200
    description = spec.json()["info"]["description"]
    for name in COMPETITOR_NAMES:
        assert name not in description
    assert "self-hosted catalog" in description.lower()


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
    assert "lookupGeneration += 1" in after_create
    assert after_create.index("lookupGeneration += 1") < after_create.index("resetBookForm()")
    assert "resetBookForm()" in after_create
    assert "renderLookup([])" in after_create
    assert after_create.index("resetBookForm()") < after_create.index('closeSheet("add-book")')


def test_workspace_js_removes_empty_room_placeholder_on_first_room():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_room = script.split("state.rooms.push(room);")[1].split("} catch")[0]
    assert '$(".nav-empty")?.remove()' in after_room
    assert after_room.index('$(".nav-empty")?.remove()') < after_room.index('$(".nav-add")?.before(nav)')


def test_workspace_js_replaces_item_url_after_delete():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_delete = script.split("Remove this household item?")[1].split("actions.append(remove)")[0]
    assert "history.replaceState" in after_delete
    assert "`/rooms/${roomId}`" in after_delete or "/rooms/${roomId}" in after_delete
    assert after_delete.index("renderAll()") < after_delete.index("history.replaceState")


def test_workspace_js_replaces_book_url_after_delete():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_delete = script.split("Remove this volume from the shelf?")[1].split(
        "copy.querySelector(\".inspect-actions\")"
    )[0]
    assert "history.replaceState" in after_delete
    assert 'history.replaceState({}, "", "/")' in after_delete
    assert "history.pushState" not in after_delete
    assert after_delete.index("renderAll()") < after_delete.index("history.replaceState")


def test_workspace_js_resets_room_form_after_success():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    after_room = script.split("state.rooms.push(room);")[1].split("} catch")[0]
    assert "event.target.reset()" in after_room
    assert after_room.index("event.target.reset()") < after_room.index('closeSheet("add-room")')


def test_workspace_js_resets_item_form_after_success():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    item_submit = script.split('$("#item-form")')[1].split("$(\"#room-form\")")[0] if '$("#room-form")' in script.split('$("#item-form")')[1] else script.split('$("#item-form")')[1]
    # After the item POST succeeds, reset the form so the next add is blank.
    success = item_submit.split("const item = await api")[1].split("} catch")[0]
    assert "event.target.reset()" in success
    assert success.index("event.target.reset()") < success.index('closeSheet("add-item")')


def test_type_chips_stay_hidden_when_display_flex_is_set():
    css = Path("app/static/css/app.css").read_text(encoding="utf-8")
    assert ".type-chips[hidden]" in css
    assert "display: none" in css.split(".type-chips[hidden]")[1].split("}")[0]


def test_workspace_js_filters_library_by_media_type():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "state.mediaFilter = \"all\"" in script or "state.mediaFilter = 'all'" in script
    render = script.split("function renderBooks(")[1].split("function ")[0]
    assert "state.mediaFilter" in render
    assert "book.media_type" in render


def test_workspace_js_resets_catalog_sheet_on_close_and_new_add():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    close_fn = script.split('$("#add-book")?.addEventListener("close"')[1].split("});")[0]
    assert "resetBookForm()" in close_fn
    add_open = script.split("add.dataset.open = \"add-book\"")[1].split("openSheet(\"add-book\")")[0]
    assert "resetBookForm()" in add_open


def test_workspace_js_deletes_new_card_if_cover_upload_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    cover = script.split('data.set("cover", cover.files[0])')[1].split("if (editId)")[0]
    assert "catch (coverErr)" in cover
    assert "if (!editId)" in cover
    assert 'api(`/api/books/${book.id}`, { method: "DELETE" })' in cover
    assert "throw coverErr" in cover


def test_workspace_js_reconciles_edited_card_when_cover_upload_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    cover = script.split('data.set("cover", cover.files[0])')[1].split("if (editId)")[0]
    edit_arm = cover.split("throw coverErr")[1]
    assert "state.books[index] = { ...state.books[index], ...book }" in edit_arm
    assert "renderAll()" in edit_arm
    assert "Metadata saved, but the cover did not." in edit_arm
    assert "DELETE" not in edit_arm
    assert edit_arm.index("state.books[index]") < edit_arm.index("renderAll()")
    assert edit_arm.index("renderAll()") < edit_arm.index("Metadata saved, but the cover did not.")


def test_workspace_js_keeps_borrowers_route_after_loan_card_delete():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    book_delete = script.split("Remove this volume from the shelf?")[1].split(
        "copy.querySelector(\".inspect-actions\")"
    )[0]
    assert 'state.view === "borrowers"' in book_delete
    assert "state.selectedBookId = null" in book_delete
    assert 'dropLoansFor("book", book.id)' in book_delete
    assert "`/borrowers/${state.selectedBorrowerId}`" in book_delete
    assert '"/borrowers"' in book_delete
    assert book_delete.index('dropLoansFor("book", book.id)') < book_delete.index("state.selectedBookId = null")
    assert book_delete.index("state.selectedBookId = null") < book_delete.index("history.replaceState")
    borrowers_arm = book_delete.split('state.view === "borrowers"')[1].split("} else {")[0]
    assert 'history.replaceState({}, "", "/")' not in borrowers_arm
    item_delete = script.split("Remove this household item?")[1].split("actions.append(remove)")[0]
    assert 'state.view === "borrowers"' in item_delete
    assert "`/borrowers/${state.selectedBorrowerId}`" in item_delete


def test_workspace_js_drops_loans_when_volume_or_item_is_deleted():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "function dropLoansFor(" in script
    book_delete = script.split("Remove this volume from the shelf?")[1].split(
        "copy.querySelector(\".inspect-actions\")"
    )[0]
    assert 'dropLoansFor("book", book.id)' in book_delete
    assert book_delete.index('dropLoansFor("book", book.id)') < book_delete.index("renderAll()")
    item_delete = script.split("Remove this household item?")[1].split("actions.append(remove)")[0]
    assert 'dropLoansFor("item", item.id)' in item_delete
    assert item_delete.index('dropLoansFor("item", item.id)') < item_delete.index("renderAll()")


def test_workspace_js_can_lend_and_return():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    assert "function appendLoanActions(" in script
    assert "function markLoanReturned(" in script
    assert "Lend this" in script
    assert "Mark returned" in script
    assert 'api(`/api/loans/${loanId}/return`' in script


def test_service_worker_bumps_shell_cache_and_purges_old_ones():
    script = Path("app/static/sw.js").read_text(encoding="utf-8")
    assert 'const CACHE = "shelfkeep-shell-v11"' in script
    assert "shelfkeep-shell-v10" not in script
    activate = script.split('addEventListener("activate"')[1].split('addEventListener("fetch"')[0]
    assert "caches.keys()" in activate
    assert "caches.delete(key)" in activate
    assert "key !== CACHE" in activate
    assert "self.clients.claim()" in activate
    assert activate.index("caches.delete(key)") < activate.index("self.clients.claim()")


def test_workspace_js_stops_camera_if_scanner_setup_fails():
    script = Path("app/static/js/app.js").read_text(encoding="utf-8")
    setup_fail = script.split('alert("Camera is not available. Type the ISBN instead.")')[0][-280:]
    assert "await stopScan()" in setup_fail
    assert 'closeSheet("scanner")' in setup_fail
