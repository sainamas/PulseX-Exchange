const API_BASE = window.location.origin;

let currentSymbol = "BTC-USD";
let currentSide = "BUY";
let websocket = null;

const elements = {
    bestBid: document.getElementById("bestBid"),
    bestAsk: document.getElementById("bestAsk"),
    spread: document.getElementById("spread"),
    lastTrade: document.getElementById("lastTrade"),

    orderBookSymbol: document.getElementById("orderBookSymbol"),
    orderBookSpread: document.getElementById("orderBookSpread"),
    midPrice: document.getElementById("midPrice"),

    asks: document.getElementById("asks"),
    bids: document.getElementById("bids"),

    tradesTable: document.getElementById("tradesTable"),
    ordersTable: document.getElementById("ordersTable"),

    orderType: document.getElementById("orderType"),
    quantity: document.getElementById("quantity"),
    price: document.getElementById("price"),
    priceField: document.getElementById("priceField"),
    traderId: document.getElementById("traderId"),

    buyButton: document.getElementById("buyButton"),
    sellButton: document.getElementById("sellButton"),
    submitOrder: document.getElementById("submitOrder"),

    orderMessage: document.getElementById("orderMessage"),

    connectionDot: document.getElementById("connectionDot"),
    connectionText: document.getElementById("connectionText"),

    activityLog: document.getElementById("activityLog"),
};


function formatNumber(value, decimals = 4) {
    if (value === null || value === undefined) {
        return "—";
    }

    return Number(value).toLocaleString(
        undefined,
        {
            minimumFractionDigits: 0,
            maximumFractionDigits: decimals,
        }
    );
}


function formatPrice(value) {
    return formatNumber(value, 2);
}


function formatQuantity(value) {
    return formatNumber(value, 4);
}


function formatTime(timestamp) {
    if (!timestamp) {
        return "—";
    }

    return new Date(timestamp).toLocaleTimeString();
}


function setConnectionStatus(connected) {
    elements.connectionDot.classList.toggle(
        "online",
        connected
    );

    elements.connectionDot.classList.toggle(
        "offline",
        !connected
    );

    elements.connectionText.textContent =
        connected
            ? "Live"
            : "Disconnected";
}


function showMessage(message, type = "success") {
    elements.orderMessage.textContent = message;

    elements.orderMessage.classList.remove(
        "hidden",
        "success",
        "error"
    );

    elements.orderMessage.classList.add(
        type
    );

    window.clearTimeout(
        showMessage.timeout
    );

    showMessage.timeout =
        window.setTimeout(() => {
            elements.orderMessage.classList.add(
                "hidden"
            );
        }, 5000);
}


function addActivity(
    eventType,
    data
) {
    const entry =
        document.createElement("div");

    entry.className =
        "activity-entry";

    const time =
        document.createElement("span");

    time.className =
        "activity-time";

    time.textContent =
        formatTime(
            new Date().toISOString()
        );

    const type =
        document.createElement("span");

    type.className =
        "activity-type";

    type.textContent =
        eventType;

    const payload =
        document.createElement("span");

    payload.className =
        "activity-data";

    payload.textContent =
        JSON.stringify(data);

    entry.appendChild(time);
    entry.appendChild(type);
    entry.appendChild(payload);

    elements.activityLog.prepend(
        entry
    );

    while (
        elements.activityLog.children.length > 100
    ) {
        elements.activityLog.removeChild(
            elements.activityLog.lastChild
        );
    }
}


function updateMarketStats(data) {
    const bestBid =
        data.best_bid;

    const bestAsk =
        data.best_ask;

    const spread =
        data.spread;

    elements.bestBid.textContent =
        formatPrice(bestBid);

    elements.bestAsk.textContent =
        formatPrice(bestAsk);

    elements.spread.textContent =
        formatPrice(spread);

    elements.orderBookSpread.textContent =
        formatPrice(spread);

    if (
        bestBid !== null &&
        bestBid !== undefined &&
        bestAsk !== null &&
        bestAsk !== undefined
    ) {
        elements.midPrice.textContent =
            formatPrice(
                (Number(bestBid) +
                    Number(bestAsk)) /
                2
            );
    } else if (
        bestBid !== null &&
        bestBid !== undefined
    ) {
        elements.midPrice.textContent =
            formatPrice(bestBid);
    } else if (
        bestAsk !== null &&
        bestAsk !== undefined
    ) {
        elements.midPrice.textContent =
            formatPrice(bestAsk);
    } else {
        elements.midPrice.textContent =
            "—";
    }

    if (data.latest_trade) {
        elements.lastTrade.textContent =
            formatPrice(
                data.latest_trade.price
            );
    }
}


