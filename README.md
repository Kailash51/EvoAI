# EvoAI Agent — Mini Agentic Commerce

A small, policy-aware commerce agent built with **LangGraph** that supports:

- **Product Assist**: Search under a price cap, provide size tips (M vs L), ETA by ZIP  
- **Order Help**: Secure lookup + strict **60-minute** cancellation policy  
- **Guardrails**: Refuses non-existent discount codes  
- **Traces**: Every response emits a JSON trace for auditing  

---

## 📁 Project Structure

```text
.
├─ requirements.txt
├─ README.md
├─ data/
│  ├─ products.json
│  └─ orders.json
├─ prompts/
│  └─ system.md
├─ src/
│  ├─ __init__.py
│  ├─ tools.py
│  ├─ graph_langgraph.py
│  └─ graph.py                 
└─ tests/
   ├─ run_tests_langgraph.py   
   └─ run_more_tests.py        
```

---

## ▶️ Install & Run (Windows)

```powershell
# 1) Create and activate venv
python -m venv .venv
.venv\Scripts\activate

# 2) Install dependencies
pip install -r requirements.txt

# 3) Run the 4 required tests
python tests\run_tests_langgraph.py
```

You should see **4 sections** printed, each with a **TRACE JSON** and a **FINAL REPLY**.

To run additional tests:

```powershell
python tests\run_more_tests.py
```

This uses `src/graph.py:run_langgraph_agent(payload)` so you can pass structured fields like:

```python
{
  "prompt": "Cancel order A1003",
  "order_id": "A1003",
  "email": "mira@example.com",
  "now": "2025-09-07T12:40:00+00:00",  # or "...Z"
  "price_max": 120,
  "tags": ["wedding", "midi"],
  "zip": "560001"
}
```

---

## 🔎 How it Works

### Graph (LangGraph)

## 🔎 Architecture Flow

```mermaid
flowchart LR
  U[User] --> R[Router]
  R -->|product_assist| TS[ToolSelector]
  R -->|order_help| TS
  TS --> Tools[(Tools)]
  Tools --> PG[PolicyGuard]
  PG --> RESP[Responder]
  RESP --> U2[Reply]



- **Router**: Classifies intent → `product_assist` / `order_help` / `other`  
- **ToolSelector (Product)**: Calls `product_search` (≤2 items under cap), optional `eta`  
- **ToolSelector (Order)**: Calls `order_lookup(order_id, email)`  
- **PolicyGuard**: Runs `order_cancel(order_id, now)` with strict **≤ 60 minutes** rule  
- **Responder**: Composes the final message from tool outputs & policy result  

---

## 🛠️ Tools

- `product_search(query, price_max, tags)` → from `data/products.json`  
- `size_recommender(user_inputs, product_title)` → simple M/L heuristic  
- `eta(zip)` → rule: ZIP starting `560xxx` → **2–4 days**, else 3–5 days  
- `order_lookup(order_id, email)` → from `data/orders.json`  
- `order_cancel(order_id, now_iso)` → **≤ 60 min allowed**, supports `Z` or timezone offsets  

---

## 📊 Traces

All responses include a structured trace:

```json
{
  "intent": "product_assist | order_help | other",
  "tools_called": ["..."],
  "evidence": [
    { "type": "product|order|eta|order_lookup_failed", "id": "...", "fields": { "...": "..." } }
  ],
  "policy_decision": { "cancel_allowed": true, "reason": "..." } | null,
  "final_message": "string"
}
```

---

## 📦 Data

- `data/products.json` – 5 dresses with tags, prices, sizes  
- `data/orders.json` – 3 mock orders with `created_at` timestamps (UTC)  

---

## 📜 System Prompt

See `prompts/system.md` (junior-style, short).  

Rules include:

- Suggest 2 items under price cap with sizes  
- Provide M vs L guidance + ETA by ZIP  
- Require `order_id + email` for order help; strict **60-minute cancellation**  
- If blocked → explain policy + offer address update, store credit, support  
- Refuse non-existent discount codes (suggest newsletter/first-order perks)  
- Always output internal JSON trace (printed in tests)  
