const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

function openSheet(id) {
  const dialog = document.getElementById(id);
  if (dialog) dialog.showModal();
}

function closeSheet(id) {
  const dialog = document.getElementById(id);
  if (dialog) dialog.close();
}

$$("[data-open]").forEach((btn) => {
  btn.addEventListener("click", () => openSheet(btn.dataset.open));
});

async function api(url, options = {}) {
  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
  });
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

function placeholderCover(title) {
  const wrap = document.createElement("div");
  wrap.className = "volume-placeholder";
  wrap.textContent = title;
  return wrap;
}

function renderShelves(books) {
  const hall = $("#shelf-hall");
  if (!hall) return;
  hall.replaceChildren();
  if (!books.length) {
    hall.innerHTML = `<div class="empty-shelf"><div class="empty-plank"></div><p>The first shelf is empty. Add a book by ISBN, title, or by hand.</p></div>`;
    return;
  }
  const perRow = window.matchMedia("(max-width: 720px)").matches ? 4 : 7;
  for (let i = 0; i < books.length; i += perRow) {
    const row = document.createElement("div");
    row.className = "shelf-row";
    for (const book of books.slice(i, i + perRow)) {
      const link = document.createElement("a");
      link.className = "volume";
      link.href = `/books/${book.id}`;
      if (book.cover_src) {
        const img = document.createElement("img");
        img.className = "volume-cover";
        img.src = book.cover_src;
        img.alt = "";
        img.addEventListener("error", () => img.replaceWith(placeholderCover(book.title)));
        link.append(img);
      } else {
        link.append(placeholderCover(book.title));
      }
      const caption = document.createElement("span");
      caption.className = "volume-title";
      caption.textContent = book.title;
      link.append(caption);
      row.append(link);
    }
    hall.append(row);
  }
}

const hall = $("#shelf-hall");
if (hall) {
  try {
    renderShelves(JSON.parse(hall.dataset.books || "[]"));
  } catch {
    renderShelves([]);
  }
}

function fillBookForm(book) {
  const form = $("#manual-book");
  if (!form) return;
  for (const [key, value] of Object.entries(book)) {
    if (form.elements[key] != null && value != null) {
      form.elements[key].value = value;
    }
  }
}

function renderLookup(results) {
  const box = $("#lookup-results");
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
        status.textContent = "No match. Fill in the details by hand — that still counts.";
        renderLookup([]);
        if (data.kind === "isbn") {
          $("#manual-book").elements.isbn.value = q.replace(/[^0-9Xx]/g, "");
        } else {
          $("#manual-book").elements.title.value = q;
        }
        return;
      }
      status.textContent = data.kind === "isbn" ? "Found a match." : `Found ${data.results.length} possible matches.`;
      renderLookup(data.results);
      if (data.results[0]) fillBookForm(data.results[0]);
    } catch (err) {
      status.textContent = err.message || "Lookup failed. You can still add the book manually.";
    }
  });
}

const manualBook = $("#manual-book");
if (manualBook) {
  manualBook.addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.target;
    const payload = Object.fromEntries(new FormData(form).entries());
    if (payload.page_count) payload.page_count = Number(payload.page_count);
    else delete payload.page_count;
    Object.keys(payload).forEach((key) => {
      if (payload[key] === "") payload[key] = null;
    });
    try {
      await api("/api/books", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      window.location.reload();
    } catch (err) {
      alert(err.message);
    }
  });
}

const roomForm = $("#room-form");
if (roomForm) {
  roomForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const payload = Object.fromEntries(new FormData(roomForm).entries());
    try {
      const room = await api("/api/rooms", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      window.location.href = `/rooms/${room.id}`;
    } catch (err) {
      alert(err.message);
    }
  });
}

const itemForm = $("#item-form");
if (itemForm) {
  itemForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = new FormData(itemForm);
    data.set("room_id", itemForm.dataset.roomId);
    try {
      const item = await api("/api/items", { method: "POST", body: data });
      window.location.href = `/items/${item.id}`;
    } catch (err) {
      alert(err.message);
    }
  });
}

const deleteBook = $("[data-delete-book]");
if (deleteBook) {
  deleteBook.addEventListener("click", async () => {
    if (!confirm("Remove this volume from the shelf?")) return;
    await api(`/api/books/${deleteBook.dataset.deleteBook}`, { method: "DELETE" });
    window.location.href = "/";
  });
}

const deleteItem = $("[data-delete-item]");
if (deleteItem) {
  deleteItem.addEventListener("click", async () => {
    if (!confirm("Remove this household item?")) return;
    await api(`/api/items/${deleteItem.dataset.deleteItem}`, { method: "DELETE" });
    window.location.href = `/rooms/${deleteItem.dataset.room}`;
  });
}

const scanBtn = $("#scan-btn");
const scanner = $("#scanner");
const video = $("#scan-video");
let scanStream = null;
let scanTimer = null;

async function stopScan() {
  if (scanTimer) {
    clearInterval(scanTimer);
    scanTimer = null;
  }
  if (scanStream) {
    scanStream.getTracks().forEach((t) => t.stop());
    scanStream = null;
  }
}

if (scanBtn && "BarcodeDetector" in window) {
  scanBtn.hidden = false;
  scanBtn.addEventListener("click", async () => {
    try {
      scanStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "environment" },
      });
      video.srcObject = scanStream;
      await video.play();
      openSheet("scanner");
      const detector = new BarcodeDetector({
        formats: ["ean_13", "ean_8", "upc_a", "code_128"],
      });
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
    } catch (err) {
      alert("Camera is not available. Type the ISBN instead.");
    }
  });
  scanner?.addEventListener("close", stopScan);
}

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
