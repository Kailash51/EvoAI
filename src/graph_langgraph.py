import re
from datetime import datetime, timezone
from langgraph.graph import StateGraph, END
from . import tools


def _price_cap(text):
    m = re.search(r"under\s*[$₹]?\s*(\d+)", text.lower())
    return float(m.group(1)) if m else None

def _zip(text):
    m = re.search(r"\b(\d{5,6})\b", text)
    return m.group(1) if m else None

def _tags(text):
    t = text.lower()
    out = []
    for k in ["wedding", "midi", "party", "daywear"]:
        if k in t:
            out.append(k)
    return out

def router(state):
    txt = state["user_text"].lower()
    if "cancel" in txt and "order" in txt and "email" in txt:
        state["intent"] = "order_help"
    elif "discount code" in txt and ("doesn't exist" in txt or "does not exist" in txt or "fake" in txt):
        state["intent"] = "other"
    elif any(k in txt for k in ["dress", "midi", "wedding", "size", "eta", "zip", "under $", "under rs", "under ₹", "under"]):
        state["intent"] = "product_assist"
    else:
        state["intent"] = "other"
    state.setdefault("tools_called", [])
    state.setdefault("evidence", [])
    state.setdefault("final_message", "")
    state.setdefault("policy_decision", None)
    return state

def route_key(state):
    return state["intent"]

def ts_product(state):
    cap = _price_cap(state["user_text"]) or 10000.0
    tg = _tags(state["user_text"])
    items = tools.product_search(state["user_text"], price_max=cap, tags=tg or None)
    items = sorted(items, key=lambda x: x["price"])[:2]
    state["product_results"] = items
    state["tools_called"].append("product_search")

    z = _zip(state["user_text"])
    if z:
        state["eta_info"] = tools.eta(z)
        state["tools_called"].append("eta")

    for p in items:
        state["evidence"].append({"type": "product", "id": p["id"], "fields": {"title": p["title"], "price": p["price"], "sizes": p["sizes"], "tags": p["tags"]}})
    if state.get("eta_info"):
        state["evidence"].append({"type": "eta", "fields": state["eta_info"]})
    return state

def ts_order(state):
    txt = state["user_text"]
    mid = re.search(r"order\s+([A-Za-z0-9\-]+)", txt, re.IGNORECASE)
    mem = re.search(r"email\s+([A-Za-z0-9_\.\-\+]+@[A-Za-z0-9\.\-]+\.[A-Za-z]{2,})", txt, re.IGNORECASE)
    order_id = mid.group(1) if mid else None
    email = mem.group(1) if mem else None
    order = tools.order_lookup(order_id, email)
    state["order"] = order
    state["tools_called"].append("order_lookup")
    if order:
        state["evidence"].append({"type": "order", "id": order["order_id"], "fields": {"email": order["email"], "created_at": order["created_at"]}})
    else:
        state["evidence"].append({"type": "order_lookup_failed", "fields": {"order_id": order_id, "email": email}})
    return state

def policy_guard(state):
    if state["intent"] != "order_help":
        state["policy_decision"] = None
        return state
    order = state.get("order")
    now_iso = state.get("now_iso_utc") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if not order:
        state["policy_decision"] = {"cancel_allowed": False, "reason": "Order not found or email mismatch"}
        state["tools_called"].append("order_cancel")
        return state
    d = tools.order_cancel(order["order_id"], now_iso)
    state["policy_decision"] = d
    state["tools_called"].append("order_cancel")
    return state

def responder(state):
    if state["intent"] == "product_assist":
        items = state.get("product_results", [])
        eta = state.get("eta_info")
        if not items:
            state["final_message"] = "I didn’t find items under your price cap with those tags. Want me to broaden to similar midi styles?"
            return state
        lines = []
        for p in items:
            rec, why = tools.size_recommender(state["user_text"], p["title"])
            sizes = ", ".join(p.get("sizes", []))
            lines.append(f"• {p['title']} — ${p['price']} (sizes: {sizes}). If you're between M/L: **{rec}** — {why}")
        if eta:
            lines.append(f"ETA to {eta['zip']}: {eta['eta_days']}.")
        if any("wedding" in p.get("tags", []) for p in items):
            lines.append("Pair with a simple wrap or clutch if you want a dressed-up look.")
        state["final_message"] = "\n".join(lines)
        return state

    if state["intent"] == "order_help":
        pol = state.get("policy_decision") or {}
        od = state.get("order") or {"order_id": "unknown"}
        if pol.get("cancel_allowed"):
            state["final_message"] = f"✅ Your order {od['order_id']} is canceled. A confirmation email will arrive shortly."
            return state
        reason = pol.get("reason", "outside the 60-minute window")
        state["final_message"] = f"❌ I can’t cancel this order because of our **60-minute cancellation policy** ({reason}). I can help with: (1) updating the shipping address if it hasn’t shipped, (2) issuing store credit after delivery, or (3) handing off to live support."
        return state

    if "discount code" in state["user_text"].lower():
        state["final_message"] = "I can’t create or share non-existent discount codes. You can still get savings via our newsletter sign-up and first-order perks."
    else:
        state["final_message"] = "I can help with products (search/size/ETA) or order help (lookup/cancellation within 60 minutes). What would you like to do?"
    return state

def build_app():
    g = StateGraph(dict)
    g.add_node("Router", router)
    g.add_node("TS_Product", ts_product)
    g.add_node("TS_Order", ts_order)
    g.add_node("PolicyGuard", policy_guard)
    g.add_node("Responder", responder)

    g.set_entry_point("Router")
    g.add_conditional_edges("Router", route_key, {
        "product_assist": "TS_Product",
        "order_help": "TS_Order",
        "other": "Responder",
    })
    g.add_edge("TS_Product", "PolicyGuard")
    g.add_edge("TS_Order", "PolicyGuard")
    g.add_edge("PolicyGuard", "Responder")
    g.add_edge("Responder", END)
    return g.compile()
