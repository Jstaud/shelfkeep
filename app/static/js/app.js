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
state.borrowers = state.borrowers || [];
state.filter = "";
state.mediaFilter = "all";

const MEDIA = {
  book: { label: "Book", creator: "Authors", add: "Add a book" },
  movie: { label: "Movie", creator: "Director", add: "Add a movie" },
  disc: { label: "Disc", creator: "Artist", add: "Add a disc" },
  game: { label: "Game", creator: "Studio", add: "Add a game" },
};

function currentBorrower() {
  return state.borrowers.find((person) => person.id === state.selectedBorrowerId) || null;
}

function catalogRecord(kind, id) {
  if (kind === "book") return state.books.find((book) => book.id === id) || null;
  return state.rooms.flatMap((room) => room.items || []).find((item) => item.id === id) || null;
}

function applyLoanToRecord(loan) {
  const record = catalogRecord(loan.item_kind, loan.item_id);
  if (record) {
    record.loan = {
      id: loan.id,
      borrower_id: loan.borrower_id,
      borrower_name: loan.borrower_name,
      loaned_at: loan.loaned_at,
      due_date: loan.due_date,
    };
  }
  const borrower = state.borrowers.find((person) => person.id === loan.borrower_id);
  if (!borrower) return;
  borrower.loans = borrower.loans || [];
  const index = borrower.loans.findIndex((entry) => entry.id === loan.id);
  if (index >= 0) borrower.loans[index] = loan;
  else borrower.loans.unshift(loan);
  borrower.active_loan_count = borrower.loans.filter((entry) => !entry.returned_at).length;
}

function clearLoanOnRecord(loan) {
  const record = catalogRecord(loan.item_kind, loan.item_id);
  if (record && record.loan?.id === loan.id) record.loan = null;
  const borrower = state.borrowers.find((person) => person.id === loan.borrower_id);
  if (!borrower) return;
  borrower.loans = (borrower.loans || []).map((entry) => (entry.id === loan.id ? loan : entry));
  borrower.active_loan_count = borrower.loans.filter((entry) => !entry.returned_at).length;
}

function todayISO() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function currentRoom() {
  return state.rooms.find((room) => room.id === state.selectedRoomId) || null;
}

function rollupInventory() {
  let items = 0;
  let value = 0;
  for (const room of state.rooms) {
    const list = room.items || [];
    room.item_count = list.length;
    let roomValue = 0;
    for (const item of list) {
      const n = Number(item.replacement_value);
      if (Number.isFinite(n)) roomValue += n;
    }
    room.replacement_total = roomValue.toFixed(2);
    items += list.length;
    value += roomValue;
  }
  return { items, value };
}

function syncNav() {
  const totals = rollupInventory();
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
  const summary = $(".nav-value");
  if (summary) {
    const formatted = totals.value.toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
    summary.textContent = `${totals.items} household items · $${formatted}`;
  }
  const outNow = $("[data-open-borrowers] em");
  if (outNow) {
    outNow.textContent = String(
      state.borrowers.reduce((sum, person) => sum + (person.active_loan_count || 0), 0)
    );
  }
  $$("[data-open-borrowers]").forEach((el) => {
    el.classList.toggle("is-active", state.view === "borrowers" && !state.selectedBorrowerId);
  });
  $$("[data-open-borrower]").forEach((el) => {
    const id = Number(el.dataset.openBorrower);
    el.classList.toggle("is-active", id === state.selectedBorrowerId);
    const person = state.borrowers.find((entry) => entry.id === id);
    const em = el.querySelector("em");
    if (person && em) em.textContent = String(person.active_loan_count || 0);
  });
}

