# GeM Bid Compliance Verification (prototype)

AI-assisted officer desk for GeM bid eligibility checks. All portal responses and bidder records are **dummy data**.

## Run

```bash
npm install
npm run dev
```

Open http://localhost:5173 — sign in with the pre-filled officer credentials (any values work).

## Demo path

1. Open tender `GEM/2026/B/5849201`.
2. Compare five bidders (OEM, MSME, MII fail, debarred trader, DPIIT startup).
3. Open a bidder, run **AI verification** (simulated portal sync), then Qualify / Seek clarification / Disqualify.

The final qualification decision is always recorded as the procurement officer’s.