function renderOrderBook(book) {
    renderBookSide(
        elements.asks,
        book.asks || [],
        "ask"
    );

    renderBookSide(
        elements.bids,
        book.bids || [],
        "bid"
    );
}


function renderBookSide(
    container,
    levels,
    side
) {
    container.innerHTML = "";

    if (!levels.length) {
        const empty =
            document.createElement("div");

        empty.className =
            "empty-state";

        empty.textContent =
            side === "ask"
                ? "No asks"
                : "No bids";

        container.appendChild(
            empty
        );

        return;
    }

    levels.forEach(level => {
        const row =
            document.createElement("div");

        row.className =
            `book-row ${side}-row`;

        const price =
            document.createElement("span");

        price.textContent =
            formatPrice(
                level.price
            );

        const quantity =
            document.createElement("span");

        quantity.textContent =
            formatQuantity(
                level.quantity
            );

        row.appendChild(price);
        row.appendChild(quantity);

        container.appendChild(row);
    });
}


function applyMarketData(data) {
    updateMarketStats(
        data
    );

    if (data.order_book) {
        renderOrderBook(
            data.order_book
        );
    }
}


async function loadMarketData() {
    try {
        const response =
            await fetch(
                `${API_BASE}/market-data/${encodeURIComponent(currentSymbol)}`
            );

        if (!response.ok) {
            throw new Error(
                "Unable to load market data"
            );
        }

        const data =
            await response.json();

        applyMarketData(
            data
        );

    } catch (error) {
        addActivity(
            "ERROR",
            {
                message:
                    error.message,
            }
        );
    }
}


async function loadTrades() {
    try {
        const response =
            await fetch(
                `${API_BASE}/trades/${encodeURIComponent(currentSymbol)}`
            );

        if (!response.ok) {
            throw new Error(
                "Unable to load trades"
            );
        }

        const trades =
            await response.json();

        renderTrades(
            trades
        );

    } catch (error) {
        addActivity(
            "ERROR",
            {
                message:
                    error.message,
            }
        );
    }
}


function renderTrades(trades) {
    elements.tradesTable.innerHTML = "";

    const recentTrades =
        [...trades]
            .reverse()
            .slice(0, 20);

    if (!recentTrades.length) {
        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td colspan="4" class="empty-table">
                No trades yet
            </td>
        `;

        elements.tradesTable.appendChild(
            row
        );

        return;
    }

    recentTrades.forEach(trade => {
        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td>${escapeHtml(
                formatTime(
                    trade.timestamp
                )
            )}</td>

            <td>
                ${escapeHtml(
                    formatPrice(
                        trade.price
                    )
                )}
            </td>

            <td>
                ${escapeHtml(
                    formatQuantity(
                        trade.quantity
                    )
                )}
            </td>

            <td>
                ${escapeHtml(
                    trade.symbol
                )}
            </td>
        `;

        elements.tradesTable.appendChild(
            row
        );
    });
}


async function loadOrders() {
    try {
        const response =
            await fetch(
                `${API_BASE}/orders?symbol=${encodeURIComponent(currentSymbol)}`
            );

        if (!response.ok) {
            throw new Error(
                "Unable to load orders"
            );
        }

        const orders =
            await response.json();

        renderOrders(
            orders
        );

    } catch (error) {
        addActivity(
            "ERROR",
            {
                message:
                    error.message,
            }
        );
    }
}


function renderOrders(orders) {
    elements.ordersTable.innerHTML = "";

    const recentOrders =
        [...orders]
            .reverse()
            .slice(0, 20);

    if (!recentOrders.length) {
        const row =
            document.createElement("tr");

        row.innerHTML = `
            <td colspan="7" class="empty-table">
                No orders yet
            </td>
        `;

        elements.ordersTable.appendChild(
            row
        );

        return;
    }

    recentOrders.forEach(order => {
        const row =
            document.createElement("tr");

        const sideClass =
            order.side === "BUY"
                ? "side-buy"
                : "side-sell";

        const statusClass =
            order.status
                .toLowerCase()
                .replaceAll(
                    "_",
                    "-"
                );

        const canCancel =
            order.status === "NEW" ||
            order.status ===
                "PARTIALLY_FILLED";

        row.innerHTML = `
            <td class="${sideClass}">
                ${escapeHtml(
                    order.side
                )}
            </td>

            <td>
                ${escapeHtml(
                    order.order_type
                )}
            </td>

            <td>
                ${
                    order.price === null
                        ? "Market"
                        : escapeHtml(
                            formatPrice(
                                order.price
                            )
                        )
                }
            </td>

            <td>
                ${escapeHtml(
                    formatQuantity(
                        order.quantity
                    )
                )}
            </td>

            <td>
                ${escapeHtml(
                    formatQuantity(
                        order.filled_quantity
                    )
                )}
            </td>

            <td>
                <span class="status status-${statusClass}">
                    ${escapeHtml(
                        order.status
                    )}
                </span>
            </td>

            <td>
                <button
                    class="cancel-button"
                    data-order-id="${escapeHtml(
                        order.order_id
                    )}"
                    ${canCancel ? "" : "disabled"}
                >
                    Cancel
                </button>
            </td>
        `;

        elements.ordersTable.appendChild(
            row
        );
    });

    document
        .querySelectorAll(
            ".cancel-button:not(:disabled)"
        )
        .forEach(button => {
            button.addEventListener(
                "click",
                () => {
                    cancelOrder(
                        button.dataset.orderId
                    );
                }
            );
        });
}


