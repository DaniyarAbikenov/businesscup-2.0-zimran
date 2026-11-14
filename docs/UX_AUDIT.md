# UX audit of every question (generated from the scenario packs)

Widget = what the form renders today. Flags = places where the form still mirrors a backend field or hides the meaning.

| Scenario | Step | Field id | Wording shown | Widget | Flags |
|---|---|---|---|---|---|
| client-change-request | The change | `changeTitle` | What is the change, in one line? | text box | no example/hint |
| client-change-request | The change | `changeDescription` | What exactly does the client want? | text area |  |
| client-change-request | The change | `requestedBy` | Who asked for it? | text box | no example/hint |
| client-change-request | The change | `priority` | How critical is it for the client? | word slider |  |
| client-change-request | Your project numbers | `releaseDate` | Current release date | date picker+chips | no example/hint |
| client-change-request | Your project numbers | `teamSize` | People working on the project | number box | plain number box; no example/hint |
| client-change-request | Your project numbers | `dailyRate` | Average cost per person-day (USD) | number box | unit/jargon in label; plain number box |
| client-change-request | Your project numbers | `budgetRemaining` | Budget remaining for the project (USD) | number box | unit/jargon in label; plain number box; no example/hint |
| client-change-request | Your project numbers | `changeEffortDays` | Estimated effort for the change (person-days) | number box | plain number box |
| client-change-request | Your project numbers | `bufferDays` | Schedule buffer left before the release (working days) | number box | plain number box; no example/hint |
| client-change-request | Your project numbers | `clientCoversPct` | Share of the change cost the client will pay (%) | slider+box | unit/jargon in label |
| client-change-request | Your project numbers | `delayPenaltyPerDay` | Contract penalty per day of delay (USD, optional) | number box | "(optional)" in label; unit/jargon in label; plain number box; no example/hint |
| client-change-request | Your project numbers | `partlyPct` | If you accept only part of it: share you would deliver now ( | slider+box | "(optional)" in label; no default |
| client-change-request | Assumptions | `overheadPct` | Testing and coordination overhead (%) | number box | unit/jargon in label; plain number box |
| client-change-request | Assumptions | `parallelPct` | Share of the work that can be split across the team (%) | slider+box | unit/jargon in label |
| client-change-request | Assumptions | `focusPct` | Productive share of a working day (%) | slider+box | unit/jargon in label; no example/hint |
| competing-priorities | Situation and tasks | `title` | In one line, what is going on? | text box | no example/hint |
| competing-priorities | Situation and tasks | `context` | Background (optional) | text area |  |
| competing-priorities | Situation and tasks | `tasks` | Tasks | cards (collapsible) |  |
| competing-priorities | Situation and tasks | `tasks.name` | Task | text box (in a card) | no example/hint |
| competing-priorities | Situation and tasks | `tasks.effortHours` | Hours of work | number box (in a card) | plain number box |
| competing-priorities | Situation and tasks | `tasks.deadline` | Deadline | date picker+chips (in a card) | no example/hint |
| competing-priorities | Situation and tasks | `tasks.requester` | Who asked | dropdown (in a card) | dropdown in a row; no example/hint |
| competing-priorities | Situation and tasks | `tasks.impact` | If it is late | dropdown (in a card) | dropdown in a row; no example/hint |
| competing-priorities | Situation and tasks | `tasks.note` | Note (optional) | text box (in a card) | no example/hint |
| competing-priorities | Situation and tasks | `tasks.costPerLateDay` | Cost per working day late (optional) | number box (in a card) | "(optional)" in label; plain number box |
| competing-priorities | Situation and tasks | `tasks.minEffortHours` | Hours of the minimum acceptable version (optional) | number box (in a card) | "(optional)" in label; plain number box; no default |
| competing-priorities | Your time | `hoursPerWeek` | Your working hours per week | slider+box | slider without word labels |
| competing-priorities | Your time | `committedHours` | Hours per week already taken | slider+box | slider without word labels |
| competing-priorities | Optional details | `hiddenHours` | Hours per week I may be forgetting | slider+box | slider without word labels |
| competing-priorities | Optional details | `forgotten` | What else might be missing? | text area |  |
| competing-priorities | Optional details | `extraHourCost` | Cost of one extra hour (overtime, contractor) | number box | plain number box |
| competing-priorities | Optional details | `extraHoursPerWeek` | Extra hours per week you could add by paying | slider+box | slider without word labels; no example/hint |
| asked-for-a-deadline | The task and your estimate | `title` | What are you being asked to do? | text box | no example/hint |
| asked-for-a-deadline | The task and your estimate | `context` | Background (optional) | text area |  |
| asked-for-a-deadline | The task and your estimate | `optimisticHours` | Best case (hours) | number box | plain number box |
| asked-for-a-deadline | The task and your estimate | `likelyHours` | Most likely (hours) | number box | plain number box |
| asked-for-a-deadline | The task and your estimate | `pessimisticHours` | Worst realistic case (hours) | number box | plain number box |
| asked-for-a-deadline | Time and who is asking | `hoursPerWeek` | Free hours per week for this task | slider+box | slider without word labels |
| asked-for-a-deadline | Time and who is asking | `interruptionsPct` | Lost to interruptions and context switches (%) | slider+box | unit/jargon in label |
| asked-for-a-deadline | Time and who is asking | `startDate` | When can you start? | date picker+chips | no example/hint |
| asked-for-a-deadline | Time and who is asking | `requester` | Who is asking? | segmented buttons | no example/hint |
| asked-for-a-deadline | Time and who is asking | `costOfLate` | What happens if you are late? | word slider | no example/hint |
| asked-for-a-deadline | Time and who is asking | `askedDeadline` | The date they asked for (optional) | date picker+chips | "(optional)" in label |
| asked-for-a-deadline | Optional details | `hiddenHours` | Hours per week I may be forgetting | slider+box | slider without word labels |
| asked-for-a-deadline | Optional details | `forgotten` | What else might be missing? | text area |  |
| asked-for-a-deadline | Optional details | `hourlyCost` | Cost of one extra hour (optional) | number box | "(optional)" in label; plain number box |
| asked-for-a-deadline | Optional details | `extraHoursPerWeek` | Extra hours per week you could add by paying | slider+box | slider without word labels; no example/hint |
| asked-for-a-deadline | Optional details | `goodEnoughPct` | Share of the hours a good-enough version needs (%) | slider+box | unit/jargon in label; no default |
| choose-between-options | The decision and criteria | `title` | What do you have to decide? | text box | no example/hint |
| choose-between-options | The decision and criteria | `context` | Background (optional) | text area |  |
| choose-between-options | The decision and criteria | `criteria` | Criteria | cards |  |
| choose-between-options | The decision and criteria | `criteria.name` | Criterion | text box (in a card) | no example/hint |
| choose-between-options | The decision and criteria | `criteria.weight` | Weight (1-5) | slider+box (words) (in a card) | unit/jargon in label |
| choose-between-options | Options and scores | `options` | Options | cards (collapsible) |  |
| choose-between-options | Options and scores | `options.name` | Option | text box (in a card) | no example/hint |
| choose-between-options | Options and scores | `options.note` | Note | text box (in a card) | no example/hint |
| choose-between-options | Options and scores | `options.s1` | Score for criterion 1 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no default |
| choose-between-options | Options and scores | `options.s2` | Score for criterion 2 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no example/hint; no default |
| choose-between-options | Options and scores | `options.s3` | Score for criterion 3 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no example/hint; no default |
| choose-between-options | Options and scores | `options.s4` | Score for criterion 4 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no example/hint; no default |
| choose-between-options | Options and scores | `options.s5` | Score for criterion 5 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no example/hint; no default |
| choose-between-options | Options and scores | `options.s6` | Score for criterion 6 (1-5) | slider+box (words) (in a card) | unit/jargon in label; no example/hint; no default |
| choose-between-options | The stakes | `reversibility` | How hard is it to undo? | word slider | no example/hint |
| choose-between-options | The stakes | `whoAffected` | Who is affected? | segmented buttons | no example/hint |
| choose-between-options | The stakes | `confidence` | How sure are you of your scores? | word slider |  |
| choose-between-options | The stakes | `decideBy` | Decide by (optional) | date picker+chips | "(optional)" in label; no example/hint |
