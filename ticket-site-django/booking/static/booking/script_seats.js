// =========================
// Seat map script for seating chart (manual payment)
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

// Global state
let qtyNeeded = 1;  // How many seats user wants
window.selectedSeats = new Set();

// --- initial booked seats from server-rendered template (if present)
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
const preBooked = new Set(getBookedFromServer());

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

function updateQtyNeeded(change) {
    let newQty = qtyNeeded + change;
    if (newQty >= 1 && newQty <= 5) {
        qtyNeeded = newQty;
        document.getElementById('qty-needed').textContent = qtyNeeded;

        // Calculate and update price
        let estimatedPrice = 0;
        for (let i = 0; i < qtyNeeded; i++) {
            estimatedPrice += BOTTOM_PRICE; // Use bottom price as estimate
        }
        document.getElementById('total-price').textContent = estimatedPrice;
    }
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

    const selectedSeats = window.selectedSeats;

    // seat click delegation - auto-fill N seats
    function seatClickHandler(e) {
        const seat = e.target.closest(".seat");
        if (!seat) return;
        if (seat.classList.contains("empty") || seat.classList.contains("booked")) return;

        const id = seat.dataset.seat;
        if (!id) return;

        // If already selected, deselect it
        if (selectedSeats.has(id)) {
            selectedSeats.delete(id);
            seat.classList.remove("selected");
        } else if (selectedSeats.size < qtyNeeded) {
            // If not at limit, add it
            selectedSeats.add(id);
            seat.classList.add("selected");
        } else {
            // At limit - replace oldest with this one
            const first = selectedSeats.values().next().value;
            selectedSeats.delete(first);
            document.querySelector(`[data-seat="${first}"]`).classList.remove("selected");

            selectedSeats.add(id);
            seat.classList.add("selected");
        }

        console.log("Seats selected:", Array.from(selectedSeats), "/ Needed:", qtyNeeded);
        refreshSummary();
    }

    if (topContainer) topContainer.addEventListener("click", seatClickHandler);
    if (bottomContainer) bottomContainer.addEventListener("click", seatClickHandler);

    refreshSummary();

    // ===== PAYMENT FLOW =====
    const confirmBtn = document.getElementById("confirm-btn");
    const checkoutModal = document.getElementById("checkout-modal");
    const paymentModal = document.getElementById("payment-modal");
    const cancelBtn = document.getElementById("cancel-modal");
    const checkoutForm = document.getElementById("checkout-form");

    if (confirmBtn && checkoutModal) {
        confirmBtn.addEventListener("click", () => {
            if (selectedSeats.size === 0) {
                alert("Please select at least one seat first.");
                return;
            }
            if (selectedSeats.size > 5) {
                alert("Maximum 5 seats can be booked at a time.");
                return;
            }
            checkoutModal.style.display = "flex";
        });
    }

    if (cancelBtn && checkoutModal) {
        cancelBtn.addEventListener("click", () => {
            checkoutModal.style.display = "none";
        });
    }

    window.addEventListener("click", (e) => {
        const backdrop = e.target.closest(".modal-backdrop");
        if (backdrop) {
            checkoutModal.style.display = "none";
            paymentModal.style.display = "none";
        }
    });

    // Handle checkout form submit
    if (checkoutForm) {
        checkoutForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const name = checkoutForm.querySelector('input[name="name"]').value;
            const email = checkoutForm.querySelector('input[name="email"]').value;
            const phone = checkoutForm.querySelector('input[name="phone"]').value;

            if (!name || !email || !phone) {
                alert("Please fill in all details");
                return;
            }

            // Show payment modal
            checkoutModal.style.display = "none";
            paymentModal.style.display = "flex";

            // Update payment amount
            let total = 0;
            for (const seat of selectedSeats) {
                total += priceForSeat(seat);
            }
            document.getElementById("pay-amount").textContent = total;

            // Store form data for later
            window.checkoutData = { name, email, phone, seats: Array.from(selectedSeats) };
        });
    }

    // Handle UTR submission
    const submitUtrBtn = document.getElementById("submit-utr-btn");
    if (submitUtrBtn) {
        submitUtrBtn.addEventListener("click", async () => {
            const utr = document.getElementById("utr-input").value.trim();
            if (!utr) {
                alert("Please enter Transaction ID");
                return;
            }

            if (!window.checkoutData) {
                alert("Form data missing");
                return;
            }

            submitUtrBtn.disabled = true;
            submitUtrBtn.textContent = "Submitting...";

            try {
                const payload = {
                    ...window.checkoutData,
                    utr: utr
                };

                const response = await fetch("/submit-seats/", {
                    method: "POST",
                    credentials: "same-origin",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrftoken
                    },
                    body: JSON.stringify(payload)
                });

                const result = await response.json();

                if (result.success) {
                    paymentModal.style.display = "none";

                    // Show success modal
                    const successModal = document.getElementById("success-modal");
                    if (successModal) {
                        successModal.classList.add("show");

                        // Add event listener to close button
                        const closeBtn = document.getElementById("close-success-modal");
                        if (closeBtn) {
                            closeBtn.onclick = () => {
                                successModal.classList.remove("show");
                                window.location.href = "/";
                            };
                        }
                        // Auto-redirect after 5 seconds
                        setTimeout(() => {
                            window.location.href = "/";
                        }, 5000);
                    } else {
                        // Fallback if modal doesn't exist
                        window.location.href = "/";
                    }
                } else {
                    alert("Error: " + (result.error || "Unknown error"));
                }
            } catch (err) {
                console.error("Error:", err);
                alert("Error submitting booking: " + err.message);
            } finally {
                submitUtrBtn.disabled = false;
                submitUtrBtn.textContent = "Confirm Booking";
            }
        });
    }
});

// Copy UPI function
function copyUPI() {
    navigator.clipboard.writeText(myUPI).then(() => {
        const msg = document.getElementById("copy-msg");
        if (msg) {
            msg.style.display = "block";
            setTimeout(() => { msg.style.display = "none"; }, 3000);
        }
    });
}

function cancelPayment() {
    document.getElementById("payment-modal").style.display = "none";
    document.getElementById("checkout-modal").style.display = "flex";
    document.getElementById("utr-input").value = "";
}
