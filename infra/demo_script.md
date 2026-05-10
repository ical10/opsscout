# OpsScout — demo recording script

Target: ≤ 5 min, 1080p, narrated by you while clicking through Streamlit. Judges score "Best of Qwen" (real Qwen3 reasoning visible) and "Best Overall" (the Airbnb-occupancy differentiator) — the script leans into both.

---

## Pre-flight (don't film this)

Run these once before hitting record. Each step has a verify line so you know you're green.

```bash
# 1. autossh tunnel up (background, persistent)
autossh -M 0 -f -N -o "ServerAliveInterval 30" -o "ExitOnForwardFailure yes" \
  -L 8000:localhost:8000 <user>@<amd-host>
curl -s http://localhost:8000/v1/models | jq -r '.data[].id'
# expect: Qwen/Qwen3-30B-A3B-Instruct-2507

# 2. .env confirms live providers
grep -E "DEMO_MODE|DATABASE_URL|AMD_VLLM_BASE_URL" .env
# expect: DEMO_MODE=false, DATABASE_URL=postgresql:///opsscout, AMD_VLLM_BASE_URL=http://localhost:8000/v1

# 3. Pre-populate ONE pending proposal per business (LLM is slow; doing it on-camera burns 2 min of dead air)
source .venv/bin/activate
python - <<'PY'
import os, psycopg
from graph import run_for_business
from db import save_proposal
for bid in ("nusa_adventures", "kopi_nusa_cafe"):
    print(f"→ pre-populating {bid}...")
    p = run_for_business(bid)
    with psycopg.connect(os.environ["DATABASE_URL"]) as c:
        save_proposal(c, p)
    print(f"  saved {p.proposal_id} priority={p.priority}")
PY

# 4. Streamlit up
streamlit run main.py --server.headless true --server.port 8501
# open http://localhost:8501 in a clean browser window, full-screen
```

Sanity-check the dashboard renders cards for both businesses. If anything's blank, do not record; debug first.

---

## Script (start recording now)

**Total budget: ~4:45.** Beats are timed loosely — the script reads in roughly that long if you don't rush.

### Beat 1 · The hook (0:00 – 0:30)

> *On screen:* Connect page, Nusa Adventures highlighted in the radio.

"I'm a tour operator in Bali. I run surf classes, rafting trips, and treks. My customers don't book a year ahead — they book the night before. So when a storm rolls in, or a yoga festival lands across the bay, or every Airbnb in Seminyak suddenly costs three times normal — I have hours, not days, to decide whether to add staff, order more wetsuits, or cancel surf and pivot guests to trekking. I usually guess. OpsScout watches for me."

> *Click:* "Nusa Adventures" radio → flip to **Dashboard** in the sidebar.

### Beat 2 · The proposal renders (0:30 – 2:30)

> *On screen:* Dashboard with the pre-populated card. Top metrics visible: Priority HIGH · Demand 1.8× · Occupancy HIGH · Confidence 80%+.

"This is what OpsScout produced ninety seconds ago. Five specialist agents — Forecaster, Demand Modeler, Logistics, Communications, Operations Manager — running on Qwen3-30B-A3B-Instruct served by vLLM on an AMD MI300X."

> *Hover the priority strip.*

"Demand for this Saturday is going to be one-point-eight times normal. The reason is the Airbnb signal — and that's the part I want to point at."

> *Click "Read the full brief" expander.*

"Listings are scarce, prices have spiked. Tourists are already in town and they are stuck. A storm doesn't send them home, it sends them looking for something to do indoors. That's not a moment to scale down — that's a moment to add cycling guides and pre-order wetsuits."

> *Scroll to the action cards grid.*

"Three concrete actions. Order 34 wetsuits — we have eight, we need 42 for safe surf and rafting capacity. Hire or reassign nine cycling staff. Hire seven more for the trekking trail. Each card has the supplier, the cost estimate. Total spend on the call is roughly nine thousand US dollars."

