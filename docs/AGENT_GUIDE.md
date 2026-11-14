# Guide for an independent agent: how to use and test RoleShift

Read this first. It tells you what the product is, how to get in, what to do, what the correct answers look like, and how to report. It is written for an AI agent with a browser (and optionally an HTTP client), and also works for a human tester.

- **Site:** https://businesscup-2-0-zimran.vercel.app (English only, desktop browser, window at least 1000 px wide).
- **What it is:** a judgement trainer for people newly in a responsible role. The person enters their own numbers, makes a guess, sees a calculation done by code (not by an AI), decides, gets a ready document, and later records the outcome.
- **What it is not:** a forecast, advice, or an AI assistant. The numbers must be deterministic: the same inputs always give the same outputs.

## 0. Ground rules

1. **Use only made-up or rounded numbers and generic names.** Never enter real employer, client, or personal data. Never enter a real password or a real card (the checkout is a test and takes no payment).
2. **Use the demo account.** Every press of "Try the demo" creates a separate temporary account with sample data. Limit: 10 demo accounts per hour per address, accounts are deleted after 7 days. If you get "Too many demo accounts", wait or register a throwaway account (any `name@example.com`, a long made-up password).
3. **The first request after a quiet period can take several seconds** (serverless cold start). Wait up to 15 seconds before calling it a failure; then retry once and report it.
4. Do not try to break security, scan the site, or flood it. Report anything odd instead.
5. Be honest: report what you actually saw. If you did not verify something, say "not verified".

## 1. Get in

1. Open the site. The sign-in page has a **Try the demo** button. Press it. You land on Home as a demo "Project / delivery manager (IT)" with sample cases.
2. Guided tips may pop up (a small dialog with Next / Skip tour). Press **Skip tour**, or tick "Do not show tours again".
3. Navigation (top bar): Home, My cases, Progress, How it works, Account, ? (replays the tip for this page), Sign out. Footer: How it works, Compare with a chat assistant, Account and data, Pricing.

Useful addresses (all relative to the site):

| Address | What |
|---|---|
| `/` | Home: three first-week exercises, "Describe your scenario", sample cases |
| `/new/client-change-request` | Client changes requirements late (accept / part / defer / decline) |
| `/new/competing-priorities` | Several urgent asks, not enough time |
| `/new/asked-for-a-deadline` | Someone asks "by when?" (three-point estimate) |
| `/new/choose-between-options` | Choose between options with weighted criteria |
| `/case/<id>` | A case: result, decision, document, debrief, follow-up |
| `/progress`, `/journal`, `/documents`, `/account`, `/pricing`, `/guide`, `/compare` | Other pages |
| `/api/health` | `{"ok": true}`, touches no database |
| `/health` | `{"ok": true}`, checks database and Redis |

## 2. The core flow (do this for each of the four scenarios)

1. **Choose a scenario** on Home (press Start) or open its `/new/...` address.
2. **Fill in the form** (2 to 4 steps plus a Review, with a progress bar and "Step n of N"):
   - **Fill with an example** (a link next to the step counter, first step) loads a ready example with made-up numbers; storyline cards near the top do the same with a choice of three. **Start over** clears the form (it asks to confirm).
   - Press **Next** on each step. A step will not continue while a required field is empty or out of range: you should see highlighted fields and a message. Test this once with an empty form.
   - Ratings and levels are **sliders with a word under them** (for example "How critical is this for the client?" from Nice to have to Must have). Small-range quantities are a slider with a number box and unit; other quantities are a number with − and + buttons and the unit next to it. Short choices are buttons. Dates have quick buttons (Today, Tomorrow, This Friday, In 1 week, In 2 weeks). Tasks, options and criteria are cards (Edit / Collapse / Up / Down / Remove / Add).
   - Optional inputs are behind a collapsed **Add more detail** section in each step (and inside each task or option card).
   - The **side panel "Where this stands"** (right of the form) updates after a short pause while you type: it lists what is still needed, then the numbers that follow from your input. For scenarios with a guess step it keeps the answer hidden ("Your guess comes first") unless you press "Show the live result instead"; the change request shows its answer at once.
   - Reload the page or press the browser Back button in the middle of the form: your values and the step come back (kept in the tab only).
   - The last step is **Review**: it lists what you entered by step with an **Edit** link for each, asks "How confident do you feel", a tick box ("I did not enter confidential ... information") and the **Compare my options** button. The tick box is required.
