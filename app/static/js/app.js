const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function openSheet(id) {
  document.getElementById(id)?.showModal();
}
function closeSheet(id) {
  document.getElementById(id)?.close();
}
$$("[data-open]").forEach((btn) => {
  btn.addEventListener("click", () => openSheet(btn.dataset.open));
});

async function api(url, options = {}) {
  const response = await fetch(url, { credentials: "same-origin", ...options });
  if (response.status === 204) return null;
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { detail: text };
  }
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((d) => d.msg || d).join(" ")
      : detail || "Request failed";
    throw new Error(message);
  }
  return data;
}

function money(value) {
  if (value == null || value === "") return null;
  const n = Number(value);
  return Number.isFinite(n) ? n.toFixed(2) : String(value);
}

const rawState = $("#workspace-data");
const state = rawState
  ? JSON.parse(rawState.textContent)
  : { view: "library", books: [], rooms: [] };

state.books = state.books || [];
state.rooms = state.rooms || [];
state.filter = "";

function currentRoom() {
  return state.rooms.find((room) => room.id === state.selectedRoomId) || null;
}

function syncNav() {
  const libEm = $("[data-open-library] em");
  if (libEm) libEm.textContent = String(state.books.length);
  $$("[data-open-library]").forEach((el) => {
    el.classList.toggle("is-active", state.view === "library");
  });
  $$("[data-open-room]").forEach((el) => {
    const id = Number(el.dataset.openRoom);
    el.classList.toggle("is-active", id === state.selectedRoomId);
    const room = state.rooms.find((entry) => entry.id === id);
    const em = el.querySelector("em");
    if (room && em) em.textContent = String(room.item_count ?? room.items?.length ?? 0);
  });
}

function setStageChrome() {
  const kicker = $("#stage-kicker");
  const title = $("#stage-title");
  const add = $("#stage-add");
  if (!kicker || !title || !add) return;
  if (state.view === "library") {
    kicker.textContent = "The stacks";
    title.textContent = "Library";
    add.textContent = "Add a book";
    add.dataset.open = "add-book";
    add.onclick = () => openSheet("add-book");
  } else {
    const room = currentRoom();
    kicker.textContent = "Under this roof";
    title.textContent = room ? room.name : "Rooms";
    add.textContent = "Add an item";
    add.dataset.open = "add-item";
    add.onclick = () => {
      if (!state.selectedRoomId) {
        openSheet("add-room");
        return;
      }
      openSheet("add-item");
    };
  }
}

function placeholder(title, className) {
  const el = document.createElement("div");
  el.className = className;
  el.textContent = title;
  return el;
}

function matchesFilter(text) {
  if (!state.filter) return true;
  return (text || "").toLowerCase().includes(state.filter);
}

function renderStage() {
  const well = $("#stage-well");
  if (!well) return;
  well.replaceChildren();
  if (state.view === "library") {
    renderBooks(well);
  } else {
    renderItems(well);
  }
}

function renderBooks(well) {
  const books = state.books.filter((book) =>
    matchesFilter([book.title, book.authors, book.isbn].filter(Boolean).join(" "))
  );
  if (!books.length) {
    well.innerHTML = `<div class="empty-shelf"><p>The first shelf is empty. Add a book by ISBN, title, or by hand.</p></div>`;
    return;
  }
  const perRow = window.matchMedia("(max-width: 720px)").matches ? 4 : 6;
  for (let i = 0; i < books.length; i += perRow) {
    const row = document.createElement("div");
    row.className = "shelf-row";
    for (const book of books.slice(i, i + perRow)) {
      row.append(bookObject(book));
    }
    well.append(row);
  }
}

function bookObject(book) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "object" + (book.id === state.selectedBookId ? " is-selected" : "");
  btn.addEventListener("click", () => selectBook(book.id, true));
  const body = document.createElement("div");
  body.className = "object-body";
  if (book.cover_src) {
    const img = document.createElement("img");
    img.className = "object-art";
    img.src = book.cover_src;
    img.alt = "";
    img.addEventListener("error", () => img.replaceWith(placeholder(book.title, "object-ph")));
    body.append(img);
  } else {
    body.append(placeholder(book.title, "object-ph"));
  }
  const caption = document.createElement("span");
  caption.className = "object-title";
  caption.textContent = book.title;
  btn.append(body, caption);
  return btn;
}

