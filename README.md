# ted-ai-countdown

A full-screen countdown, meant for a dedicated wall screen, of the days left until Top-Expert-Dominating AI (TED-AI) according to the AI Futures Project. It shows the mean of the five authors' median forecast dates, each author's own date, and a ticking clock, and it picks up new forecasts on its own when the project publishes a timelines update. Built 2026-11-17.

## How it works

- `server.py` runs under launchd and does two things: serves `web/` on port 8805 to the whole LAN, and every 6 hours reads the blog feed (`https://blog.aifutures.org/feed`).
- Feed parsing: it takes the newest post containing a paragraph that mentions "TED-AI" and "median" and lists at least three `Name Mon YYYY` pairs (the caption under the forecast-history chart, e.g. "Daniel Sep 2027 (from late 2028), Eli Sep 2028 ..."). If that post is newer than the stored one, the stored forecasts are replaced.
- If a post with "timeline" in its title is newer than the stored source but could not be parsed, the page shows an amber "Newer post not yet reflected" notice instead of staying silently stale. Fix by editing the state file by hand (below) or adjusting the parser.
- The page (`web/index.html`) fetches `/forecasts.json` every 5 minutes and ticks every second. Each median is given to the month, so it is placed at the 15th, noon UTC; the headline is the mean of those dates. After the date passes it counts up as "Days since".
- The page reloads itself when `index.html` changes on disk, and keeps the last forecasts in `localStorage` so it still counts down if the Mac is unreachable (it then says "offline").
- No LLM calls and no dependencies beyond the Python standard library.

What the number is and is not: it is the average of the authors' *median* (50/50) dates, conditional on no deliberate slowdown. It is not the expected time to TED-AI. The distributions have long right tails, so the true expectation is later and cannot be computed from published medians.

## Files

| File | Purpose |
| --- | --- |
| `server.py` | Web server plus feed checker; `--test` for a dry run |
| `web/index.html` | The countdown page |
| `forecasts.seed.json` | Forecasts from the 2026-11-10 update, used until the state file exists |
| `com.elityre.ted-ai-countdown.plist` | launchd agent (RunAtLoad, KeepAlive) |
| `install.sh` | Copies the plist and restarts the agent |

## Runtime locations

- State: `~/Library/Application Support/TedAiCountdown/forecasts.json`
- Log: `~/Library/Logs/ted-ai-countdown.log`
- Agent: `~/Library/LaunchAgents/com.elityre.ted-ai-countdown.plist`, running the code in this folder directly
- Page: `http://Elis-MacBook-Pro-2.local:8805` (or the Mac's IP) from any device on the same network

## Common tasks

```sh
./install.sh                                   # install or restart
/opt/homebrew/bin/python3 server.py --test     # fetch + parse the feed, print, change nothing
tail -f ~/Library/Logs/ted-ai-countdown.log    # logs
launchctl bootout gui/$(id -u)/com.elityre.ted-ai-countdown   # stop
open http://localhost:8805                     # view
```

To set forecasts by hand, edit `medians` (and `source_date`) in the state file; the page picks it up within 5 minutes.

## Settings that matter

- The screen must be on the same network as this Mac, and the Mac must be awake for forecast updates (the page keeps counting without it).
- macOS may ask once to allow Python to accept incoming connections; allow it.

## Gotchas learned

- The name/month pattern also matches ordinary prose such as "The Nov 2026 points"; `NOT_NAMES` in `server.py` filters those. Run `--test` after any new update and check the names.
- The per-author forecast table in the posts is an image, so the chart caption is the only machine-readable source of all five medians.
