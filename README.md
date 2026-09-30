# Vireo Audio — First-Response SLA Monitor

## Run on a clean machine
Requires Python 3.10+ and the assignment-pack files `tickets.csv` and `agents.csv`.

1. Unzip this folder.
2. Open a terminal in the folder.
3. Create a virtual environment:
   - Windows: `py -m venv .venv` then `.\.venv\Scripts\Activate.ps1`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install: `pip install -r requirements.txt`
5. Run: `streamlit run app.py`
6. Upload `tickets.csv` and `agents.csv` in the sidebar.

## Features
Weekly breach report by week, resolving agent, historical shift; channel summary; CSV downloads; validation checks; aggregate narrative. Optional OpenAI API key adds an AI-written narrative. App works without a key.

## Rules and assumptions
- SLA: chat 15 min, voice 120 min, social 240 min, email 480 min.
- Timestamps are parsed as UTC and converted to IST.
- Legacy `csat_score=0` means no survey response and is treated as missing.
- Duplicate ticket IDs are deduplicated, preferring `helpdesk`.
- Shift is based on the historical roster row active on the resolution date.
- Week starts Monday and is based on ticket creation date in IST.
- The report includes tickets with resolution timestamps and valid historical roster matches.
- ₹350 per breach is a policy-based estimate, not verified Finance expenditure.
- Broad keywords are not sufficient to identify failed IVR records. Validate them with reliable flags or manual review.
- Passing validation checks does not prove all source data are correct.

## AI and cost disclosure
The optional OpenAI summary sends aggregate metrics only, not ticket-level data. If you do not enter an API key, the app uses a deterministic summary. In your submission, disclose the tools you actually used and the actual API cost, if any.

## Submission form
Add the original `submission-form.md` from the assignment pack and complete its exact fields. It was not present in the available files when this starter was created; do not submit an invented replacement form.
