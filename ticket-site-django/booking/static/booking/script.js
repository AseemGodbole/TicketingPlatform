// =========================
// Seat map + checkout script (cleaned, copy-paste ready)
// =========================

const TOP_PRICE = 350;    // rows A–F
const BOTTOM_PRICE = 250; // rows G–P

const SEGMENT_MAX = { padLeft: 2, left: 7, middle: 13, right: 7, padRight: 2 };

const REMOVED_SEAT_SLOTS = {
    A: new Set([4]),
    C: new Set([18]),
    G: new Set([19]),
    I: new Set([20]),
    K: new Set([20]),
    M: new Set([19]),
    O: new Set([16]),
};

const ROW_SHAPE = {
    A: { block: "top", left: 3, middle: 13, right: 3 },
    B: { block: "top", left: 4, middle: 13, right: 4 },
    C: { block: "top", left: 5, middle: 13, right: 5 },
    D: { block: "top", left: 6, middle: 13, right: 6 },
    E: { block: "top", left: 7, middle: 13, right: 6 },
    F: { block: "top", left: 7, middle: 13, right: 7 },

    G: { block: "bottom", left: 6, middle: 13, right: 7 },
    H: { block: "bottom", left: 7, middle: 13, right: 7 },
    I: { block: "bottom", left: 7, middle: 13, right: 7 },
    J: { block: "bottom", left: 7, middle: 13, right: 7 },
    K: { block: "bottom", left: 7, middle: 13, right: 7 },
    L: { block: "bottom", left: 7, middle: 13, right: 7 },
    M: { block: "bottom", left: 6, middle: 13, right: 6 },
    N: { block: "bottom", left: 5, middle: 13, right: 6 },
    O: { block: "bottom", left: 3, middle: 13, right: 3 },

    P: { block: "bottom", left: 7, middle: 10, right: 7, hasAisles: false },
};

// --- initial booked and locked seats from server-rendered template ---
function getBookedFromServer() {
    try {
        const el = document.getElementById("booked-seats-data");
        if (!el) return [];
        const txt = el.textContent.trim();
        if (!txt) return [];
        return JSON.parse(txt);
    } catch (e) {
        console.error("Error parsing booked seat JSON", e);
        return [];
    }
}

function getLockedFromServer() {
    try {
        const el = document.getElementById("locked-seats-data");
        if (!el) return [];
        const txt = el.textContent.trim();
        if (!txt) return [];
        return JSON.parse(txt);
    } catch (e) {
        console.error("Error parsing locked seat JSON", e);
        return [];
    }
}

const preBooked = new Set(getBookedFromServer());
const preLocked = new Set(getLockedFromServer());

// --------- global selected set exposed for helpers & debugging ----------
window.selectedSeats = new Set();

// --------- helpers ----------
function priceForSeat(seatId) {
    const row = seatId[0];
    return "ABCDEF".includes(row) ? TOP_PRICE : BOTTOM_PRICE;
}

function refreshSummary() {
    const selected = Array.from(window.selectedSeats || []);
    const selEl = document.getElementById("selected");
    const totalEl = document.getElementById("total");
    if (selEl) selEl.innerText = selected.join(", ");
    let total = 0;
    for (const s of selected) total += priceForSeat(s);
    if (totalEl) totalEl.innerText = total;
}

function createPadding(count, seatRow) {
    for (let i = 0; i < count; i++) {
        const pad = document.createElement("div");
        pad.className = "seat empty";
        seatRow.appendChild(pad);
    }
}