async function cancelOrder(
    orderId
) {
    try {
        const response =
            await fetch(
                `${API_BASE}/orders/${encodeURIComponent(orderId)}`,
                {
                    method: "DELETE",
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Unable to cancel order"
            );
        }

        showMessage(
            "Order cancelled successfully.",
            "success"
        );

        addActivity(
            "ORDER_CANCELLED",
            data
        );

        await loadMarketData();
        await loadOrders();

    } catch (error) {
        showMessage(
            error.message,
            "error"
        );

        addActivity(
            "ERROR",
            {
                message:
                    error.message,
            }
        );
    }
}


function setSide(
    side
) {
    currentSide =
        side;

    elements.buyButton.classList.toggle(
        "active",
        side === "BUY"
    );

    elements.sellButton.classList.toggle(
        "active",
        side === "SELL"
    );

    elements.submitOrder.classList.toggle(
        "sell-mode",
        side === "SELL"
    );

    elements.submitOrder.textContent =
        `Submit ${side === "BUY" ? "Buy" : "Sell"} Order`;
}


function updatePriceField() {
    const isMarket =
        elements.orderType.value ===
        "MARKET";

    elements.priceField.style.display =
        isMarket
            ? "none"
            : "block";

    if (isMarket) {
        elements.price.value =
            "";
    }
}


async function submitOrder() {
    const quantity =
        Number(
            elements.quantity.value
        );

    const orderType =
        elements.orderType.value;

    const traderId =
        elements.traderId.value.trim();

    const price =
        elements.price.value === ""
            ? null
            : Number(
                elements.price.value
            );

    if (!quantity || quantity <= 0) {
        showMessage(
            "Enter a valid quantity.",
            "error"
        );

        return;
    }

    if (!traderId) {
        showMessage(
            "Trader ID is required.",
            "error"
        );

        return;
    }

    if (
        orderType === "LIMIT" &&
        (!price || price <= 0)
    ) {
        showMessage(
            "Enter a valid limit price.",
            "error"
        );

        return;
    }

    const payload = {
        symbol:
            currentSymbol,

        side:
            currentSide,

        order_type:
            orderType,

        quantity:
            quantity,

        price:
            orderType === "MARKET"
                ? null
                : price,

        trader_id:
            traderId,
    };

    elements.submitOrder.disabled =
        true;

    try {
        const response =
            await fetch(
                `${API_BASE}/orders`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",
                    },

                    body:
                        JSON.stringify(
                            payload
                        ),
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Order submission failed"
            );
        }

        showMessage(
            `Order ${data.order.order_id} submitted successfully.`,
            "success"
        );

        addActivity(
            "ORDER_SUBMITTED",
            data.order
        );

        if (
            data.trades &&
            data.trades.length
        ) {
            data.trades.forEach(
                trade => {
                    addActivity(
                        "TRADE_EXECUTED",
                        trade
                    );
                }
            );
        }

        elements.quantity.value =
            "";

        if (
            orderType === "LIMIT"
        ) {
            elements.price.value =
                "";
        }

        await loadMarketData();
        await loadTrades();
        await loadOrders();

    } catch (error) {
        showMessage(
            error.message,
            "error"
        );

        addActivity(
            "ERROR",
            {
                message:
                    error.message,
            }
        );

    } finally {
        elements.submitOrder.disabled =
            false;
    }
}


