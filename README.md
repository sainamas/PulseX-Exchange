# TradeX — Real-Time Order Matching Engine

A real-time multi-symbol exchange simulation built with Python and FastAPI.

TradeX — Real-Time Order Matching Engine implements core exchange functionality including order matching, price-time priority, FIFO order queues, partial fills, market orders, order cancellation, trade execution, and real-time WebSocket market updates.

## Features

### Trading Engine

- Limit orders
- Market orders
- Buy and sell orders
- Price-time priority
- FIFO matching
- Partial fills
- Multi-level market order execution
- Order cancellation
- Trade generation
- Self-trade prevention
- Order lifecycle tracking

### Order Book

- Separate order books for each symbol
- Bid and ask price levels
- Best bid and ask
- Spread calculation
- Market depth
- FIFO queues at each price level

### API

- FastAPI REST API
- Order submission
- Order lookup
- Order history
- Order cancellation
- Order-book queries
- Trade history
- Market-data endpoint
- Health endpoint

### Real-Time Updates

WebSocket market feeds provide:

- Order submissions
- Trade executions
- Order fills
- Partial fills
- Order cancellations
- Order-book updates
- Market-data updates

### Trading Terminal

The browser-based terminal provides:

- BTC-USD and ETH-USD selection
- Buy/sell order entry
- Limit/market order selection
- Quantity and price input
- Live order book
- Best bid and ask
- Spread
- Latest trade
- Recent trades
- Active orders
- Order cancellation
- Live event activity

## Architecture

```text
                    Trading Terminal
                           │
                    REST / WebSocket
                           │
                           ▼
                     FastAPI API
                           │
                           ▼
                    Matching Engine
                     │           │
                     ▼           ▼
                 Order Book   Trade/Event System
                     │           │
                     └─────┬─────┘
                           ▼
                    Real-Time Feed