function createSegment(side, realCount, maxCount, rowLabel, seatRow, seatNumberRef, seatSlotRef) {
    const emptiesTotal = maxCount - realCount;
    if (maxCount < realCount) throw new Error(`Row ${rowLabel} segment ${side}: realCount > maxCount`);

    let before = 0, after = 0;
    if (side === "left") before = emptiesTotal;
    else if (side === "right") after = emptiesTotal;
    else { before = Math.floor(emptiesTotal / 2); after = emptiesTotal - before; }

    for (let i = 0; i < before; i++) { const e = document.createElement("div"); e.className = "seat empty"; seatRow.appendChild(e); }

    for (let i = 0; i < realCount; i++) {
        const currentSeatSlot = seatSlotRef.value;
        seatSlotRef.value++;

        if (REMOVED_SEAT_SLOTS[rowLabel] && REMOVED_SEAT_SLOTS[rowLabel].has(currentSeatSlot)) {
            const removed = document.createElement("div");
            removed.className = "seat empty no-seat";
            removed.textContent = "×";
            removed.title = `${rowLabel}${currentSeatSlot} removed`;
            seatRow.appendChild(removed);
            continue;
        }

        const seatId = `${rowLabel}${seatNumberRef.value}`;
        const s = document.createElement("div");
        s.className = "seat";
        if (preBooked.has(seatId)) s.classList.add("booked");
        else if (preLocked.has(seatId)) s.classList.add("locked");
        s.dataset.seat = seatId;
        s.textContent = seatNumberRef.value;
        seatRow.appendChild(s);
        seatNumberRef.value++;
    }

    for (let i = 0; i < after; i++) { const e = document.createElement("div"); e.className = "seat empty"; seatRow.appendChild(e); }
}

function createRow(rowLabel, shape, container) {
    const row = document.createElement("div");
    row.className = "row";
    if (rowLabel === "P") row.classList.add("row-p");
    const leftLabel = document.createElement("div"); leftLabel.className = "row-label"; leftLabel.textContent = rowLabel;
    const rightLabel = leftLabel.cloneNode(true);
    const seatRow = document.createElement("div"); seatRow.className = "seat-row";
    const seatNumberRef = { value: 1 };
    const seatSlotRef = { value: 1 };

    if (shape.hasAisles === false) {
        const totalSeats = shape.left + shape.middle + shape.right;
        createPadding(SEGMENT_MAX.padLeft, seatRow);
        createSegment("full", totalSeats, totalSeats, rowLabel, seatRow, seatNumberRef, seatSlotRef);
        createPadding(SEGMENT_MAX.padRight, seatRow);
        row.appendChild(leftLabel); row.appendChild(seatRow); row.appendChild(rightLabel);
        container.appendChild(row);
        return;
    }

    createPadding(SEGMENT_MAX.padLeft, seatRow);
    createSegment("left", shape.left, SEGMENT_MAX.left, rowLabel, seatRow, seatNumberRef, seatSlotRef);
    if (shape.hasAisles !== false) { const a = document.createElement("div"); a.className = "aisle-vert"; seatRow.appendChild(a); }
    createSegment("middle", shape.middle, SEGMENT_MAX.middle, rowLabel, seatRow, seatNumberRef, seatSlotRef);
    if (shape.hasAisles !== false) { const a = document.createElement("div"); a.className = "aisle-vert"; seatRow.appendChild(a); }
    createSegment("right", shape.right, SEGMENT_MAX.right, rowLabel, seatRow, seatNumberRef, seatSlotRef);
    createPadding(SEGMENT_MAX.padRight, seatRow);
    row.appendChild(leftLabel); row.appendChild(seatRow); row.appendChild(rightLabel);
    container.appendChild(row);
}

function markSeatsAsBooked(seatsArray, { dropFromSelection = true } = {}) {
    for (const s of seatsArray) preBooked.add(s);
    document.querySelectorAll(".seat").forEach(el => {
        const id = el.dataset && el.dataset.seat;
        if (!id) return;
        if (preBooked.has(id)) {
            el.classList.add("booked");
            el.classList.remove("selected");
            el.classList.remove("locked");  // Remove locked class when marking as booked
        }
    });
    if (dropFromSelection) {
        for (const s of Array.from(window.selectedSeats)) if (preBooked.has(s)) window.selectedSeats.delete(s);
    }
    refreshSummary();
}

function markSeatsAsUnlocked(seatsArray) {
    for (const s of seatsArray) preBooked.delete(s);
    document.querySelectorAll(".seat").forEach(el => {
        const id = el.dataset && el.dataset.seat;
        if (!id) return;
        if (!preBooked.has(id)) el.classList.remove("booked");
    });
    refreshSummary();
}

// helper to POST JSON and return parsed data; logs text for debugging
async function postJson(url, payload, csrftoken) {
    try {
        const resp = await fetch(url, {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
            body: JSON.stringify(payload)
        });
        const text = await resp.text();
        let json = null;
        try { json = JSON.parse(text); } catch (e) { /* not JSON */ }
        console.log("POST", url, "status", resp.status, "json:", json, "text:", text);
        return { ok: resp.ok, status: resp.status, json, text, raw: resp };
    } catch (err) {
        console.error("Network error postJson:", err);
        return { ok: false, status: 0, error: err };
    }
}