function handleWebSocketEvent(
    event
) {
    if (
        event.event_type ===
        "MARKET_DATA"
    ) {
        applyMarketData(
            event.data
        );

        return;
    }

    if (
        event.event_type ===
        "ORDER_BOOK_UPDATED"
    ) {
        renderOrderBook(
            event.data
        );

        return;
    }

    if (
        event.event_type ===
        "TRADE_EXECUTED"
    ) {
        addActivity(
            event.event_type,
            event.data
        );

        loadTrades();

        return;
    }

    addActivity(
        event.event_type,
        event.data
    );

    if (
        event.event_type ===
        "ORDER_FILLED" ||
        event.event_type ===
        "ORDER_PARTIALLY_FILLED" ||
        event.event_type ===
        "ORDER_CANCELLED"
    ) {
        loadOrders();
    }
}


function connectWebSocket() {
    if (
        websocket &&
        (
            websocket.readyState ===
                WebSocket.OPEN ||
            websocket.readyState ===
                WebSocket.CONNECTING
        )
    ) {
        websocket.close();
    }

    const protocol =
        window.location.protocol ===
        "https:"
            ? "wss:"
            : "ws:";

    const wsUrl =
        `${protocol}//${window.location.host}/ws/${encodeURIComponent(currentSymbol)}`;

    websocket =
        new WebSocket(
            wsUrl
        );

    websocket.onopen =
        () => {
            setConnectionStatus(
                true
            );

            addActivity(
                "CONNECTED",
                {
                    symbol:
                        currentSymbol,
                }
            );
        };

    websocket.onmessage =
        event => {
            try {
                const message =
                    JSON.parse(
                        event.data
                    );

                if (
                    message.event_type ===
                    "ORDERBOOK_SNAPSHOT"
                ) {
                    renderOrderBook(
                        message.data
                    );

                    addActivity(
                        "SNAPSHOT",
                        {
                            symbol:
                                currentSymbol,
                        }
                    );

                    return;
                }

                handleWebSocketEvent(
                    message
                );

            } catch (error) {
                addActivity(
                    "ERROR",
                    {
                        message:
                            "Invalid WebSocket message",
                    }
                );
            }
        };

    websocket.onclose =
        () => {
            setConnectionStatus(
                false
            );

            addActivity(
                "DISCONNECTED",
                {
                    symbol:
                        currentSymbol,
                }
            );
        };

    websocket.onerror =
        () => {
            setConnectionStatus(
                false
            );
        };
}


async function switchSymbol(
    symbol
) {
    if (
        symbol ===
        currentSymbol
    ) {
        return;
    }

    currentSymbol =
        symbol;

    document
        .querySelectorAll(
            ".symbol-button"
        )
        .forEach(button => {
            button.classList.toggle(
                "active",
                button.dataset.symbol ===
                    currentSymbol
            );
        });

    elements.orderBookSymbol.textContent =
        currentSymbol;

    elements.bestBid.textContent =
        "—";

    elements.bestAsk.textContent =
        "—";

    elements.spread.textContent =
        "—";

    elements.lastTrade.textContent =
        "—";

    elements.midPrice.textContent =
        "—";

    elements.asks.innerHTML =
        `
        <div class="empty-state">
            Loading...
        </div>
        `;

    elements.bids.innerHTML =
        `
        <div class="empty-state">
            Loading...
        </div>
        `;

    await loadMarketData();
    await loadTrades();
    await loadOrders();

    connectWebSocket();
}


function escapeHtml(
    value
) {
    return String(value)
        .replaceAll(
            "&",
            "&amp;"
        )
        .replaceAll(
            "<",
            "&lt;"
        )
        .replaceAll(
            ">",
            "&gt;"
        )
        .replaceAll(
            '"',
            "&quot;"
        )
        .replaceAll(
            "'",
            "&#039;"
        );
}


elements.buyButton.addEventListener(
    "click",
    () => {
        setSide(
            "BUY"
        );
    }
);


elements.sellButton.addEventListener(
    "click",
    () => {
        setSide(
            "SELL"
        );
    }
);


elements.orderType.addEventListener(
    "change",
    updatePriceField
);


elements.submitOrder.addEventListener(
    "click",
    submitOrder
);


document
    .querySelectorAll(
        ".symbol-button"
    )
    .forEach(button => {
        button.addEventListener(
            "click",
            () => {
                switchSymbol(
                    button.dataset.symbol
                );
            }
        );
    });


document
    .getElementById(
        "refreshOrders"
    )
    .addEventListener(
        "click",
        loadOrders
    );


document
    .getElementById(
        "clearActivity"
    )
    .addEventListener(
        "click",
        () => {
            elements.activityLog.innerHTML =
                "";
        }
    );


updatePriceField();
setSide("BUY");

loadMarketData();
loadTrades();
loadOrders();
connectWebSocket();// This file will handle dashboard interactions.
// It will communicate with our trading API.// This file will handle dashboard interactions.
// It will communicate with our trading API.