function setStageChrome() {
  const kicker = $("#stage-kicker");
  const title = $("#stage-title");
  const add = $("#stage-add");
  if (!kicker || !title || !add) return;
  const chips = $("#type-chips");
  if (chips) chips.hidden = state.view !== "library";
  if (state.view === "library") {
    kicker.textContent = "The stacks";
    title.textContent = "Library";
    const meta = MEDIA[state.mediaFilter] || MEDIA.book;
    add.textContent = state.mediaFilter === "all" ? "Add to the shelf" : meta.add;
    add.dataset.open = "add-book";
    add.onclick = () => {
      resetBookForm();
      if (state.mediaFilter !== "all" && $("#catalog-type")) {
        $("#catalog-type").value = state.mediaFilter;
        syncMediaForm();
      }
      openSheet("add-book");
    };
  } else if (state.view === "borrowers") {
    const person = currentBorrower();
    kicker.textContent = "On loan";
    title.textContent = person ? person.name : "Out now";
    add.textContent = "Add a borrower";
    add.dataset.open = "add-borrower";
    add.onclick = () => openSheet("add-borrower");
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
  } else if (state.view === "borrowers") {
    renderLoans(well);
  } else {
    renderItems(well);
  }
}

function renderBooks(well) {
  const books = state.books.filter((book) => {
    const typeOk = state.mediaFilter === "all" || (book.media_type || "book") === state.mediaFilter;
    return (
      typeOk &&
      matchesFilter([book.title, book.authors, book.isbn, book.media_type].filter(Boolean).join(" "))
    );
  });
  if (!books.length) {
    const empty =
      state.mediaFilter !== "all" && state.books.length
        ? "Nothing of this type on the shelf yet."
        : "The first shelf is empty. Add a book by ISBN, title, or by hand.";
    well.innerHTML = `<div class="empty-shelf"><p>${empty}</p></div>`;
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
  btn.addEventListener("click", () => {
    if (state.view === "borrowers") selectLoaned("book", book.id, true);
    else selectBook(book.id, true);
  });
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
    body.append(placeholder(book.title, "object-ph is-" + (book.media_type || "book")));
  }
  if (book.loan) {
    const badge = document.createElement("span");
    badge.className = "object-loan";
    badge.textContent = "Out";
    body.append(badge);
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
  btn.addEventListener("click", () => {
    if (state.view === "borrowers") selectLoaned("item", item.id, true);
    else selectItem(item.id, true);
  });
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
  if (item.loan) {
    const badge = document.createElement("span");
    badge.className = "object-loan";
    badge.textContent = "Out";
    body.append(badge);
  }
  const caption = document.createElement("span");
  caption.className = "object-title";
  caption.textContent = item.name;
  btn.append(body, caption);
  return btn;
}

function renderLoans(well) {
  const person = currentBorrower();
  const loans = (person ? person.loans || [] : state.borrowers.flatMap((entry) => entry.loans || []))
    .filter((loan) => !loan.returned_at)
    .filter((loan) =>
      matchesFilter([loan.item_title, loan.borrower_name].filter(Boolean).join(" "))
    );
  if (!loans.length) {
    const empty = person
      ? "Nothing is out with this person."
      : "Nothing is out. Lend a volume or an item from its inspector.";
    well.innerHTML = `<div class="empty-shelf"><p>${empty}</p></div>`;
    return;
  }
  const perRow = window.matchMedia("(max-width: 720px)").matches ? 4 : 6;
  for (let i = 0; i < loans.length; i += perRow) {
    const row = document.createElement("div");
    row.className = "shelf-row";
    for (const loan of loans.slice(i, i + perRow)) {
      const record = catalogRecord(loan.item_kind, loan.item_id);
      if (loan.item_kind === "item" && record) {
        row.append(itemObject(record));
      } else if (record) {
        row.append(bookObject(record));
      } else {
        const ghost = { id: loan.item_id, title: loan.item_title || "On loan", media_type: "book", loan };
        row.append(bookObject(ghost));
      }
    }
    well.append(row);
  }
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
    <p class="eyebrow"></p>
    <h2></h2>
    <p class="byline"></p>
    <dl class="facts"></dl>
    <p class="blurb"></p>
    <p class="notes"></p>
    <p class="fineprint"></p>
    <div class="inspect-actions"></div>
  `;
  copy.querySelector(".eyebrow").textContent = MEDIA[book.media_type]?.label || "Volume";
  copy.querySelector("h2").textContent = book.title;
  copy.querySelector(".byline").textContent = [book.authors, book.subtitle].filter(Boolean).join(" · ");
  const facts = copy.querySelector(".facts");
  const rows = [
    ["Type", MEDIA[book.media_type]?.label || book.media_type],
    ["ISBN", book.isbn],
    ["Publisher", book.publisher],
    ["Year", book.published_year],
    ["Pages", book.page_count],
    ["On loan", book.loan ? `${book.loan.borrower_name} since ${book.loan.loaned_at}` : null],
    ["Due", book.loan?.due_date],
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
    dropLoansFor("book", book.id);
    state.selectedBookId = null;
    renderAll();
    history.replaceState({}, "", "/");
  });
  copy.querySelector(".inspect-actions").append(remove);
  const edit = document.createElement("button");
  edit.type = "button";
  edit.className = "ghost-btn";
  edit.textContent = "Edit";
  edit.addEventListener("click", () => openCatalogEditor(book));
  copy.querySelector(".inspect-actions").append(edit);
  appendLoanActions(copy.querySelector(".inspect-actions"), "book", book);
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
    ["On loan", item.loan ? `${item.loan.borrower_name} since ${item.loan.loaned_at}` : null],
    ["Due", item.loan?.due_date],
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
    if (room) room.items = (room.items || []).filter((i) => i.id !== item.id);
    else {
      state.rooms.forEach((entry) => {
        entry.items = (entry.items || []).filter((row) => row.id !== item.id);
      });
    }
    dropLoansFor("item", item.id);
    state.selectedItemId = null;
    renderAll();
    const roomId = item.room_id || room?.id || state.selectedRoomId;
    if (roomId) history.replaceState({}, "", `/rooms/${roomId}`);
  });
  actions.append(remove);
  appendLoanActions(actions, "item", item);
  pane.append(art, copy);
}

function inspectEmpty() {
  const pane = $("#inspector");
  if (!pane) return;
  pane.innerHTML = `<p class="inspect-empty">Select a volume or an item. Details stay here — the shelf stays in the middle.</p>`;
}

function inspectBorrower(person) {
  const pane = $("#inspector");
  if (!pane || !person) return;
  pane.replaceChildren();
  const copy = document.createElement("div");
  copy.className = "inspect-copy";
  copy.innerHTML = `
    <p class="eyebrow">Borrower</p>
    <h2></h2>
    <p class="byline"></p>
    <p class="notes"></p>
    <h3 class="loan-heading">Loans</h3>
    <ul class="loan-list"></ul>
    <div class="inspect-actions"></div>
  `;
  copy.querySelector("h2").textContent = person.name;
  copy.querySelector(".byline").textContent = person.contact || "";
  copy.querySelector(".notes").textContent = person.notes || "";
  const list = copy.querySelector(".loan-list");
  const loans = [...(person.loans || [])].sort((a, b) => Number(!!a.returned_at) - Number(!!b.returned_at));
  if (!loans.length) {
    const empty = document.createElement("li");
    empty.textContent = "No loans yet.";
    list.append(empty);
  }
  loans.forEach((loan) => {
    const row = document.createElement("li");
    const status = loan.returned_at ? `returned ${loan.returned_at}` : `out since ${loan.loaned_at}`;
    row.textContent = `${loan.item_title || "Item"} — ${status}`;
    if (loan.due_date && !loan.returned_at) row.textContent += ` · due ${loan.due_date}`;
    if (!loan.returned_at) {
      const mark = document.createElement("button");
      mark.type = "button";
      mark.className = "ghost-btn";
      mark.textContent = "Mark returned";
      mark.addEventListener("click", () => markLoanReturned(loan.id));
      row.append(mark);
    }
    list.append(row);
  });
  const remove = document.createElement("button");
  remove.type = "button";
  remove.className = "danger-btn";
  remove.textContent = "Remove borrower";
  remove.addEventListener("click", async () => {
    if (!confirm("Remove this borrower?")) return;
    try {
      await api(`/api/borrowers/${person.id}`, { method: "DELETE" });
      state.borrowers = state.borrowers.filter((entry) => entry.id !== person.id);
      $(`[data-open-borrower="${person.id}"]`)?.remove();
      state.selectedBorrowerId = null;
      renderAll();
      history.replaceState({}, "", "/borrowers");
    } catch (err) {
      alert(err.message);
    }
  });
  copy.querySelector(".inspect-actions").append(remove);
  pane.append(copy);
}

function renderInspector() {
  if (state.view === "library") {
    const book = state.books.find((b) => b.id === state.selectedBookId);
    book ? inspectBook(book) : inspectEmpty();
    return;
  }
  if (state.view === "borrowers") {
    if (state.selectedBookId) {
      const book = state.books.find((b) => b.id === state.selectedBookId);
      if (book) {
        inspectBook(book);
        return;
      }
    }
    if (state.selectedItemId) {
      const item = catalogRecord("item", state.selectedItemId);
      if (item) {
        inspectItem(item);
        return;
      }
    }
    const person = currentBorrower();
    person ? inspectBorrower(person) : inspectEmpty();
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

function selectBorrowers(push) {
  state.view = "borrowers";
  state.selectedBorrowerId = null;
  state.selectedBookId = null;
  state.selectedItemId = null;
  state.selectedRoomId = null;
  renderAll();
  if (push) history.pushState({}, "", "/borrowers");
}

function selectBorrower(id, push) {
  state.view = "borrowers";
  state.selectedBorrowerId = id;
  state.selectedBookId = null;
  state.selectedItemId = null;
  state.selectedRoomId = null;
  renderAll();
  if (push) history.pushState({}, "", `/borrowers/${id}`);
}

function selectLoaned(kind, id, push) {
  state.view = "borrowers";
  if (kind === "book") {
    state.selectedBookId = id;
    state.selectedItemId = null;
  } else {
    state.selectedItemId = id;
    state.selectedBookId = null;
  }
  renderAll();
  if (push) {
    history.pushState({}, "", state.selectedBorrowerId ? `/borrowers/${state.selectedBorrowerId}` : "/borrowers");
  }
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
$$("[data-open-borrowers]").forEach((el) => {
  el.addEventListener("click", (event) => {
    event.preventDefault();
    selectBorrowers(true);
  });
});
$$("[data-open-borrower]").forEach((el) => {
  el.addEventListener("click", (event) => {
    event.preventDefault();
    selectBorrower(Number(el.dataset.openBorrower), true);
  });
});
$$("[data-media-filter]").forEach((el) => {
  el.addEventListener("click", () => {
    state.mediaFilter = el.dataset.mediaFilter || "all";
    $$("[data-media-filter]").forEach((chip) => {
      chip.classList.toggle("is-active", chip.dataset.mediaFilter === state.mediaFilter);
    });
    setStageChrome();
    renderStage();
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
  const borrower = path.match(/^\/borrowers\/(\d+)/);
  if (book) selectBook(Number(book[1]), false);
  else if (borrower) selectBorrower(Number(borrower[1]), false);
  else if (path === "/borrowers") selectBorrowers(false);
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

const BOOK_FORM_KEYS = [
  "title",
  "authors",
  "isbn",
  "publisher",
  "published_year",
  "notes",
  "subtitle",
  "cover_url",
  "openlibrary_url",
  "description",
  "page_count",
];

function dropLoansFor(kind, id) {
  state.borrowers.forEach((person) => {
    person.loans = (person.loans || []).filter(
      (loan) => !(loan.item_kind === kind && loan.item_id === id)
    );
    person.active_loan_count = person.loans.filter((loan) => !loan.returned_at).length;
  });
}

function resetBookForm() {
  const form = $("#manual-book");
  if (!form) return;
  BOOK_FORM_KEYS.forEach((key) => {
    if (form.elements[key]) form.elements[key].value = "";
  });
  form.dataset.editId = "";
  if (form.elements.media_type) form.elements.media_type.value = "book";
  const cover = $("#book-cover");
  if (cover) cover.value = "";
  syncMediaForm();
}

function syncMediaForm() {
  const type = $("#catalog-type")?.value || "book";
  const isBook = type === "book";
  const lookup = $("#lookup-block");
  const hint = $("#manual-type-hint");
  const isbn = $("#isbn-label");
  const publisher = $("#publisher-label");
  const creator = $("#creator-label");
  const sheetTitle = $("#catalog-sheet-title");
  if (lookup) lookup.hidden = !isBook;
  if (hint) hint.hidden = isBook;
  if (isbn) isbn.hidden = !isBook;
  if (publisher) publisher.hidden = !isBook;
  if (creator) {
    const label = creator.childNodes[0];
    if (label) label.textContent = `${MEDIA[type]?.creator || "Authors"} `;
  }
  if (sheetTitle) {
    const editing = $("#manual-book")?.dataset.editId;
    sheetTitle.textContent = editing ? "Edit shelf card" : MEDIA[type]?.add || "Add to the shelf";
  }
}

function openCatalogEditor(book) {
  const form = $("#manual-book");
  if (!form) return;
  fillBookForm(book);
  if (form.elements.media_type) form.elements.media_type.value = book.media_type || "book";
  form.dataset.editId = String(book.id);
  syncMediaForm();
  openSheet("add-book");
}

$("#catalog-type")?.addEventListener("change", syncMediaForm);

function fillBookForm(book) {
  const form = $("#manual-book");
  if (!form) return;
  resetBookForm();
  for (const [key, value] of Object.entries(book || {})) {
    if (form.elements[key] != null && value != null && value !== "") {
      form.elements[key].value = value;
    }
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
let lookupGeneration = 0;

$("#add-book")?.addEventListener("close", () => {
  lookupGeneration += 1;
  resetBookForm();
  renderLookup([]);
  const lookupQ = $("#lookup-q");
  if (lookupQ) lookupQ.value = "";
  const lookupStatus = $("#lookup-status");
  if (lookupStatus) {
    lookupStatus.hidden = true;
    lookupStatus.textContent = "";
  }
});

function applyLookupQuery(q) {
  const digits = q.replace(/[^0-9Xx]/g, "");
  if (digits.length === 10 || digits.length === 13) {
    $("#manual-book").elements.isbn.value = digits;
  } else if (q) {
    $("#manual-book").elements.title.value = q;
  }
}

if (lookupBtn) {
  lookupBtn.addEventListener("click", async () => {
    const q = $("#lookup-q").value.trim();
    const status = $("#lookup-status");
    const generation = ++lookupGeneration;
    status.hidden = false;
    status.textContent = "Asking Open Library…";
    try {
      const data = await api(`/api/lookup?q=${encodeURIComponent(q)}`);
      if (generation !== lookupGeneration) return;
      if (!data.found) {
        status.textContent =
          data.kind === "isbn"
            ? "No match. A book EAN often starts with 978. You can still type the title and place it by hand."
            : "No match. Keep the title and place it by hand.";
        renderLookup([]);
        resetBookForm();
        applyLookupQuery(q);
        return;
      }
      status.textContent =
        data.kind === "isbn" ? "Found a match." : `Found ${data.results.length} possible matches. Pick the one you want.`;
      renderLookup(data.results);
      if (data.results[0]) fillBookForm(data.results[0]);
    } catch (err) {
      if (generation !== lookupGeneration) return;
      status.textContent = err.message || "Lookup failed. You can still add the book manually.";
      renderLookup([]);
      resetBookForm();
      applyLookupQuery(q);
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
    const editId = event.target.dataset.editId;
    const book = await api(editId ? `/api/books/${editId}` : "/api/books", {
      method: editId ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const cover = $("#book-cover");
    let saved = book;
    if (cover?.files?.[0]) {
      const data = new FormData();
      data.set("cover", cover.files[0]);
      try {
        saved = await api(`/api/books/${book.id}/cover`, { method: "POST", body: data });
      } catch (coverErr) {
        if (!editId) {
          await api(`/api/books/${book.id}`, { method: "DELETE" }).catch(() => {});
        }
        throw coverErr;
      }
    }
    if (editId) {
      const index = state.books.findIndex((entry) => entry.id === saved.id);
      if (index >= 0) state.books[index] = { ...state.books[index], ...saved };
    } else {
      state.books.unshift(book);
      if (saved.cover_src) state.books[0] = saved;
    }
    lookupGeneration += 1;
    resetBookForm();
    renderLookup([]);
    const lookupQ = $("#lookup-q");
    if (lookupQ) lookupQ.value = "";
    const lookupStatus = $("#lookup-status");
    if (lookupStatus) {
      lookupStatus.hidden = true;
      lookupStatus.textContent = "";
    }
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
    $(".nav-empty")?.remove();
    $(".nav-add")?.before(nav);
    event.target.reset();
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
    }
    event.target.reset();
    closeSheet("add-item");
    selectItem(item.id, true);
  } catch (err) {
    alert(err.message);
  }
});

function appendLoanActions(actions, kind, record) {
  if (!actions || !record) return;
  if (record.loan) {
    const mark = document.createElement("button");
    mark.type = "button";
    mark.className = "primary-btn";
    mark.textContent = "Mark returned";
    mark.addEventListener("click", () => markLoanReturned(record.loan.id));
    actions.insertBefore(mark, actions.firstChild);
    return;
  }
  const lend = document.createElement("button");
  lend.type = "button";
  lend.className = "ghost-btn";
  lend.textContent = "Lend this";
  lend.addEventListener("click", () => openLoanSheet(kind, record.id));
  actions.insertBefore(lend, actions.firstChild);
}

async function markLoanReturned(loanId) {
  try {
    const loan = await api(`/api/loans/${loanId}/return`, { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    clearLoanOnRecord(loan);
    renderAll();
  } catch (err) {
    alert(err.message);
  }
}

function openLoanSheet(kind, id) {
  if (!state.borrowers.length) {
    openSheet("add-borrower");
    return;
  }
  const form = $("#loan-form");
  if (!form) return;
  form.elements.item_kind.value = kind;
  form.elements.item_id.value = String(id);
  form.elements.loaned_at.value = todayISO();
  form.elements.due_date.value = "";
  form.elements.notes.value = "";
  const select = $("#loan-borrower");
  select.replaceChildren();
  state.borrowers.forEach((person) => {
    const option = document.createElement("option");
    option.value = String(person.id);
    option.textContent = person.name;
    select.append(option);
  });
  openSheet("loan-out");
}

$("#borrower-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  Object.keys(payload).forEach((key) => {
    if (payload[key] === "") payload[key] = null;
  });
  try {
    const person = await api("/api/borrowers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    person.loans = person.loans || [];
    state.borrowers.push(person);
    state.borrowers.sort((a, b) => a.name.localeCompare(b.name));
    const nav = document.createElement("a");
    nav.className = "nav-row";
    nav.href = `/borrowers/${person.id}`;
    nav.dataset.openBorrower = String(person.id);
    nav.innerHTML = `<span class="nav-ico nav-ico-person" aria-hidden="true"></span><span></span><em>0</em>`;
    nav.querySelector("span:nth-child(2)").textContent = person.name;
    nav.addEventListener("click", (click) => {
      click.preventDefault();
      selectBorrower(person.id, true);
    });
    $("#borrower-empty")?.remove();
    $("#borrower-nav")?.append(nav);
    event.target.reset();
    closeSheet("add-borrower");
    selectBorrower(person.id, true);
  } catch (err) {
    alert(err.message);
  }
});

$("#loan-form")?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.target).entries());
  payload.borrower_id = Number(payload.borrower_id);
  payload.item_id = Number(payload.item_id);
  if (!payload.due_date) payload.due_date = null;
  if (!payload.notes) payload.notes = null;
  try {
    const loan = await api("/api/loans", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    applyLoanToRecord(loan);
    event.target.reset();
    closeSheet("loan-out");
    renderAll();
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
  if (video) video.srcObject = null;
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
      await stopScan();
      closeSheet("scanner");
      alert("Camera is not available. Type the ISBN instead.");
    }
  });
  scanner?.addEventListener("close", stopScan);
}

if (rawState) {
  if (state.view === "library") {
    if (!state.selectedBookId && state.books[0]) state.selectedBookId = state.books[0].id;
  } else if (state.view === "borrowers") {
    state.selectedRoomId = null;
  } else if (!state.selectedRoomId && state.rooms[0]) {
    state.selectedRoomId = state.rooms[0].id;
  }
  syncMediaForm();
  renderAll();
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