function renderItems(well) {
  const room = currentRoom();
  if (!room) {
    well.innerHTML = `<div class="empty-shelf"><p>Add a room, then photograph what lives there.</p></div>`;
    return;
  }
  const items = (room.items || []).filter((item) =>
    matchesFilter([item.name, item.serial_number, item.brand].filter(Boolean).join(" "))
  );
  if (!items.length) {
    well.innerHTML = `<div class="empty-shelf"><p>This room is still settling in. Add something you would want on an insurance list.</p></div>`;
    return;
  }
  const perRow = window.matchMedia("(max-width: 720px)").matches ? 3 : 5;
  for (let i = 0; i < items.length; i += perRow) {
    const row = document.createElement("div");
    row.className = "shelf-row";
    for (const item of items.slice(i, i + perRow)) {
      row.append(itemObject(item));
    }
    well.append(row);
  }
}

function itemObject(item) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "object item-object" + (item.id === state.selectedItemId ? " is-selected" : "");
  btn.addEventListener("click", () => selectItem(item.id, true));
  const body = document.createElement("div");
  body.className = "object-body";
  if (item.photo_src) {
    const img = document.createElement("img");
    img.className = "object-art";
    img.src = item.photo_src;
    img.alt = "";
    body.append(img);
  } else {
    body.append(placeholder(item.name, "object-ph"));
  }
  const caption = document.createElement("span");
  caption.className = "object-title";
  caption.textContent = item.name;
  btn.append(body, caption);
  return btn;
}

function inspectBook(book) {
  const pane = $("#inspector");
  if (!pane || !book) return;
  pane.replaceChildren();
  const art = book.cover_src
    ? Object.assign(document.createElement("img"), { className: "inspect-cover", src: book.cover_src, alt: "" })
    : placeholder(book.title, "inspect-ph");
  const copy = document.createElement("div");
  copy.className = "inspect-copy";
  copy.innerHTML = `
    <p class="eyebrow">Volume</p>
    <h2></h2>
    <p class="byline"></p>
    <dl class="facts"></dl>
    <p class="blurb"></p>
    <p class="notes"></p>
    <p class="fineprint"></p>
    <div class="inspect-actions"></div>
  `;
  copy.querySelector("h2").textContent = book.title;
  copy.querySelector(".byline").textContent = [book.authors, book.subtitle].filter(Boolean).join(" · ");
  const facts = copy.querySelector(".facts");
  const rows = [
    ["ISBN", book.isbn],
    ["Publisher", book.publisher],
    ["Year", book.published_year],
    ["Pages", book.page_count],
  ];
  rows.forEach(([label, value]) => {
    if (!value) return;
    const wrap = document.createElement("div");
    wrap.innerHTML = `<dt></dt><dd></dd>`;
    wrap.querySelector("dt").textContent = label;
    wrap.querySelector("dd").textContent = value;
    facts.append(wrap);
  });
  copy.querySelector(".blurb").textContent = book.description || "";
  copy.querySelector(".notes").textContent = book.notes || "";
  if (book.openlibrary_url) {
    const link = document.createElement("a");
    link.href = book.openlibrary_url;
    link.rel = "noreferrer";
    link.textContent = "Open Library record";
    copy.querySelector(".fineprint").append(link);
  }
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "danger-btn";
  remove.textContent = "Remove from shelf";
  remove.addEventListener("click", async () => {
    if (!confirm("Remove this volume from the shelf?")) return;
    await api(`/api/books/${book.id}`, { method: "DELETE" });
    state.books = state.books.filter((b) => b.id !== book.id);
    state.selectedBookId = null;
    renderAll();
    history.pushState({}, "", "/");
  });
  copy.querySelector(".inspect-actions").append(remove);
  pane.append(art, copy);
}

function inspectItem(item) {
  const pane = $("#inspector");
  if (!pane || !item) return;
  pane.replaceChildren();
  const art = item.photo_src
    ? Object.assign(document.createElement("img"), { className: "inspect-photo", src: item.photo_src, alt: "" })
    : placeholder(item.name, "inspect-ph");
  const copy = document.createElement("div");
  copy.className = "inspect-copy";
  copy.innerHTML = `
    <p class="eyebrow">Household item</p>
    <h2></h2>
    <p class="byline"></p>
    <dl class="facts"></dl>
    <p class="notes"></p>
    <div class="inspect-actions"></div>
  `;
  copy.querySelector("h2").textContent = item.name;
  copy.querySelector(".byline").textContent = [item.brand, item.model].filter(Boolean).join(" ");
  const facts = copy.querySelector(".facts");
  [
    ["Serial", item.serial_number],
    ["Purchased", item.purchase_date],
    ["Replacement", item.replacement_value ? `$${money(item.replacement_value)}` : null],
    ["Room", item.room_name],
  ].forEach(([label, value]) => {
    if (!value) return;
    const wrap = document.createElement("div");
    wrap.innerHTML = `<dt></dt><dd></dd>`;
    wrap.querySelector("dt").textContent = label;
    wrap.querySelector("dd").textContent = value;
    facts.append(wrap);
  });
  copy.querySelector(".notes").textContent = item.notes || "";
  const actions = copy.querySelector(".inspect-actions");
  if (item.receipt_src) {
    const rec = document.createElement("a");
    rec.href = item.receipt_src;
    rec.textContent = "View receipt";
    rec.className = "ghost-btn";
    actions.append(rec);
  }
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "danger-btn";
  remove.textContent = "Remove item";
  remove.addEventListener("click", async () => {
    if (!confirm("Remove this household item?")) return;
    await api(`/api/items/${item.id}`, { method: "DELETE" });
    const room = currentRoom();
    if (room) room.items = room.items.filter((i) => i.id !== item.id);
    room.item_count = room.items.length;
    state.selectedItemId = null;
    renderAll();
  });
  actions.append(remove);
  pane.append(art, copy);
}

