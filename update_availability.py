import urllib.request
import urllib.error
import json
import re
from datetime import datetime, timedelta
import sys

WIX_API_KEY = "IST.eyJraWQiOiJQb3pIX2FDMiIsImFsZyI6IlJTMjU2In0.eyJkYXRhIjoie1wiaWRcIjpcIjY2ZDYyNjEzLTY1ODQtNGMyZC1hYTIzLTA3MmM3ZmRhNDIwOVwiLFwiaWRlbnRpdHlcIjp7XCJ0eXBlXCI6XCJhcHBsaWNhdGlvblwiLFwiaWRcIjpcIjU2MTdmNTI1LTRkMGItNDg1Zi1hNzM2LTE2MWYwNzljY2Q3ZFwifSxcInRlbmFudFwiOntcInR5cGVcIjpcImFjY291bnRcIixcImlkXCI6XCIzOWEyNTBhMC1hNDg2LTRkYWEtOGIwNi02YjFiOWI2OTc2NjNcIn19IiwiaWF0IjoxNzc3ODA3ODAxfQ.D0vlLeXW9Ixq-9A13KgTAsT5SSlsq3rFkwdnLwbY66QVAyhSZcl-EhVOaeoZ6LeoHPYhJVpTPMmX2NlPE9-5rVf0dfFZ9A_mfbz2CUBQXIQEwcqraQ0WWLzneMuGXuSTPOeqlDAduOPWYtVPchm_3d5Id1Ir-yFLOMiHj_MGZunjcn9KgqbVKyLOrmzvohBVVVULCvyHSuxAcJ77sd0cVPkYh4QL2230gbKVMwOWlRmbLt3MpHYU2VjKLlaEMSNmYWoynC8akgB3bAnOlXTicVdDCulnZpFUcH6w4iSDHEARQNkLnFkkBy_mUHQttXOAa9HChgn5qprDyG8ubRYgEw"
SITE_ID = "5e8a071f-9e9a-498d-87ab-4a2cc314b404"

SERVICES = {
    "Early Pregnancy Scan (£65)":        "73b244aa-1eff-4f83-826b-2375812588b8",
    "Wellbeing & Gender Reveal (£75)":   "0accf983-be32-48a4-9f92-58dde5228a33",
    "3D/4D Live Scan (£95)":             "79add909-5c20-47c4-8569-0fbd97b52789",
    "Emergency Pregnancy Scan (£250)":   "ec80d195-a675-46e1-b34c-9459ffeb3a08",
}

def fetch_slots(service_id):
    now   = datetime.now()
    later = now + timedelta(days=14)
    fmt   = lambda d: d.strftime("%Y-%m-%dT00:00:00")

    payload = json.dumps({
        "serviceId":     service_id,
        "fromLocalDate": fmt(now),
        "toLocalDate":   fmt(later),
        "bookable":      True,
        "timeZone":      "Europe/London",
        "cursorPaging":  {"limit": 50}
    }).encode()

    req = urllib.request.Request(
        "https://www.wixapis.com/_api/service-availability/v2/time-slots",
        data=payload,
        headers={
            "Content-Type":  "application/json",
            "Authorization": WIX_API_KEY,
            "wix-site-id":   SITE_ID,
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"HTTP error {e.code} for service {service_id}: {e.read()}")
        return []

    slots = data.get("timeSlots", [])
    by_day = {}
    for s in slots:
        start = s.get("localStartDate", "")
        if not start:
            continue
        day = start[:10]
        by_day.setdefault(day, []).append(start[11:16])

    lines = []
    for day in sorted(by_day)[:5]:
        d = datetime.strptime(day, "%Y-%m-%d")
        label = d.strftime("%A %-d %B")
        times = ", ".join(by_day[day][:6])
        lines.append(f"  - {label}: {times}")
    return lines

def build_availability_block():
    updated = datetime.now().strftime("%A %-d %B %Y at %H:%M")
    lines = [f"CURRENT LIVE AVAILABILITY (updated {updated}):\n"]
    for name, sid in SERVICES.items():
        lines.append(f"{name}:")
        if "Emergency" in name:
            lines.append("  - Available evenings 7 days a week.")
            lines.append("  - Must call/email at least 2 hours in advance.")
            lines.append("  - Phone: 0127 642 3372 | Email: info@mybabyultrasound.co.uk")
        else:
            slots = fetch_slots(sid)
            if slots:
                lines.extend(slots)
            else:
                lines.append("  - No availability found in the next 14 days. Please call to enquire.")
        lines.append("")
    return "\n".join(lines)

def update_html(html_path, availability_block):
    with open(html_path, "r") as f:
        content = f.read()

    # Replace everything between the AVAILABILITY markers
    pattern = r"(const AVAILABILITY = `)([^`]*)(`;)"
    replacement = r"\g<1>" + availability_block.replace("\\", "\\\\").replace("`", "\\`") + r"\g<3>"
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("ERROR: Could not find AVAILABILITY marker in HTML file.")
        sys.exit(1)

    with open(html_path, "w") as f:
        f.write(new_content)

    print(f"Updated availability in {html_path}")
    print(availability_block)

if __name__ == "__main__":
    html_file = "mybaby-chatbot.html"
    block = build_availability_block()
    update_html(html_file, block)