3. **Guess first.** For the priorities, deadline and options scenarios a "What do you think the numbers will say?" screen appears. Either answer (and press "Save my guess and show the numbers") or press "Skip, show me the numbers". The change-request scenario has no guess step.
4. **Read the result** (page `/case/<id>`, step 2 "Compare"): a one-sentence answer at the top, one column per option, a risk label per option with a "Why this label" link that explains the points and has a "What counted in this label" block (time / money / quality), a "How was this calculated?" section, a **Challenge my numbers** button, and (when optional money or scope inputs exist) a table "Time, money, quality ...".
5. **Decide.** Click **Choose** on one option, write a reason, press "Save decision and create ...". A ready document appears (editable, Copy, Download .md) and a debrief.
6. **Follow up.** Pick when to be asked "how did it go"; optionally add a reflection and later report the outcome. Then open **Progress** (days of 90, decisions, how often your guess matched the numbers).

## 3. Correct answers you can check

The calculation is fixed. These checks do not depend on today's date. Amounts in the table are shown without thousands separators (for example 18900) and in USD; the result columns and the document may show 32,700 with a separator.

**Change request** (`/new/client-change-request`). Enter: priority Important; people 6; cost of one person-day 600; budget left 40000; work in the change 10 person-days; spare days 2; client pays 0%; penalty 0; the assumptions in "Add more detail" unchanged (extra for testing 25%, shareable work 60%, productive day 70%); release date a weekday at least 3 weeks away; in "Add more detail" "how much would you deliver now" 60.
- Accept as is: effort with overhead 12.5 person-days, added working time 9 days, release slips 7 working days, labour 7,500, extended run 25,200, **extra cost 32,700**, budget left afterwards **7,300**, risk label high.
- Table row "Accept part of it" (60%): slips **4** working days, money **18,900**, "60% delivered now", quality risk **high (40% cut)** (cut up to 15% is low, up to 35% medium, above that high).
- "Defer to the next release": money **8,100** (600 to re-plan now plus 7,500 later). "Decline": money 0.
- Clear the "how much would you deliver now" box: the "Accept part of it" row must say "not set", not a number.
- On the result page, in **What if?**, drag "How much work is the change?" up: the "If accepted" numbers in the right column must change and be highlighted, and the saved column must stay until you press Save these numbers.

**Competing priorities** (`/new/competing-priorities`). Three tasks of 14, 6 and 8 hours, deadlines within the next working week; hours per week 40, already taken 25.
- Total hours **28**, free hours per day **3.0**.
- On step 1 open "Add more detail" inside the 14-hour task card: a minimum version of 8 hours and a cost per late day of 100. On step 2 open "Add more detail": cost of an extra hour 30, extra hours per week 10. The table must then show "Cut scope on the late tasks" with **21% cut** and quality risk **medium** (6 of 28 hours), plus rows for paying for extra hours and moving a deadline.
- The ordering by earliest deadline must match the dates you entered. Whichever option is marked "Least damage on these numbers" must be the one with the smallest weighted lateness.

**Asked for a deadline** (`/new/asked-for-a-deadline`). Estimates: best 8, likely 16, worst 40 hours; 20 free hours a week; interruptions 20%.
- The "safe date" must be later than the "likely" date, and the optimistic date earliest. Chances shown rise with later dates.
- In "Add more detail" on step 2, with "share a good-enough version needs" 70% and an extra-hour price entered, the table shows "Deliver the good-enough version" (**30% cut, quality risk medium**) and "Pay to speed up".

**Choose between options** (`/new/choose-between-options`). The form starts with the criteria Time, Cost and Quality (weight 3 each).
- The winner must be the option with the highest weighted score = sum(weight x score) / (sum of weights x 5) x 100. Check one by hand.

