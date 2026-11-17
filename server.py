#!/opt/homebrew/bin/python3
"""TED-AI countdown: serves a full-screen countdown page to the average of the
AI Futures Project authors' median forecasts for Top-Expert-Dominating AI, and
keeps those forecasts current by checking the project's blog feed.

Runs under launchd as com.elityre.ted-ai-countdown on port 8805.
State:  ~/Library/Application Support/TedAiCountdown/forecasts.json
Log:    ~/Library/Logs/ted-ai-countdown.log
Usage:  server.py          serve the page and check the feed every 6 hours
        server.py --test   fetch and parse the feed once, print, change nothing
"""
import functools
import html
import http.server
import json
import os
import re
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
SEED = os.path.join(HERE, "forecasts.seed.json")
STATE_DIR = os.path.expanduser("~/Library/Application Support/TedAiCountdown")
STATE = os.path.join(STATE_DIR, "forecasts.json")
FEED = "https://blog.aifutures.org/feed"
PORT = 8805
CHECK_EVERY = 6 * 3600

MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
# "Daniel Sep 2027": a first name directly followed by a month and year. The
# updates list each author's median this way in the caption of the history chart.
PAIR = re.compile(r"\b([A-Z][a-z]+) ((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*)\.? (20\d\d)\b")

NOT_NAMES = set("The In By Since From Until Before After On And Of To At Around About Early Late Mid Our".split())


def log(msg):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), msg, flush=True)


def parse_item(content):
    """Return [{name, month}] from the paragraph that lists the authors' TED-AI
    medians, or None if this post has no such paragraph."""
    best = []
    for para in re.findall(r"(?s)<p>(.*?)</p>", content):
        text = html.unescape(re.sub(r"<[^>]+>", "", para))
        if "TED-AI" not in text or "median" not in text.lower():
            continue
        found = {}
        for name, mon, year in PAIR.findall(text):
            if name in NOT_NAMES:  # "The Nov 2026 points are..."
                continue
            found.setdefault(name, "%s-%02d" % (year, MONTHS.index(mon.lower()[:3]) + 1))
        if len(found) > len(best):
            best = [{"name": n, "month": m} for n, m in found.items()]
    # Fewer than three names is more likely prose about one person than the table.
    return best if len(best) >= 3 else None


def parse_feed(xml):
    """Return (latest parsed forecast or None, newest timelines-looking post)."""
    forecast, newest_timelines = None, None
    for item in re.findall(r"(?s)<item>(.*?)</item>", xml):
        def field(tag):
            m = re.search(r"(?s)<%s>(.*?)</%s>" % (tag, tag), item)
            return re.sub(r"^<!\[CDATA\[|\]\]>$", "", m.group(1).strip()) if m else ""
        post = {
            "source_title": html.unescape(field("title")),
            "source_url": field("link"),
            "source_date": parsedate_to_datetime(field("pubDate")).astimezone(timezone.utc).isoformat(),
        }
        if newest_timelines is None and re.search(r"(?i)timeline", post["source_title"]):
            newest_timelines = post
        if forecast is None:
            medians = parse_item(html.unescape(item) if "&lt;p&gt;" in item else item)
            if medians:
                forecast = dict(post, medians=medians)
        if forecast and newest_timelines:
            break
    return forecast, newest_timelines


def fetch_feed():
    req = urllib.request.Request(FEED, headers={"User-Agent": "Mozilla/5.0 (feed reader)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def load_state():
    path = STATE if os.path.exists(STATE) else SEED
    with open(path) as f:
        return json.load(f)


def save_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE)


def check_once():
    state = load_state()
    forecast, newest = parse_feed(fetch_feed())
    if forecast and forecast["source_date"] > state["source_date"]:
        log("new forecasts from %s: %s" % (forecast["source_url"], forecast["medians"]))
        state.update(forecast)
    # A newer timelines post we could not read means the screen may be showing
    # superseded numbers; say so on the page rather than stay silently stale.
    if newest and newest["source_date"] > state["source_date"]:
        state["notice"] = "Newer post not yet reflected: " + newest["source_title"]
        log("WARNING could not parse newer timelines post %s" % newest["source_url"])
    else:
        state["notice"] = ""
    state["checked_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    log("checked feed; source is %s (%d medians)" % (state["source_url"], len(state["medians"])))


def check_loop():
    while True:
        try:
            check_once()
        except Exception as e:  # network down, feed changed shape: keep serving the last good data
            log("ERROR feed check failed: %r" % (e,))
        time.sleep(CHECK_EVERY)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] != "/forecasts.json":
            return super().do_GET()
        state = load_state()
        # The page reloads itself when this changes, so edits reach the screen untouched.
        state["page_version"] = int(os.path.getmtime(os.path.join(WEB, "index.html")))
        body = json.dumps(state).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # the screen polls constantly; request lines would bury real log entries


def main():
    if "--test" in sys.argv:
        forecast, newest = parse_feed(fetch_feed())
        print(json.dumps({"parsed": forecast, "newest_timelines_post": newest}, indent=2))
        sys.exit(0 if forecast else 1)
    threading.Thread(target=check_loop, daemon=True).start()
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), functools.partial(Handler, directory=WEB))
    log("serving on port %d" % PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