> *Scroll to the communications card.*

"And here's the email draft to my operations team — channel, urgency, body. Notice the bracket — Pending Owner Approval. Nothing is sent. Nothing is ordered. Nothing is staffed. Until I say so."

### Beat 3 · The architecture, while you scroll (2:30 – 3:30)

> *Open a new tab/window:* `docker logs -f vllm-server` OR the terminal showing the autossh tunnel + curl on `/v1/models`. Just visual proof Qwen3 is the engine.

"Underneath, this is a LangGraph state machine. Six nodes — Forecaster, Demand Modeler, Logistics + Comms, Operations Manager, await_approval, execute. The graph runs to await_approval and stops. PostgresSaver persists the checkpoint to disk. The agents are done, but nothing has fired."

> *Switch back to the dashboard.*

"The data sources are live. Open-Meteo for the seven-day weather forecast. PredictHQ for events within ten kilometers. And the @openbnb MCP server — open source, the same Airbnb integration AMD's own ROCm developer hub uses in their Qwen agent tutorial — for accommodation supply and price. All three responses are cached locally so demo runs are fast."

### Beat 4 · Approve and resume (3:30 – 4:00)

> *Click ✅ Approve.*

"When I approve, two things happen. The proposal status flips to approved in postgres. And the same checkpoint thread resumes — the graph picks up at execute. In production, execute would dispatch to a Calendar MCP, a Gmail MCP, a Slack MCP. For the hackathon scope, it logs the dispatched action."

> *Wait for the rerun. (Approve currently kicks off another full crew run — about a minute. Either edit this beat in post, or let it spin and narrate the next beat over the wait.)*

> *Click **History** in the sidebar.*

"There's the proposal, marked approved."

### Beat 5 · The tier-2 contrast (4:00 – 4:30)

> *Click **Connect** → **Kopi Nusa Café** → **Dashboard**.*

"Same agents, different business — a café in Ubud. Tier 2. The system knows tour operators can ramp staff in 48 hours; cafés can't, so the staffing actions list is empty by design. The actions are inventory and comms only — order more milk, more pastries, message regulars about extended hours. Same five-agent crew, same Qwen3 model, different proposal shape because the business profile is different."

### Beat 6 · The close (4:30 – 4:50)

> *Show: README open in a side panel, or the GitHub repo, or just back to the dashboard.*

"Built solo over seven days. Open source. Running on AMD MI300X. The whole point is that small businesses with no data scientist on staff get the same kind of demand intelligence that hotel chains and airlines pay six-figure annual licenses for — gated behind one-click approval so the agent never goes rogue."

> *End on the proposal card, fade out.*

"OpsScout. Submitted to the AMD-times-lablab hackathon. Best Overall. Best of Qwen."

---

## Things to NOT do on camera

- Don't click Run Forecast (no such button yet — adding that is Slice 5 polish).
- Don't click Approve and then sit for 60s of dead air. Either trim in post or talk over Beat 5 while it spins.
- Don't open the Trace page — `react_trace` isn't populated yet (also Slice 5).
- Don't show the terminal where streamlit is running unless it's clean of stack traces.
- Don't show `.env` (PHQ_TOKEN is in plaintext).

## Recovery moves if something breaks live

- **vLLM 500/timeout** — Qwen3 occasionally over-thinks. Refresh the dashboard; the proposal you pre-populated is still in postgres.
- **@openbnb returns 0 listings** — switch the narration to "the model can't see Airbnb supply right now, here's the fallback occupancy_pressure derived from the price-only signal" and continue.
- **Tunnel drops mid-record** — autossh restarts in ~30s. If the dashboard is already showing the proposal, the live LLM isn't needed for the rest of the recording. Don't restart the take.
- **Streamlit hangs on Approve** — kill the tab, reopen `localhost:8501`, the redirect lands you on Dashboard with status updated.
