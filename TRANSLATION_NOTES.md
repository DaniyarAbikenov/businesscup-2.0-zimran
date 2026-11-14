# Translation notes

**Russian (ru) and Kazakh (kk) texts were written by a machine (an AI model), not by native-speaking translators or domain experts. They need review by a native speaker before real users see them.** Kazakh needs the most care. English is the source language.

## What is translated

| Part | Where | Languages |
|---|---|---|
| Interface texts (≈506) | `frontend/src/i18n/ru.ts`, `kk.ts` (English text = key) | ru, kk |
| Scenario packs (titles, questions, hints, options, steps, pitfalls, examples), roles, worries, tenures, "describe" examples | `backend/app/packs/i18n/ru.json`, `kk.json` (by id, merged over the English base) | ru, kk |
| Server texts (engine results, risk lines, documents, debriefs, emails, API errors, journal lines) | `backend/app/messages/ru.json`, `kk.json` (English template = key) | ru, kk |
| Role vocabulary (officer: orders, unit; mayor: council, residents; chief accountant; director) | `backend/app/packs/roles.json` → `vocab` | en, ru only (Kazakh falls back to the neutral wording) |
| Dates inside sentences | `app/msg.py` (`14.11.2026` for ru and kk, `Nov 14, 2026` for en) | all |

Anything missing falls back to English. Documents and results stay in the language active when they were created. AI-made scenarios stay in the language they were created in. AI prompts ask the model to write user-facing text in the user's language.

## Not translated or not reviewed

- User-typed text, scenario titles a user enters, and data from the AI are shown as written.
- Plural forms on the server are simplified (Russian uses wording that avoids "day/days"; Kazakh has no plural in these phrases).
- Russian grammatical cases in the position vocabulary only cover the main words.
- No Kazakh vocabulary table for positions yet.
- Placeholders (`{name}`) are verified by tests and `scripts/check-i18n.mjs`; the *meaning and tone* are not.

## Terms we were unsure about (please decide with a native speaker)

| English | Russian used | Kazakh used | Note |
|---|---|---|---|
| scenario | сценарий | сценарий | A kind of work moment; "exercise" is used for the three first-week items (упражнение / жаттығу). |
| follow-up | итог | қорытынды | The note about how it turned out; "result"/"outcome" is a separate word. |
| pass (the 90-day pass) | пропуск / рұқсаттама | рұқсаттама | A one-time access pass, not a subscription. |
| case | кейс | кейс | A saved scenario with numbers and decision. |
| debrief | разбор | талдау | |
| risk on your numbers | риск по вашим числам | сіздің сандарыңыз бойынша тәуекел | The phrase stresses "on your numbers, not a forecast". |
| guess / predict | догадка | болжам | "Guess" is intended; "prediction" sounds too certain. |
| tour (guided tips) | подсказки / тур | тур | |
| team lead | тимлид | тимлид | |
| unit (officer) | подразделение | бөлімше | Neutral, no military detail. |

How to add or fix a language: see the "Languages" section of the README.
