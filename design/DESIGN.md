# RoleShift design system ("Ledger")

Follow this file for every UI change. If a rule here blocks you, change the rule in the same PR.

## Where it comes from

We borrowed principles, not looks.

| Source | What we took |
|---|---|
| **Linear** (UI redesign, 2024) | Theme from few inputs (base, accent, contrast) instead of dozens of variables. Perceptually even lightness. Keep chrome neutral so content stands out. A display face for headings, a plain one for UI. Reduce visual noise, raise density where users scan. |
| **Vercel Geist** | Color scales with fixed roles per step (100 background, 200 hover, 300 active, 400 border, 500 hover border, 600 active border, 700 solid, 800 hover solid, 900 secondary text, 1000 primary text). Gray for text, fills and borders by default. Draw each border once. Shadows only when something floats, and translucent. |
| **GOV.UK design principles** | "Do the hard work to make it simple." Accessible beats elegant. Plain words. "Be consistent, not uniform." |

Our own idea: RoleShift is a **ledger for decisions**. Users compare real numbers and sign a document. So the look is warm paper, ink text, hairline rules, tabular numerals, one calm accent. It should feel like a careful colleague's notebook, not an AI chat toy.

## Color

Neutrals are warm "paper and ink". One accent (ink teal). Status colors are used only for risk and validation.

Light theme tokens (`frontend/src/styles/tokens.css` is the source of truth):

| Token | Value | Role |
|---|---|---|
| `--n-100` | `#FAF8F4` | App background |
| `--surface` | `#FFFFFF` | Cards, inputs |
| `--n-200` | `#F3F0EA` | Hover, subtle fill |
| `--n-300` | `#EAE6DE` | Active fill |
| `--n-400` | `#DDD8CD` | Default border |
| `--n-500` | `#CBC5B8` | Hover border |
| `--n-800` | `#6B6559` | Muted text (5:1 on background) |
| `--n-900` | `#4A463E` | Secondary text |
| `--n-1000` | `#1D1B17` | Primary text (15:1) |
| `--accent-700` | `#0F6B5C` | Primary button, links (white text 6:1) |
| `--accent-800` | `#0B5A4D` | Hover |
| `--accent-100` | `#E6F2EF` | Selected row tint |
| `--ok` / `--warn` / `--bad` | text `#1B6B3A` / `#7A4B00` / `#A3281D` on `#E4F3E8` / `#FBF0D5` / `#FBE4E0` | Low, medium, high risk; errors |

Dark theme is a real redesign of the same roles (`prefers-color-scheme`), not an inversion: background `#14130F`, surface `#1C1B16`, border `#2E2C25`, text `#F1EEE7`, accent `#3DB59D`.

Rules:
- Gray carries text, borders and fills. The accent appears on at most one primary action per view, links and the selected state.
- Never use color alone: risk is always text ("High risk") plus color.
- Minimum contrast 4.5:1 for text, 3:1 for borders of inputs and focus rings.

## Typography

- Headings: **Fraunces** (variable serif), weight 500, tight tracking. Gives the product a voice.
- UI and body: **Inter** variable. Numbers use `font-variant-numeric: tabular-nums` everywhere money or dates appear.
- Documents and code: system monospace.

Scale (px / line-height): caption 12/16 (uppercase eyebrow, +0.04em), small 14/20, body 16/24, lead 18/28, h3 20/28, h2 26/32, h1 36/42. Body copy never below 14. Line length for prose at most 68 characters.

## Spacing, shape, elevation

- 4px base: 4, 8, 12, 16, 24, 32, 48, 64. Use the tokens `--s-1` to `--s-8`.
- Radius: 6px controls, 8px panels. No pill-shaped buttons. Badges are 4px.
- Panels are flat: 1px `--n-400` border on `--surface`, no shadow. Draw each border once (no border plus ring plus shadow).
- Only floating things (toast, menus) get a shadow: `0 8px 24px rgb(29 27 23 / 0.14)`.
- Page width: 1040px max for app pages, 680px for forms and reading.
- Motion: 120ms ease-out on color and border only. Respect `prefers-reduced-motion`.

## Layout

- Left aligned. No centered hero blocks.
- Page header: eyebrow (caption, uppercase, muted), serif h1, one line of muted lead text.
- Compare options in a **ledger table** (rows are measures, columns are options), not three identical cards. On narrow screens it becomes stacked option blocks.
- Forms: one column, label above, help text under the label, error under the field in text plus icon-free `--bad` color.

## Components

| Component | Rules |
|---|---|
| Button | Primary (accent solid), Secondary (border only), Quiet (text). Height 40px, 44px touch target on mobile. One primary per view. Disabled shows `aria-busy` and keeps its label. |
| Field | Label, optional help, control, error. Error sets `aria-invalid` and `aria-describedby`. |
| Panel | Surface with 1px border, 24px padding. Title is h2 serif. |
| Badge | 4px radius, uppercase 12px, text and tint from the status triple. |
| Banner | Left 3px rule in status color, tint background. Used for the privacy warning and results. |
| Ledger | Hairline rows, right-aligned tabular numbers, selected column gets `--accent-100` tint. |
| Stat | Large serif number over a small label. No icons, no cards-in-cards. |
| Toast | The only shadowed element. Disappears after 2.5s and uses `role="status"`. |

## Content

Sentence case. US English. Plain words ("cost", not "financial impact"). Say what happens next on every button ("Save decision and create Change Request"). Self-reported results are labeled as such. No exclamation marks, no emoji, no "AI magic" wording.

## Avoid

- Purple or indigo gradients, glow blobs, glassmorphism.
- Default Tailwind or shadcn look: slate/zinc plus blue-600, rounded-2xl everywhere, shadow on every card.
- Rows of three identical icon cards.
- Sparkle icons for AI. AI output is labeled "AI draft" in plain text and sits behind a button.
- Opaque or stacked shadows, overlapping alpha borders.
- Color-only status, placeholder-only labels, text smaller than 12px.
- Inventing new colors or sizes: add a token here first.
