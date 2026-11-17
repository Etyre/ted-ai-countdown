# ted-ai-countdown

A full-screen countdown, meant for a dedicated wall screen, of the days left until Top-Expert-Dominating AI (TED-AI) according to the AI Futures Project. It shows the mean of the five authors' median forecast dates, each author's own date, and a ticking clock, and it picks up new forecasts on its own when the project publishes a timelines update. It is hosted on GitHub Pages at https://etyre.github.io/ted-ai-countdown/ and kept current by GitHub Actions, so the screen does not need the Mac. Built 2026-11-17.

## How it works

- Hosted copy (what the screen loads): the workflow in `.github/workflows/publish.yml` runs on every push and every 6 hours. It runs `server.py --publish _site`, which reads the blog feed (`https://blog.aifutures.org/feed`), updates `web/forecasts.json` if the forecasts changed (the workflow commits that), and deploys `_site` to GitHub Pages. If the feed check fails it redeploys the last committed forecasts.
- Local copy (for previewing changes): `server.py` under launchd serves `web/` on port 8805 to the LAN and checks the same feed every 6 hours, keeping its own state file.
- Feed parsing: it takes the newest post containing a paragraph that mentions "TED-AI" and "median" and lists at least three `Name Mon YYYY` pairs (the caption under the forecast-history chart, e.g. "Daniel Sep 2027 (from late 2028), Eli Sep 2028 ..."). If that post is newer than the stored one, the stored forecasts are replaced.
- If a post with "timeline" in its title is newer than the stored source but could not be parsed, the page shows an amber "Newer post not yet reflected" notice instead of staying silently stale. Fix by editing the state file by hand (below) or adjusting the parser.
- The page (`web/index.html`) fetches `/forecasts.json` every 5 minutes and ticks every second. Each median is given to the month, so it is placed at the 15th, noon UTC; the headline is the mean of those dates. After the date passes it counts up as "Days since".
- The page reloads itself when `index.html` changes (a checksum travels in `forecasts.json`), and keeps the last forecasts in `localStorage` so it still counts down if the host is unreachable (it then says "offline").
- No LLM calls and no dependencies beyond the Python standard library.

What the number is and is not: it is the average of the authors' *median* (50/50) dates, conditional on no deliberate slowdown. It is not the expected time to TED-AI. The distributions have long right tails, so the true expectation is later and cannot be computed from published medians.

## Files

| File | Purpose |
| --- | --- |
| `server.py` | Feed checker, static-site builder (`--publish`), local preview server; `--test` for a dry run |
| `web/index.html` | The countdown page |
| `web/forecasts.json` | The current forecasts; the hosted site's state, updated by the workflow |
| `.github/workflows/publish.yml` | Scheduled feed check and GitHub Pages deploy |
| `com.elityre.ted-ai-countdown.plist` | launchd agent (RunAtLoad, KeepAlive) |
| `install.sh` | Copies the plist and restarts the agent |

## Runtime locations

- Hosted page: https://etyre.github.io/ted-ai-countdown/ (repo `Etyre/ted-ai-countdown`, public); its state is `web/forecasts.json` in the repo
- Local state: `~/Library/Application Support/TedAiCountdown/forecasts.json`
- Log: `~/Library/Logs/ted-ai-countdown.log`
- Agent: `~/Library/LaunchAgents/com.elityre.ted-ai-countdown.plist`, running the code in this folder directly
- Local preview: `http://localhost:8805`

## Common tasks

```sh
git push                                       # deploy: every push redeploys the hosted page within a minute or two
gh workflow run publish && gh run watch        # force a feed check and deploy now
gh run list --limit 5                          # recent deploys
./install.sh                                   # install or restart the local preview server
/opt/homebrew/bin/python3 server.py --test     # fetch + parse the feed, print, change nothing
tail -f ~/Library/Logs/ted-ai-countdown.log    # logs
launchctl bootout gui/$(id -u)/com.elityre.ted-ai-countdown   # stop
open http://localhost:8805                     # view
```

To set forecasts by hand, edit `medians` (and `source_date`) in `web/forecasts.json`, commit and push; the screen picks it up within 5 minutes of the deploy.

## Settings that matter

- The screen is an Insignia 32" FE Series Fire TV (ordered 2026-11-17). Setup, not yet tried on the device: open the Silk browser, go to `https://etyre.github.io/ted-ai-countdown/`, bookmark it, and set Settings > Display & Sounds > Screensaver to Never. The sleep timer has no menu setting; over adb, `settings put secure sleep_timeout 0` is reported to disable it on some models.

## Gotchas learned

- Pushing `.github/workflows/*` needs the `workflow` scope on the GitHub token: `gh auth refresh -h github.com -s workflow`. Without it the push is rejected.
- GitHub disables scheduled workflows after 60 days without a commit; the workflow commits a `keepalive` file monthly to prevent that.
- Commits in this repo use the GitHub noreply address (set in the repo's git config) because the repo is public.
- The name/month pattern also matches ordinary prose such as "The Nov 2026 points"; `NOT_NAMES` in `server.py` filters those. Run `--test` after any new update and check the names.
- The per-author forecast table in the posts is an image, so the chart caption is the only machine-readable source of all five medians.