function inspectEmpty() {
  const pane = $("#inspector");
  if (!pane) return;
  pane.innerHTML = `<p class="inspect-empty">Select a volume or an item. Details stay here — the shelf stays in the middle.</p>`;
}

function renderInspector() {
  if (state.view === "library") {
    const book = state.books.find((b) => b.id === state.selectedBookId);
    book ? inspectBook(book) : inspectEmpty();
    return;
  }
  const room = currentRoom();
  const item = room?.items?.find((i) => i.id === state.selectedItemId);
  item ? inspectItem(item) : inspectEmpty();
}

function renderAll() {
  syncNav();
  setStageChrome();
  renderStage();
  renderInspector();
}

function selectLibrary(push) {
  state.view = "library";
  state.selectedRoomId = null;
  state.selectedItemId = null;
  if (!state.selectedBookId && state.books[0]) state.selectedBookId = state.books[0].id;
  renderAll();
  if (push) history.pushState({}, "", state.selectedBookId ? `/books/${state.selectedBookId}` : "/");
}

function selectBook(id, push) {
  state.view = "library";
  state.selectedBookId = id;
  state.selectedRoomId = null;
  state.selectedItemId = null;
  renderAll();
  if (push) history.pushState({}, "", `/books/${id}`);
}

function selectRoom(id, push) {
  state.view = "room";
  state.selectedRoomId = id;
  state.selectedBookId = null;
  const room = currentRoom();
  state.selectedItemId = room?.items?.[0]?.id || null;
  renderAll();
  if (push) history.pushState({}, "", `/rooms/${id}`);
}

function selectItem(id, push) {
  const room = currentRoom();
  const item = room?.items?.find((i) => i.id === id);
  if (item) state.selectedRoomId = item.room_id;
  state.view = "room";
  state.selectedItemId = id;
  renderAll();
  if (push) history.pushState({}, "", `/items/${id}`);
}

$$("[data-open-library]").forEach((el) => {
  el.addEventListener("click", (event) => {
    event.preventDefault();
    selectLibrary(true);
  });
});
$$("[data-open-room]").forEach((el) => {
  el.addEventListener("click", (event) => {
    event.preventDefault();
    selectRoom(Number(el.dataset.openRoom), true);
  });
});

$("#shelf-filter")?.addEventListener("input", (event) => {
  state.filter = event.target.value.trim().toLowerCase();
  renderStage();
});
$("#cover-scale")?.addEventListener("input", (event) => {
  document.documentElement.style.setProperty("--cover-scale", String(Number(event.target.value) / 100));
});

window.addEventListener("popstate", () => {
  const path = location.pathname;
  const book = path.match(/^\/books\/(\d+)/);
  const room = path.match(/^\/rooms\/(\d+)/);
  const item = path.match(/^\/items\/(\d+)/);
  if (book) selectBook(Number(book[1]), false);
  else if (item) {
    const found = state.rooms.flatMap((r) => r.items || []).find((i) => i.id === Number(item[1]));
    if (found) {
      state.selectedRoomId = found.room_id;
      selectItem(found.id, false);
    }
  } else if (room) selectRoom(Number(room[1]), false);
  else if (path === "/rooms") {
    if (state.rooms[0]) selectRoom(state.rooms[0].id, false);
  } else selectLibrary(false);
});

function fillBookForm(book) {
  const form = $("#manual-book");
  if (!form) return;
  for (const [key, value] of Object.entries(book)) {
    if (form.elements[key] != null && value != null) form.elements[key].value = value;
  }
}

