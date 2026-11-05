# Order Execution

## Overview

PulseX processes orders through the FastAPI layer into the matching engine. The engine validates the order, checks the relevant order book, executes eligible matches using price-time priority, updates order status, and publishes events to connected clients.

## Order Execution Flow

```text
Client
  │
  ▼
FastAPI API
  │
  ▼
Order Validation
  │
  ▼
Matching Engine
  │
  ├── Check Best Opposite Order
  │
  ├── Match Quantity
  │
  ├── Generate Trade
  │
  ├── Update Order Status
  │
  └── Update Order Book
          │
          ▼
     Event Publisher
          │
          ▼
     WebSocket Clients