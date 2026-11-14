# Persona test report (simulated)

**Read this first.** This is a SIMULATED test run by one person (the developer) acting as six personas on the running app. It is not user research and not real users. Real users will behave differently: they will not know the words, will skip fields, will paste long messy text, and will tell us what they would actually do with the result. Nothing here shows that anyone wants or would pay for the product.

How it was run: for each persona I wrote a realistic first-week problem in their own words (English; three also in Russian), registered with that position in the running stack, used the real "Describe your scenario" endpoint (keyword path, no AI key), created the case with numbers from the text, decided, read the result, the document, the "Challenge my numbers" answer, and Home/Progress in the browser (desktop, and 375 px for layout). Backend tests (`tests/test_personas.py`) also run every position through every scenario it can see in English and Russian.

## What each persona saw

| Persona | Problem (short) | Scenario the app picked | Verdict |
|---|---|---|---|
| Team lead (promoted) | Report by Friday, data pull for a demo, VP overview, 25 free hours | Several urgent asks | Right match. Result: even the best order leaves 1 task late, document ready. Works. |
| Director | Two departments want the same budget line | Choose between options (after fix) | Before the fix the app picked "client changes requirements" (wrong). After: right scenario. The tie between the two options (70.7 vs 70.7) was shown honestly as "too close to call". |
| Project manager | Late change before release, 8 person-days, 3 days buffer | Client change request | Right and the best fit for the app. Hourly rate, buffer and client fields make sense for this person. |
| Chief accountant | Month-end close in 4 days plus an audit request | Estimate and promises (after fix) | Before the fix: "no match", defaulted to change request (irrelevant). After: right scenario. Result: asked date cannot be met; says so plainly and offers a range. |
| Officer | Three orders from three superiors, people for two | Several urgent asks | Right match and a believable result (all three late). "Challenge my numbers" said the conclusion does NOT hold: useful. Wording ("manager", "colleague") is civilian. |
| Mayor | Road, school roof or flood prevention, fixed budget | Choose between options (after fix) | Before the fix: change request (wrong). After: right. The decision calculator fits, but the banner showed the "safest" pick that is not the top-scoring one without saying so (fixed). |

Russian (team lead, chief accountant, mayor): all three matched after adding Russian keywords; before, none matched.

## Top 10 fixes, by impact

1. **Describe-your-scenario picked the wrong scenario** for 4 of 9 texts (director, chief accountant, mayor, and every Russian text), because keywords were English-only and the fallback was the first catalog entry. FIXED: Russian keywords, more English keywords, ties and "no match" now go to what is recommended for the person's position.
2. **Risk wording leaked internals** in "Challenge my numbers" ("medium (risk) risk"). FIXED.
3. **Decision banner named the lowest-risk strategy's pick as "Best by the numbers"** even when another option scored higher. FIXED: it now says "Highest score: X. Lowest risk: Y".
4. **The decided-case banner was untranslated** for the decision and estimate scenarios. FIXED.
5. **No persona-specific examples**: everybody saw the analyst/manager examples. FIXED partly: added examples for officer (orders), chief accountant (close plus audit), director (budget line), mayor (road/school/flood), in English and Russian. They still show to every position; filtering by position is not done.
6. **Vocabulary is still civilian/corporate** for officer and mayor ("manager", "my manager's manager", "colleague", "team"). Only the "client" word was neutralised. NOT FIXED: needs per-position vocabulary in the scenario text.
7. **The "Describe" placeholder example (quarterly report, VP) is the same for every position.** NOT FIXED: make it depend on the position.
8. **Dates in documents are ISO (2026-11-23)** in every language. NOT FIXED.
9. **Free plan allows 3 scenarios**: a tester who tries four scenarios hits the pricing wall during the test. Test accounts need a pass or a higher limit. NOT FIXED (a policy decision).
10. **A transient 500 on `/api/me` appeared in the browser console while the backend was reloading** during development (not reproducible afterwards). No fix needed, but a visible "Something went wrong" page appears if it happens at load time.

## What worked

- The three calculators produce sensible, explainable results for all six situations; documents are usable text.
- "Challenge my numbers" gave useful, differing answers (it said "does not hold" for the officer and the mayor, "holds" for the team lead).
- Mobile layout (375 px): no horizontal scroll on Home, case, guide, progress, journal, account, pricing, new scenario.

## Dead ends and errors

- Console errors: only the transient 500 above and Vite websocket reconnects during hot reload.
- No dead ends in the main flow once the right scenario was picked. If the intake picks the wrong scenario, the form says "Wrong scenario?" with alternatives, and that link worked.

## What only real users can show

Whether the text of each scenario makes sense in their job; whether they have the numbers the forms ask for; whether they would send the generated message; whether the risk labels change what they do; whether they come back; whether anyone would pay, and who. A realistic next step is five to eight real people from these positions doing one real case each while someone watches silently.