function renderLookup(results) {
  const box = $("#lookup-results");
  if (!box) return;
  box.replaceChildren();
  results.filter(Boolean).forEach((book) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "lookup-hit";
    const art = book.cover_url
      ? Object.assign(document.createElement("img"), { src: book.cover_url, alt: "" })
      : Object.assign(document.createElement("div"), { className: "mini-ph" });
    const copy = document.createElement("div");
    copy.innerHTML = `<strong></strong><div></div>`;
    copy.querySelector("strong").textContent = book.title || "Untitled";
    copy.querySelector("div").textContent = [book.authors, book.published_year].filter(Boolean).join(" · ");
    const use = document.createElement("span");
    use.textContent = "Use";
    btn.append(art, copy, use);
    btn.addEventListener("click", () => fillBookForm(book));
    box.append(btn);
  });
}

const lookupBtn = $("#lookup-btn");
if (lookupBtn) {
  lookupBtn.addEventListener("click", async () => {
    const q = $("#lookup-q").value.trim();
    const status = $("#lookup-status");
    status.hidden = false;
    status.textContent = "Asking Open Library…";
    try {
      const data = await api(`/api/lookup?q=${encodeURIComponent(q)}`);
      if (!data.found) {
        status.textContent =
          data.kind === "isbn"
            ? "No match. A book EAN often starts with 978. You can still type the title and place it by hand."
            : "No match. Keep the title and place it by hand.";
        renderLookup([]);
        if (data.kind === "isbn") $("#manual-book").elements.isbn.value = q.replace(/[^0-9Xx]/g, "");
        else $("#manual-book").elements.title.value = q;
        return;
      }
      status.textContent =
        data.kind === "isbn" ? "Found a match." : `Found ${data.results.length} possible matches. Pick the one you want.`;
      renderLookup(data.results);
      if (data.results[0]) fillBookForm(data.results[0]);
    } catch (err) {
      status.textContent = err.message || "Lookup failed. You can still add the book manually.";
    }
  });
}

$("#manual-book")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  if (payload.page_count) payload.page_count = Number(payload.page_count);
  else delete payload.page_count;
  Object.keys(payload).forEach((key) => {
    if (payload[key] === "") payload[key] = null;
  });
  try {
    const book = await api("/api/books", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    state.books.unshift(book);
    closeSheet("add-book");
    selectBook(book.id, true);
  } catch (err) {
    alert(err.message);
  }
});

$("#room-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  try {
    const room = await api("/api/rooms", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    room.items = [];
    state.rooms.push(room);
    const nav = document.createElement("a");
    nav.className = "nav-row";
    nav.href = `/rooms/${room.id}`;
    nav.dataset.openRoom = String(room.id);
    nav.innerHTML = `<span class="nav-ico nav-ico-room" aria-hidden="true"></span><span></span><em>0</em>`;
    nav.querySelector("span:nth-child(2)").textContent = room.name;
    nav.addEventListener("click", (click) => {
      click.preventDefault();
      selectRoom(room.id, true);
    });
    $(".nav-add")?.before(nav);
    closeSheet("add-room");
    selectRoom(room.id, true);
  } catch (err) {
    alert(err.message);
  }
});

$("#item-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(event.target);
  data.set("room_id", String(state.selectedRoomId || ""));
  try {
    const item = await api("/api/items", { method: "POST", body: data });
    const room = currentRoom();
    if (room) {
      room.items = room.items || [];
      room.items.push(item);
      room.item_count = room.items.length;
    }
    closeSheet("add-item");
    selectItem(item.id, true);
  } catch (err) {
    alert(err.message);
  }
});

const scanBtn = $("#scan-btn");
const scanner = $("#scanner");
const video = $("#scan-video");
let scanStream = null;
let scanTimer = null;

async function stopScan() {
  if (scanTimer) clearInterval(scanTimer);
  scanTimer = null;
  scanStream?.getTracks().forEach((t) => t.stop());
  scanStream = null;
}

if (scanBtn && "BarcodeDetector" in window) {
  scanBtn.hidden = false;
  scanBtn.addEventListener("click", async () => {
    try {
      scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" } });
      video.srcObject = scanStream;
      await video.play();
      openSheet("scanner");
      const detector = new BarcodeDetector({ formats: ["ean_13", "ean_8", "upc_a", "code_128"] });
      scanTimer = setInterval(async () => {
        try {
          const codes = await detector.detect(video);
          if (codes[0]?.rawValue) {
            $("#lookup-q").value = codes[0].rawValue;
            await stopScan();
            closeSheet("scanner");
            lookupBtn.click();
          }
        } catch {
          /* keep scanning */
        }
      }, 400);
    } catch {
      alert("Camera is not available. Type the ISBN instead.");
    }
  });
  scanner?.addEventListener("close", stopScan);
}

if (rawState) {
  if (state.view === "library") {
    if (!state.selectedBookId && state.books[0]) state.selectedBookId = state.books[0].id;
  } else if (!state.selectedRoomId && state.rooms[0]) {
    state.selectedRoomId = state.rooms[0].id;
  }
  renderAll();
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