// optional polling function (comment out startBookedPolling() call later to disable)
let bookedPollingTimer = null;
async function fetchBookedSeats(csrftoken) {
    try {
        const resp = await fetch("/booked-seats/", { credentials: "same-origin" });
        const txt = await resp.text();
        if (!resp.ok) { console.warn("/booked-seats returned", resp.status, txt); return []; }
        return JSON.parse(txt);
    } catch (err) { console.warn("fetchBookedSeats err:", err); return []; }
}
function startBookedPolling(intervalMs = 15000) {
    if (bookedPollingTimer) clearInterval(bookedPollingTimer);
    bookedPollingTimer = setInterval(async () => {
        const arr = await fetchBookedSeats(); // uses same-origin credentials
        preBooked.clear();
        for (const s of arr) preBooked.add(s);
        document.querySelectorAll(".seat").forEach(el => {
            const id = el.dataset && el.dataset.seat;
            if (!id) return;
            if (preBooked.has(id)) el.classList.add("booked"); else el.classList.remove("booked");
        });
        for (const s of Array.from(window.selectedSeats)) if (preBooked.has(s)) window.selectedSeats.delete(s);
        refreshSummary();
    }, intervalMs);
}

// =========================
// MAIN
// =========================
async function requestTicketGeneration(payload) {
    const resp = await fetch("/generate-ticket/", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
        body: JSON.stringify(payload)
    });

    const data = await resp.json();

    if (resp.ok && data.status === "ok") {
        // force browser to download
        const a = document.createElement("a");
        a.href = data.ticket_url;
        a.download = ""; // browser auto-downloads
        document.body.appendChild(a);
        a.click();
        a.remove();

        alert("Ticket downloaded successfully!");
    } else {
        console.error("Ticket generation failed:", data);
        alert("Error generating ticket. Check server logs.");
    }
}

