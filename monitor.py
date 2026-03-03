import requests
import json
import os
import sys
from datetime import datetime

URL = os.environ["TARGET_URL"]
TEXT = os.environ["TARGET_TEXT"]
PHONE = os.environ["PHONE"]
TEXTBELT_KEY = os.environ["TEXTBELT_APIKEY"]

STATE_FILE = "state.json"
LOG_FILE = "monitor.log"


def log(message):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    entry = f"[{timestamp}] {message}"
    print(entry, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(entry + "\n")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"text_found": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_page():
    response = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    response.raise_for_status()
    return response.text


def send_sms(message):
    resp = requests.post(
        "https://textbelt.com/text",
        {"phone": PHONE, "message": message, "key": TEXTBELT_KEY},
        timeout=15,
    )
    result = resp.json()
    if result.get("success"):
        log(f"SMS sent. Remaining quota: {result.get('quotaRemaining', '?')}")
    else:
        log(f"SMS failed: {result.get('error', 'unknown error')}")


def main():
    state = load_state()
    prev_found = state.get("text_found")

    try:
        page_content = fetch_page()
    except Exception as e:
        log(f"ERROR fetching {URL}: {e}")
        sys.exit(1)

    text_found = TEXT in page_content
    log(f"Checked {URL} | Looking for: '{TEXT}' | Found: {text_found} | Previously: {prev_found}")

    if prev_found is None:
        log("First run — baseline established. No alert sent.")
    elif text_found and not prev_found:
        msg = f"ALERT: '{TEXT}' now APPEARS at {URL}"
        log(msg)
        send_sms(msg)
    elif not text_found and prev_found:
        msg = f"ALERT: '{TEXT}' has DISAPPEARED from {URL}"
        log(msg)
        send_sms(msg)
    else:
        log("No change detected.")

    state["text_found"] = text_found
    save_state(state)


if __name__ == "__main__":
    main()
