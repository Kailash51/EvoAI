import json, os, re
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _load_products():
    with open(os.path.join(DATA_DIR, "products.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def _load_orders():
    with open(os.path.join(DATA_DIR, "orders.json"), "r", encoding="utf-8") as f:
        return json.load(f)

def product_search(query, price_max=None, tags=None):
    items = _load_products()
    out = []
    for p in items:
        if price_max is not None and p["price"] > price_max:
            continue
        if tags:
            ok = True
            for t in tags:
                if t not in p.get("tags", []):
                    ok = False
                    break
            if not ok:
                continue
        out.append(p)
    return out

def size_recommender(user_inputs, product_title=""):
    text = (user_inputs or "").lower()
    between = ("m/l" in text) or ("m or l" in text) or ("between m" in text)
    if between and "bodycon" in product_title.lower():
        return "L", "Bodycon runs close to body; L gives a little more comfort."
    if between:
        return "M", "Between sizes; regular cut—M for cleaner fit (L if you want more ease)."
    return "M", "Defaulting to M unless you prefer extra ease."

def eta(zip_code):
    z = str(zip_code).strip()
    # 560xxx → 2–4 days, else 3–5 days
    if len(z) == 6 and z.startswith("560"):
        return {"zip": z, "eta_days": "2–4 days"}
    return {"zip": z, "eta_days": "3–5 days"}

def order_lookup(order_id, email):
    if not order_id or not email:
        return None
    orders = _load_orders()
    for o in orders:
        if o["order_id"].lower() == order_id.lower().strip() and o["email"].lower() == email.lower().strip():
            return o
    return None

def _parse_iso_z(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

def order_cancel(order_id, now_iso_utc):
    orders = _load_orders()
    found = None
    for o in orders:
        if o["order_id"].lower() == order_id.lower().strip():
            found = o
            break
    if not found:
        return {"cancel_allowed": False, "reason": "Order not found"}

    now = _parse_iso_z(now_iso_utc)
    created = _parse_iso_z(found["created_at"])
    mins = (now - created).total_seconds() / 60
    if mins <= 60:
        return {"cancel_allowed": True, "reason": f"{mins:.0f} minutes since order"}
    return {"cancel_allowed": False, "reason": f">{int(mins)} minutes since order (policy: ≤60 min)"}