**Determinism.** Create the same case twice (same inputs). Every number in the two results must be identical.

## 4. Other things worth testing

- **Challenge my numbers**: shows how the conclusion holds if numbers get worse (estimates 20% higher, an extra hour 20% dearer, cut 10 points deeper).
- **Describe your scenario** on Home: type a few sentences; it should pick a scenario and copy your text into the form. Check that it never invents numbers.
- **Guess accuracy**: after guessing, the result page shows your guess next to the numbers; Progress counts agreement. Fewer than 3 guesses must not show a trend.
- **Documents**: edit the generated document, Save changes, reload, confirm the edit stays. Try Copy and Download .md.
- **Account**: Account and data (export, delete). Do not delete the demo account unless you finish the whole test.
- **Pricing and test checkout** (`/pricing`): the pass is **$19**, one-time, no real payment. After 3 cases of your own a free account is asked to buy the pass; the demo account may differ.
- **Compare page** (`/compare`): must say honestly what a chat assistant does better. Flag any claim you think is unsupported.
- **Back and refresh**: refresh in the middle of the form (entries and step should come back), use the browser Back button, open a case in a second tab (a new tab starts with an empty form).

## 5. API route (optional, for exact checks)

Session is a cookie; every write needs `Content-Type: application/json`.

```bash
J='Content-Type: application/json'; S=https://businesscup-2-0-zimran.vercel.app
curl -s -c jar -X POST $S/api/auth/demo -H "$J" -d '{}'
curl -s -b jar $S/api/me | head -c 300
curl -s -b jar -X POST $S/api/cases -H "$J" -d '{
 "situationId":"client-change-request","privacyAck":true,"confidenceBefore":3,
 "inputs":{"changeTitle":"Export","changeDescription":"","requestedBy":"Jo","priority":"important",
  "releaseDate":"2026-12-14","teamSize":6,"dailyRate":600,"budgetRemaining":40000,"changeEffortDays":10,
  "bufferDays":2,"clientCoversPct":0,"delayPenaltyPerDay":0,"overheadPct":25,"parallelPct":60,"focusPct":70,"partlyPct":60}}'
```

The reply holds `case.result.options` (accept / defer / decline with `extraCost`, `slipWorkdays`, `riskLevel`, `labelBasis`) and `case.result.levers` (the table). Change the release date to a weekday at least 3 weeks away. Then `POST /api/cases/<id>/decision` with `{"option":"defer","rationale":"..."}` returns the document. Other useful calls: `GET /api/cases/<id>`, `GET /api/cases/<id>/challenge`, `GET /api/progress`, `GET /api/journal`, `GET /api/documents`.

Wrong input must fail cleanly: for example `teamSize: 0` returns HTTP 400 with `fields`, never HTTP 500.

## 6. How to report

Send one report with these parts. Keep it factual.

1. **What you did**: scenarios completed end to end (yes / no for each of the four), pages visited.
2. **Checks**: for each item in section 3, "matched" or the exact number you saw.
3. **Problems**: for each, the page, the steps, what you expected, what happened, how serious (blocks the task / confusing / cosmetic), and a screenshot or the exact text.
4. **Where you got stuck or hesitated**, and for how long, even if it worked.
5. **Unclear words, fields or numbers.**
6. **Would you use this on a real decision? Yes / no / only if ...**, and what is missing.
7. **Not verified**: list anything you could not check (for example email reminders: the site sends no email unless a mail service is connected).

## 7. Known limits (do not report these as new)

- English only; desktop layout only (phones open the pages but forms are long).
- Email reminders are not sent from the test site (no mail service is connected); the "send now" button only logs.
- The first request after idle is slow; the data of demo accounts can be removed at any time.
- Risk labels, the "quality" rating and the guess score are rules of thumb on your own inputs, not measurements of real-life results. Money and quality do not change a risk label except where "What counted in this label" says so.
- The unsaved form is kept only in the same browser tab (session storage); a new tab or a closed tab starts empty.
- The time, money and quality table appears only when the optional money or scope inputs are filled (for the change request, the "how much would you deliver now" box).