window.addEventListener("DOMContentLoaded", () => {
    const topContainer = document.getElementById("seats-top");
    const bottomContainer = document.getElementById("seats-bottom");

    // Render rows
    const rowOrder = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P"];
    for (const r of rowOrder) {
        const shape = ROW_SHAPE[r];
        const container = shape.block === "top" ? topContainer : bottomContainer;
        createRow(r, shape, container);
    }

    // expose selected set (already on window.selectedSeats)
    const selectedSeats = window.selectedSeats;

    // debug log to ensure form exists
    console.log("DEBUG: checkout-form element:", document.getElementById("checkout-form"));
    console.log("DEBUG: topContainer/bottomContainer found:", !!topContainer, !!bottomContainer);

    // seat click delegation
    function seatClickHandler(e) {
        const seat = e.target.closest(".seat");
        if (!seat) return;
        if (seat.classList.contains("empty") || seat.classList.contains("booked") || seat.classList.contains("locked")) return;
        const id = seat.dataset.seat;
        if (!id) return;
        if (selectedSeats.has(id)) { selectedSeats.delete(id); seat.classList.remove("selected"); }
        else { selectedSeats.add(id); seat.classList.add("selected"); }
        console.log("DEBUG: clicked", id, "selectedSeats:", Array.from(selectedSeats));
        refreshSummary();
    }
    if (topContainer) topContainer.addEventListener("click", seatClickHandler);
    if (bottomContainer) bottomContainer.addEventListener("click", seatClickHandler);

    refreshSummary();

    // start polling if you want (uncomment to enable)
    // startBookedPolling(15000);

    // payment setup
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    const csrftoken = getCookie('csrftoken');

    const confirmBtn = document.getElementById("confirm-btn");
    const modal = document.getElementById("checkout-modal");
    const cancelBtn = document.getElementById("cancel-modal");
    const checkoutForm = document.getElementById("checkout-form");

    if (confirmBtn && modal) {
        confirmBtn.addEventListener("click", () => {
            if (selectedSeats.size === 0) { alert("Please select at least one seat first."); return; }
            modal.classList.add("show");
        });
    }
    if (cancelBtn && modal) cancelBtn.addEventListener("click", () => { modal.classList.remove("show"); });
    window.addEventListener("click", (e) => { if (e.target === document.querySelector(".modal-backdrop")) modal.classList.remove("show"); });

    if (!checkoutForm) {
        console.warn("checkout-form not found. Ensure your HTML has <form id='checkout-form'>");
        return;
    }

    checkoutForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        console.log("DEBUG: checkout submit fired; selectedSeats:", Array.from(selectedSeats));

        const seatsArray = Array.from(selectedSeats);
        if (seatsArray.length === 0) { alert("Select at least one seat"); return; }

        const formData = new FormData(checkoutForm);
        const payload = { name: formData.get("name"), email: formData.get("email"), phone: formData.get("phone"), seats: seatsArray };

        const submitBtn = checkoutForm.querySelector("button[type='submit']");
        if (submitBtn) submitBtn.disabled = true;

        let serverData = null;

        try {
            // 1) create order and lock seats on backend
            const createResult = await postJson("/create-order/", payload, csrftoken);
            if (!createResult.ok) {
                alert("Server error while creating order: " + createResult.text);
                markSeatsAsUnlocked(seatsArray);
                if (submitBtn) submitBtn.disabled = false;
                return;
            }
            serverData = createResult.json;

            // 2) update UI with server locked seats if provided (preferred)
            if (serverData && Array.isArray(serverData.locked_seats) && serverData.locked_seats.length) {
                markSeatsAsBooked(serverData.locked_seats);
            } else {
                // optimistic fallback
                markSeatsAsBooked(seatsArray);
            }

            // 3) validate required fields
            if (!serverData || !serverData.order_id || !serverData.key_id || typeof serverData.amount === "undefined") {
                console.error("Missing payment fields:", serverData);
                alert("Payment initialization failed: missing fields. Check console.");
                // attempt to unlock seats if booking_id exists
                try { if (serverData && serverData.booking_id) await postJson("/unlock-seats/", { booking_id: serverData.booking_id, seats: seatsArray }, csrftoken); } catch (_) { }
                markSeatsAsUnlocked(seatsArray);
                if (submitBtn) submitBtn.disabled = false;
                return;
            }

            // 4) ensure amount is integer paise
            let amountPaise = Number(serverData.amount);
            if (!Number.isInteger(amountPaise)) amountPaise = Math.round(amountPaise * 100);
            if (!(amountPaise > 0)) {
                console.error("Invalid amount:", serverData.amount);
                alert("Invalid payment amount. See console.");
                markSeatsAsUnlocked(seatsArray);
                if (submitBtn) submitBtn.disabled = false;
                return;
            }

            // 5) check Razorpay loaded
            if (typeof Razorpay === "undefined") {
                console.error("Razorpay script missing. Add: <script src='https://checkout.razorpay.com/v1/checkout.js'></script>");
                alert("Payment library not loaded. See console.");
                markSeatsAsUnlocked(seatsArray);
                if (submitBtn) submitBtn.disabled = false;
                return;
            }

            // 6) build options and open checkout
            const options = {
                key: serverData.key_id,
                amount: amountPaise,
                currency: "INR",
                name: "Ticket Booking",
                description: "Seat purchase",
                order_id: serverData.order_id,
                prefill: { name: payload.name, email: payload.email, contact: payload.phone },
                modal: {
                    ondismiss: async function () {
                        console.log("Razorpay modal dismissed by user");
                        try { await postJson("/unlock-seats/", { booking_id: serverData.booking_id || null, seats: seatsArray }, csrftoken); } catch (err) { console.warn("unlock error on dismiss", err); }
                        markSeatsAsUnlocked(seatsArray);
                        alert("Payment cancelled — reserved seats released.");
                    }
                },
                handler: async function (response) {
                    // server-side verification
                    try {
                        const verifyRes = await postJson("/verify-payment/", {
                            booking_id: serverData.booking_id,
                            razorpay_order_id: response.razorpay_order_id,
                            razorpay_payment_id: response.razorpay_payment_id,
                            razorpay_signature: response.razorpay_signature
                        }, csrftoken);

                        if (!verifyRes.ok) {
                            alert("Verification failed: " + verifyRes.text);
                            await postJson("/unlock-seats/", { booking_id: serverData.booking_id, seats: seatsArray }, csrftoken);
                            markSeatsAsUnlocked(seatsArray);
                            return;
                        }
                        // after verification success (inside your handler where vr.status === "ok")
                        async function requestTicketGeneration(serverData) {
                            const payload = {
                                name: payload.name,                // from checkout form
                                email: payload.email,
                                phone: payload.phone,              // include country code e.g. +919xxxxxxxxx
                                seats: seatsArray,                 // your selected seats array
                                booking_id: serverData.booking_id  // passed from create-order
                            };

                            const resp = await fetch("/generate-ticket/", {
                                method: "POST",
                                credentials: "same-origin",
                                headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                                body: JSON.stringify(payload)
                            });

                            const data = await resp.json();
                            if (resp.ok && data.status === "ok") {
                                // open the ticket url in a new tab (this will trigger browser download if it's served with attachment headers)
                                window.open(data.ticket_url, "_blank");
                            } else {
                                console.error("Ticket generation error:", data);
                                alert("Ticket generation failed. Check server logs.");
                            }
                        }

                        const vr = verifyRes.json;
                        // ---- REPLACE existing "if (vr && vr.status === 'ok') { ... }" block with this ----
                        if (vr && vr.status === "ok") {
                            try {
                                // request server to generate + email + whatsapp the ticket
                                const ticketPayload = {
                                    name: payload.name,           // payload is available in outer scope
                                    email: payload.email,
                                    phone: payload.phone,         // ensure this includes country code e.g. "+91..."
                                    seats: seatsArray,
                                    booking_id: serverData.booking_id
                                };

                                const ticketResp = await fetch("/generate-ticket/", {
                                    method: "POST",
                                    credentials: "same-origin",
                                    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
                                    body: JSON.stringify(ticketPayload)
                                });

                                const ticketJson = await ticketResp.json().catch(() => ({}));

                                if (ticketResp.ok && ticketJson.status === "ok") {
                                    // open ticket in new tab for user to download / view
                                    if (ticketJson.ticket_url) {
                                        window.open(ticketJson.ticket_url, "_blank");
                                    }
                                    const ticketPayload = {
                                        name: payload.name,
                                        email: payload.email,
                                        phone: payload.phone,
                                        seats: seatsArray,
                                        booking_id: serverData.booking_id
                                    };

                                    // generate + download ticket
                                    await requestTicketGeneration(ticketPayload);

                                    alert("Payment successful! Ticket has been downloaded.");

                                    // refresh page AFTER download
                                    window.location.reload();

                                } else {
                                    console.error("Ticket generation failed:", ticketJson);
                                    alert("Payment succeeded but ticket generation failed. Check server logs.");
                                    // still reload so UI reflects the booking
                                    window.location.reload();
                                }
                            } catch (err) {
                                console.error("Ticket request error:", err);
                                alert("Ticket generation request failed. See console.");
                                window.location.reload();
                            }
                        }
                        else {
                            alert("Verification failed: " + (vr && vr.error ? vr.error : "unknown"));
                            await postJson("/unlock-seats/", { booking_id: serverData.booking_id, seats: seatsArray }, csrftoken);
                            markSeatsAsUnlocked(seatsArray);
                        }
                    } catch (err) {
                        console.error("verify handler error:", err);
                        alert("Verification JS error: " + err.message);
                        try { await postJson("/unlock-seats/", { booking_id: serverData.booking_id, seats: seatsArray }, csrftoken); } catch (e) { }
                        markSeatsAsUnlocked(seatsArray);
                    }
                }
            };

            const rzp = new Razorpay(options);
            rzp.on('payment.failed', async function (resp) {
                console.warn("payment.failed", resp);
                alert("Payment failed or cancelled.");
                try { await postJson("/unlock-seats/", { booking_id: serverData.booking_id || null, seats: seatsArray }, csrftoken); } catch (e) { console.warn("unlock failed", e); }
                markSeatsAsUnlocked(seatsArray);
                window.location.reload();
            });

            rzp.open();

        } catch (err) {
            console.error("Checkout error:", err);
            alert("Checkout error: " + (err && err.message));
            markSeatsAsUnlocked(seatsArray);
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });

}); // DOMContentLoaded end
