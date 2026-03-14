# Video Demo Script (6 minutes max)

Date: Sunday March 15, 03:00 UTC

This script assumes the venv is available and uses local paths under `.\_targets\`.

## Minutes 1–3 (Required)

### Step 1 — Cold Start (analyze)
Command:
```powershell
.\.venv\Scripts\python.exe .\src\cli.py analyze .\_targets\jaffle_shop
```

Expected on-screen output:
- “Running analysis on: …”
- “Starting orchestration for: …”
- “Orchestration complete. Artifacts saved in: …\.cartography”

What to show:
- Open `.\_targets\jaffle_shop\.cartography\CODEBASE.md`
- Highlight: “Architecture Overview” and “Critical Path”

### Step 2 — Lineage Query (Navigator)
Command:
```powershell
.\.venv\Scripts\python.exe .\src\cli.py query .\_targets\jaffle_shop
```

At the prompt:
```text
ask What are the upstream sources for customers? Include citations.
```

Expected on-screen output:
- A short answer + a “Citations:” block with file:line entries.

What to show:
- Open one cited file and jump to the cited line to confirm.

### Step 3 — Blast Radius
At the prompt:
```text
blast customers
```

Expected on-screen output:
- A list of impacted downstream datasets and a path for each.

What to show:
- One example path.

## Minutes 4–6 (Mastery)

### Step 4 — Day-One Brief
Open:
- `.\_targets\jaffle_shop\.cartography\onboarding_brief.md`

What to show:
- The “Day-One Questions (Semanticist)” section if the LLM is available.
- Verify 2+ answers by opening cited file:line references.

### Step 5 — Living Context Injection
Open:
- `.\_targets\jaffle_shop\.cartography\CODEBASE.md`

What to do:
1. Start a fresh AI agent session.
2. Paste the CODEBASE.md into the system prompt.
3. Ask: “Where is the business logic concentrated?”
4. Start a second fresh session without CODEBASE.md and ask the same question.

Expected outcome:
- The session with CODEBASE.md answers more specifically and faster.

### Step 6 — Self-Audit
Command:
```powershell
.\.venv\Scripts\python.exe .\src\cli.py analyze <path_to_week1_repo>
```

What to show:
- `.\.cartography\CODEBASE.md` for the Week 1 repo
- A discrepancy between your written notes and the generated output
- Explanation of why it differs (stale docs, missing module, template parsing, etc.)

## Backup Demo (if LLM is unavailable)
1. Run `query` and use deterministic commands:
   - `stats`
   - `sources 25`
   - `sinks 25`
   - `trace up <dataset> 6`
2. Show lineage graph paths and module stats without LLM calls.

