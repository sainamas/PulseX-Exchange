# PulseX Exchange Architecture

## 1. Overview

PulseX is a real-time multi-symbol exchange simulation built with Python and FastAPI.

The system is separated into multiple layers so that the core trading logic is independent from the API and web interface.

### Main layers

- Web Trading Terminal
- FastAPI API
- Order Model
- Matching Engine
- Order Book
- Trade and Event System
- WebSocket Market Feed
- In-memory Order Registry

The current implementation supports BTC-USD and ETH-USD trading with limit orders, market orders, price-time priority, FIFO execution, partial fills, order cancellation, self-trade prevention, REST APIs, and real-time WebSocket updates.

---

## 2. System Architecture

```text
                         ┌─────────────────────────┐
                         │       Web Browser        │
                         │     PulseX Terminal      │
                         │        web/              │
                         └────────────┬────────────┘
                                      │
                          REST API / WebSocket
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       FastAPI API        │
                         │      api/main.py         │
                         └────────────┬────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌───────────────┐ ┌───────────────┐ ┌───────────────┐
            │ Order Registry│ │ Request       │ │ WebSocket     │
            │ orders dict   │ │ Validation    │ │ Connection    │
            │               │ │               │ │ Manager       │
            └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
                    │                  │                 │
                    └──────────────────┼─────────────────┘
                                       │
                                       ▼
                         ┌─────────────────────────┐
                         │     Matching Engine      │
                         │    trading/matching.py   │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │       Order Book         │
                         │   trading/order_book.py  │
                         └────────────┬────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                 ┌──────────────┐         ┌──────────────┐
                 │ Bid Levels   │         │ Ask Levels   │
                 │ FIFO Queues  │         │ FIFO Queues  │
                 └──────────────┘         └──────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │     Trade / Event        │
                         │        System            │
                         └────────────┬────────────┘
                                      │
                         ┌────────────┴────────────┐
                         │                         │
                         ▼                         ▼
                 ┌──────────────┐         ┌──────────────┐
                 │ Trade History│         │ Market Data  │
                 │              │         │ Events       │
                 └──────────────┘         └───────┬──────┘
                                                  │
                                                  ▼
                                         ┌────────────────┐
                                         │ WebSocket Feed │
                                         └───────┬────────┘
                                                 │
                                                 ▼
                                         PulseX Terminal