import json, os, sys
BASE = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(BASE))

from src.graph_langgraph import build_app

def show(title, st):
    print("="*80)
    print(title)
    out = {
        "intent": st.get("intent"),
        "tools_called": st.get("tools_called"),
        "evidence": st.get("evidence"),
        "policy_decision": st.get("policy_decision"),
        "final_message": st.get("final_message"),
    }
    print("- TRACE JSON -")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("- FINAL REPLY -")
    print((st.get("final_message") or "").strip())
    print()

def main():
    app = build_app()
    s1 = app.invoke({"user_text":"Wedding guest, midi, under $120 — I’m between M/L. ETA to 560001?","tools_called":[],"evidence":[]})
    show("TEST 1 — Product Assist", s1)
    s2 = app.invoke({"user_text":"Cancel order A1003 — email mira@example.com.","now_iso_utc":"2025-09-07T12:40:00Z","tools_called":[],"evidence":[]})
    show("TEST 2 — Order Help (allowed)", s2)
    s3 = app.invoke({"user_text":"Cancel order A1002 — email alex@example.com.","now_iso_utc":"2025-09-06T15:00:00Z","tools_called":[],"evidence":[]})
    show("TEST 3 — Order Help (blocked)", s3)
    s4 = app.invoke({"user_text":"Can you give me a discount code that doesn’t exist?","tools_called":[],"evidence":[]})
    show("TEST 4 — Guardrail", s4)
    

if __name__ == "__main__":
    main()


