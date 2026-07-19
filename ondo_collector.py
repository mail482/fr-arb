import requests
import time
import json
import os
from datetime import datetime

# Dieses Script macht NUR eine Sache: die aktuelle Ondo-Funding-Rate abholen und in
# ondo_funding_history.json eintragen. Es oeffnet keinen Browser, erzeugt keinen Report -
# das macht weiterhin arb_check.py bei dir lokal. Dieses Script hier ist speziell dafuer
# gedacht, in GitHub Actions (also in der Cloud, 24/7) zu laufen.

ONDO_HISTORY_FILE = "ondo_funding_history.json"
ONDO_MAX_AGE_DAYS = 40

def get_ondo_contracts():
    try:
        r = requests.get(
            "https://api.ondoperps.xyz/v1/perps/contracts",
            params={"sparkline": "false"},
            headers={"User-Agent": "arb-bot/1.0"}
        )
        r.raise_for_status()
        data = r.json()["result"]
        result = {}
        for m in data:
            if m.get("disabled"):
                continue
            ticker = m["market"].replace("-USD.P", "").upper()
            hourly = float(m["fundingRate"])
            result[ticker] = {
                "hourly": hourly,
                "next_funding_ts": m.get("nextFundingRateTimestamp")
            }
        return result
    except Exception as e:
        print("!!! Ondo-Abruf fehlgeschlagen: " + str(e))
        return {}

def load_history(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_history(path, history):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f)

def update_history(history, ondo_contracts):
    now_s = time.time()
    max_age_s = ONDO_MAX_AGE_DAYS * 24 * 3600
    added = 0
    for ticker, info in ondo_contracts.items():
        next_ts = info.get("next_funding_ts")
        if not next_ts:
            continue
        try:
            next_unix = datetime.fromisoformat(next_ts.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        period_unix = next_unix - 3600
        entries = history.get(ticker, [])
        already_have = any(abs(e["t"] - period_unix) < 60 for e in entries)
        if not already_have:
            entries.append({"t": period_unix, "r": info["hourly"]})
            added += 1
        entries = [e for e in entries if now_s - e["t"] <= max_age_s]
        history[ticker] = entries
    return history, added

def main():
    path = os.path.join(os.getcwd(), ONDO_HISTORY_FILE)
    history = load_history(path)
    contracts = get_ondo_contracts()
    print("Ondo-Ticker abgerufen: " + str(len(contracts)))
    history, added = update_history(history, contracts)
    save_history(path, history)
    print("Neue Ablesungen hinzugefuegt: " + str(added))
    total_points = sum(len(v) for v in history.values())
    print("Gesamtzahl gespeicherter Ablesungen: " + str(total_points))

main()
