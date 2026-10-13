---
name: Job search dashboard, the standard design
description: The familiar job board played straight, at the polish of Airbnb and LinkedIn Jobs, for one reader checking a ranked list each morning.
colors:
  page: "#f3f2ef"
  surface: "#ffffff"
  surface-hover: "#f7f6f4"
  ink: "#1d2226"
  ink-2: "#5e6166"
  ink-3: "#8a8d91"
  line: "#e3e2de"
  line-strong: "#cfcdc8"
  accent: "#2563eb"
  accent-hover: "#1d4ed8"
  accent-soft: "#e8effd"
  on-accent: "#ffffff"
  new: "#0b7a53"
  new-soft: "#e3f3ec"
  warn: "#8a4b08"
  warn-soft: "#fbf0dc"
  danger: "#b42318"
  danger-soft: "#fdecea"
typography:
  wordmark:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.015em"
  score:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "1.75rem"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "-0.015em"
    fontFeature: "tnum"
  headline:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  title:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "1.0625rem"
    fontWeight: 650
    lineHeight: 1.3
    letterSpacing: "-0.005em"
  section:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "1.0625rem"
    fontWeight: 700
    lineHeight: 1.5
  body:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
  button:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.5
  label:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.5
  meta:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  badge:
    fontFamily: "Newsreader Variable, ui-serif, Georgia, serif"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.5
  mono:
    fontFamily: "ui-monospace, SF Mono, Menlo, Consolas, monospace"
    fontSize: "0.8125rem"
    fontWeight: 400
rounded:
  tile: "8px"
  inner: "10px"
  card: "12px"
  pill: "999px"
spacing:
  gutter: "clamp(16px, 2.6vw, 48px)"
  grid-gap: "20px"
  grid-gap-phone: "12px"
  workspace-gap: "24px"
  card-pad: "18px"
  card-pad-280: "20px"
  card-pad-340: "22px"
  panel-pad: "28px"
  inset-block: "14px"
  inset-inline: "16px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.button}"
    rounded: "{rounded.pill}"
    padding: "0 18px"
    height: "40px"
  button-secondary-hover:
    backgroundColor: "{colors.surface-hover}"
  button-small:
    typography: "{typography.meta}"
    rounded: "{rounded.pill}"
    padding: "0 12px"
    height: "32px"
  icon-button:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.pill}"
    size: "36px"
  icon-button-hover:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink}"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "36px"
  chip-new-pressed:
    backgroundColor: "{colors.new-soft}"
    textColor: "{colors.new}"
  lane-chip-pressed:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.surface}"
  segmented:
    backgroundColor: "{colors.page}"
    rounded: "{rounded.pill}"
    padding: "3px"
  segment:
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "0 14px"
    height: "30px"
  segment-chosen:
    textColor: "{colors.ink}"
  segmented-thumb:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.pill}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.card}"
    padding: "18px 18px 16px"
  badge:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink-2}"
    typography: "{typography.badge}"
    rounded: "{rounded.pill}"
    padding: "0 8px"
    height: "22px"
  badge-new:
    backgroundColor: "{colors.new-soft}"
    textColor: "{colors.new}"
  badge-closed:
    backgroundColor: "{colors.danger-soft}"
    textColor: "{colors.danger}"
  lane-tag:
    backgroundColor: "{colors.page}"
    textColor: "{colors.ink-2}"
    typography: "{typography.badge}"
    rounded: "{rounded.pill}"
    padding: "3px 10px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.card}"
    padding: "0 28px 32px"
    width: "clamp(380px, 34vw, 560px)"
  fact-block:
    backgroundColor: "{colors.page}"
    rounded: "{rounded.inner}"
    padding: "14px 16px"
  notice:
    backgroundColor: "{colors.warn-soft}"
    rounded: "{rounded.inner}"
    padding: "14px 16px"
---

# Design System: Job search dashboard, the standard design

Scope: this file documents the second dashboard design only, the standard design in `dashboard/standard/` (served by `dashboard.serve`, where it is the default, reading `/api/v2/`). The first design is an earlier page design that is not in this repository, and none of these tokens or rules apply to it.

## Overview

**Creative North Star: "The Job Board You Already Know"**

The category standard, played straight: a calm grid of job cards on a warm page, with the chosen job's details in a panel beside the grid. The quality bar is Airbnb and LinkedIn Jobs. The system gets its polish from restraint, not novelty. It has one family, hairline white cards and pill controls, and every colour does a single job: blue for the primary action, the selected card and focus, green for New, ink for everything current or starred.

Density stays moderate on purpose. The product principle is less on screen at once, so a card carries score, title, employer, place, one lane and whole lines of summary, and the rest waits in the panel. Depth is quiet. Cards sit on a 1px ring at rest, and a soft shadow shows only on hover, on selection and on the panel. Motion has one signature moment: choosing a card slides the panel in and glides every card to its place in the narrowed grid. The only other movement is a slider's white thumb gliding to the chosen option.

Three things would feel wrong here: cold and corporate, crowded like an admin tool, plain to the point of dull. The warm page and the moving panel answer the first and third. The capped panel width and the clamped summary answer the second.

**Key Characteristics:**
- Warm grey page, white cards with a 12px radius and a hairline ring.
- Blue in three roles only, green for New only, ink for current and starred.
- Newsreader throughout, with tabular figures on every number that is compared.
- Cards that fill the row and gain a column when there is room, each row as tall as its longest card.
- The chosen job opens in a sticky panel beside the grid, never over it on a laptop.
- Light or dark follows the computer, a button in the header flips it, and every role is kept in both.

## Colors

Warm neutrals with two saturated voices, each kept to its role.

Light values are in the frontmatter. Dark mode swaps the neutrals and lightens the voices but keeps every role. It is `data-theme="dark"` on the root, which a short script in `index.html` sets before the page draws: from the choice the header's theme button saved, or from `prefers-color-scheme` when none is saved. The dark values are page #141618, surface #1e2124, surface-hover #25292d, ink #eceef0, ink-2 #a9adb3, ink-3 #7d8288, line #2f3338, line-strong #454b52, accent #7aa7ff, accent-hover #9dbeff, on-accent #0d1b33 and new #52c794. Warn is #f0b35c and danger is #ff8a7a. Each soft tint becomes its voice at 12 to 14% alpha.

### Primary
- **Clear Action Blue** (accent): fills the one primary button (Write brief) and draws the 2px ring on the selected card, the 2px focus outline on every control, the text caret and the text selection wash (accent-soft). Its hover step is accent-hover. It is used for nothing else.

### Secondary
- **New Green** (new, with new-soft): the dot and pressed state of the New chip, the New badge, and the "n new" count on a lane chip. It is used for nothing else, including success, good scores or confirmation.

### Tertiary
- **Status Amber and Red** (warn, warn-soft, danger, danger-soft): amber for the stale-ranking notice, and for the notice that names a job site whose reader has stopped finding ad text. Red for error notices, a failed brief and the Closed badge. They appear only where something needs attention.
### Neutral
- **Warm Page** (page): the canvas behind the grid, plus recessed wells inside white surfaces: badges, lane tags, the fact block, the segmented track and the icon-button hover.
- **Card White** (surface): cards, the header, the panel, every resting button and chip, and the slider thumb.
- **Hover White** (surface-hover): the secondary button hover and its pressed state (Saved).
- **Ink** (ink): text, the chosen option in a slider, the pressed lane chip, the filled star, and hover borders on chips and buttons.
- **Secondary Ink** (ink-2): meta text, summaries, counts, labels and a slider's other options.
- **Faint Ink** (ink-3): the run-line separators only.
- **Hairline** (line) and **Strong Hairline** (line-strong): line draws the card rings, header and toolbar rules, the card head and footer rules and panel section rules. line-strong draws resting chip and button borders and the scrollbar thumb.

### Named Rules
**The Three Jobs of Blue Rule.** Blue marks the primary action, the selected card and focus. Nothing else. The current view, the pressed lane chip and a starred job are ink.

**The One Green Rule.** Green means New and nothing else.

**The Same Roles After Dark Rule.** Dark mode swaps values, never roles. Anything added must work under both schemes with the same role mapping.

## Typography

**Display Font:** Newsreader Variable (with ui-serif, Georgia, serif)
**Body Font:** Newsreader Variable (same stack)
**Label/Mono Font:** ui-monospace, SF Mono, Menlo, Consolas, for file paths and commands only

**Character:** One serif made for reading news on screen, at several weights, including a variable 650 for card titles. Its optical size axis draws the 12px badges sturdier and the score and headlines finer, so one family covers every size. The font is self-hosted from `@fontsource-variable/newsreader`'s opsz files, so the optical size axis comes with the weights and the page makes no outside request for type. `fonts.css` declares the faces itself rather than importing the package's `opsz.css`, to override the vertical metrics: ascent 85.75% and descent 14.25%, so capital height (0.715em) is centred in every line. With the font's own 73.5% and 26.5%, text sits 2 to 3px high in every button, chip and slider. The capitals are what is centred, not a point between capitals and lowercase. The sum is still 1em, so no line box changes size.

Newsreader is used over Source Serif 4 and Literata. Checked in the font files: it has a `tnum` feature and lining figures by default. Fraunces, Playfair Display, Instrument Serif and Georgia fail that check, and Georgia and Playfair also drop 3, 4, 7 and 9 below the line.

### Hierarchy
- **Score** (700, 1.75rem, rising to 2rem in cards 340px and wider, line-height 1): the number that leads each card's head band.
- **Headline** (700, 1.5rem, 1.25, balanced wrap): the job title in the panel.
- **Wordmark** (700, 1.75rem, 1.1, and 1.5rem on a phone): "jobFinder" beside the 32px logo in the header.
- **Title** (650, 1.0625rem, then 1.1875rem at 280px and 1.3125rem at 340px card width): the card's job title, clamped at 3 lines.
- **Section** (700, 1.0625rem): panel section headings, and 1.125rem for empty-state titles.
- **Body** (400, 0.9375rem, 1.5): base text. Panel reasons and summary are capped at 70ch. Card summaries run 0.875rem at 1.45, stepping to 0.9375rem and then 1rem at 1.55.
- **Button** (600, 0.9375rem): buttons.
- **Label** (600, 0.875rem): chips and slider options. Lane chips use 500 with a 700 code.
- **Meta** (400, 0.8125rem): the run line, the card footer, the count at the end of the list and the small button.
- **Badge** (600, 0.75rem): badges. Lane tags use 500 with a 700 code, and fact labels use 500.

### Named Rules
**The Tabular Figures Rule.** Every number meant for comparison uses `font-variant-numeric: tabular-nums`: scores, want and reach values, counts in chips, lanes and the Saved option, the run line with the list's count, the rank, and the count at the end of the list.

**The One Family Rule.** Newsreader carries every role. Monospace appears only for a path or command someone has to copy.

## Layout

The page has a sticky white header and a warm workspace under it. Both use one horizontal gutter, `clamp(16px, 2.6vw, 48px)`.

**Header.** The first row is the logo and "jobFinder", with the theme button at its end, and the run line under them: the last run's counts, "24 job listings added · 4 removed · 216 open", where the noun says the run's intake is listings rather than new jobs for the reader, then the count of the list below, worded for the view. It reads "44 jobs match your profile", "3 doctoral calls in Stockholm match your profile", "2 saved jobs in Stockholm", "3 applied jobs", "2 removed jobs" or, in Rejected, "29 jobs matched no lane". Under it, in the same sticky header, sits the toolbar: two view sliders on the left, Top picks, By lane, PhD and Rejected, then Saved, Applied and Removed, and the New chip, the All / Stockholm / Outside slider and the All sites / Platsbanken / Other sites slider on the right, on every view. The source slider is there for the ads from other job sites, and the list's count names it: "4 jobs from other sites match your profile". Rejected is a list like the others, with the same grid, cards and panel. In By lane a third row of lane chips follows. The views are split into the two sliders, the lists the system ranks and then the user's own; one view is chosen at a time, so the other slider shows no thumb. App.tsx writes the header's height to `--header-h` with a ResizeObserver so the panel can stick beneath it.

**Lane row.** It scrolls horizontally with its scrollbar hidden. When there is more on one side, an arrow button sits at that edge. The row is masked so chips are fully transparent for the first 72px under the arrow, reach 12% at 92px and are solid by 140px, so no half-word sits beside an arrow. The chosen lane is scrolled into view.

**Grid.** `repeat(auto-fill, minmax(272px, 1fr))` with a 20px gap: 4 cards across at 1512 and 8 at 2560. Each row is as tall as its longest card, and every card in it stretches to that height. The list has no pages. It opens with ten cards, and a centred block 32px under the grid holds a "Show 10 more jobs" button that adds the next ten below, "Try again" after an error, or "End of the list" once all are shown, and then the count, "20 of 44 shown". Nothing loads on scroll, because that fills a 2,560px monitor with 60 cards at once. A list that fits in ten shows no block.

**Panel beside the grid.** When a job is open, the workspace becomes two columns, `minmax(0, 1fr)` and `clamp(380px, 34vw, 560px)`, with a 24px gap. The panel sticks at `--header-h + 24px` and scrolls within `100dvh - header - 48px`. At 1512 it takes about a third of the width. At 2560 it stops at 560px, about 22%, because the reading width is capped. A wider panel would only lengthen lines, and the extra width goes back to the grid.

**Container steps.** Each grid item is an inline-size container named `card`. At 280px the card's padding grows from 18 to 20px and title, employer and summary step up. At 340px the padding is 22px, the head band's vertical padding grows from 12 to 14px, the score to 2rem, the title to 1.3125rem and the summary to 1rem.

**Phone (at or below 760px).** Not a target device: the dashboard is made for a laptop and a wide monitor, so this layout is kept working rather than refined. One column with a 12px gap. Each card is as tall as its own content, since a row holds one. The wordmark drops to 1.5rem. The two view sliders share the toolbar row, the second wrapping below the first when they do not fit, each scrolling inside its track and keeping the chosen option in view, and New and the place slider wrap below them. The panel is fixed full screen with no radius or shadow and an "All jobs" back button in place of the close button. Lane arrows are hidden.

**Rhythm.** Spacing sits on 4px steps: 4, 6, 8, 12, 14, 16, 18, 20, 24, 28 and 32px. Insets inside wells are 14px by 16px.

## Elevation & Depth

This is a hybrid system. Surfaces are flat at rest and separated by a 1px ring (`box-shadow: 0 0 0 1px line`) rather than a border, and a warm page sits behind white. Soft, diffuse shadows appear only as a response to hover or selection, or on the one floating surface, the panel. No shadow is hard or offset without blur.

### Shadow Vocabulary
- **Hover lift** (`box-shadow: 0 6px 18px rgb(29 34 38 / 0.1), 0 1px 3px rgb(29 34 38 / 0.06)`, dark: `0 8px 22px rgb(0 0 0 / 0.45), 0 1px 3px rgb(0 0 0 / 0.4)`): a card on hover, and under the blue ring on the selected card.
- **Panel** (`box-shadow: 0 12px 32px rgb(29 34 38 / 0.08), 0 1px 3px rgb(29 34 38 / 0.05)`, dark: `0 14px 36px rgb(0 0 0 / 0.45), 0 1px 3px rgb(0 0 0 / 0.4)`): the job panel beside the grid, and the skip link when focused.
- **Pressed** (`box-shadow: 0 1px 3px rgb(29 34 38 / 0.12)`, dark: `0 1px 3px rgb(0 0 0 / 0.5)`): the slider thumb and the lane-row arrow buttons.

### Named Rules
**The Hairline At Rest Rule.** Cards, empty states and skeletons rest on a 1px ring and no shadow. A shadow means hover, selection or the panel.

## Shapes

Two families of corners. Everything you press is a full pill (999px): buttons, chips, segments, icon buttons, badges, lane tags and the slider thumb. Everything that holds content has a gentle radius that steps down as it nests: cards, the panel and empty states at 12px, wells inside the panel (fact block, notices, brief note) at 10px, and the copy field at 8px. Cards clip their content, and the head band bleeds to the card's edges with negative margins.

### Named Rules
**The Pill Rule.** If it is a control, it is a pill. If it holds content, it has a 12, 10 or 8px radius by depth.

## Components

### Buttons
Friendly and plain: pill, one weight, one primary per panel.
- **Shape:** full pill (999px), 40px tall, 18px inline padding.
- **Primary:** accent fill, on-accent text. One per surface: Write brief in the panel.
- **Secondary:** surface fill, line-strong border, ink text. On hover the border goes ink and the fill surface-hover. A pressed secondary (Saved, Applied) keeps the ink border and fills its icon, which is why Applied's icon is a paper plane rather than a check mark.
- **Small:** 32px tall, 12px padding, 0.8125rem, for Reload, Copy and a removed card's Restore.
- **Quiet:** transparent with no border, for the phone panel's back button.
- **Icon button:** a 36px transparent circle in ink-2. On hover it fills with the page grey rather than surface-hover, so the hover shows on a white card.
- **Focus:** 2px accent outline at 2px offset. Colour changes run over 150ms.
- **Disabled:** 55% opacity.

### Chips
- **New chip:** a 36px pill with a line-strong border, an 8px green dot, a label and a count in ink-2. Pressed, it takes the new border, new-soft fill and new text.
- **Lane chip:** a 36px pill with code (700), name (500, truncated at 26rem), count and a green "n new". Pressed, it fills with ink, text goes surface-white and the width cap lifts. Hover sets the border to ink.
- **Slider (segmented control):** one control for the views and for the place, in `Segmented.tsx`. A page-grey pill track with 3px padding and a hairline. Options are 30px pills in ink-2, and the chosen one is ink. Under it sits a white thumb with the pressed shadow and a hairline ring. The component measures the chosen option and the track and sets `--thumb-x`, `--thumb-w` and `--track-w`. The thumb spans the track, and a clip-path cuts the chosen option's pill out of it: a hairline layer 1px outside the option and the white layer on the option, with the shadow as a drop-shadow filter that follows the cut. The filter uses `shadow-pressed-drop`, the pressed shadow with a 1px blur instead of 3px, because a filter's blur spreads about twice as far as a box-shadow's; at 1px the edge matches a 3px box-shadow thumb pixel for pixel in both themes. Saved, Applied and Removed carry their counts in ink-2. The views are two sliders, and the one without the current view gets `data-empty`, which hides its thumb; its glide is off until the thumb is placed again, so the thumb appears on its option instead of sliding in from where it last stood. The views mark the chosen option `aria-current="page"`, and the place marks it pressed.

### Cards / Containers
The signature component, a listing card.
- **Corner Style:** 12px.
- **Background:** surface, on the warm page.
- **Shadow Strategy:** hairline ring at rest, hover lift on hover, a 2px accent ring plus hover lift when selected. Keyboard focus on the card's title button draws a 2px surface gap and a 4px accent ring around the whole card.
- **Border:** none. The ring is a box-shadow.
- **Internal Padding:** 18px, then 20px at 280px and 22px at 340px card width. Bottom padding is 16px, and 18px at 340px.
- **Height:** as tall as the longest card in its row, which every card in the row stretches to. A fixed 7:10 aspect ratio is not used, because it leaves 117 to 196px empty under the summaries at a 1512px viewport.
- **Head band:** bleeds to the top and side edges, keeps the card's own white and has a line rule under it. It is one row, always as tall as a 36px button: the score with its "score" label and any New badge on the left, and on the right the x, an icon button labelled "Remove" with the title, which takes the job into Removed. In Removed a small Restore button with an undo arrow takes the x's place, and an applied job, which cannot be removed, has nothing there. The star is in the footer, not here. Neither cards nor the panel have an employer initials tile, because it carries nothing.
- **Body:** title (3-line clamp, and the whole card is its hit area), employer (one line), a map pin with place ("Stockholm and 2 more"), for an ad from another job site a globe with "via thehub.io" in the same small ink-2 line, then the summary. A Platsbanken ad carries no source line.
- **Summary:** at most 6 lines, which no summary reaches (they run two to five). At least 12px is kept between the text and the footer's hairline, or under the place when a job has no summary. A shorter card in a row takes the rest of the row's height above its footer.
- **Footer:** sits on the card floor behind a line rule. It holds the best-fit lane tag (code in 700 plus the config's `lanes[].short`), "+n" for further lanes, then Closed, a check with "Brief", the rank "#n", and last the star, or an Applied badge in its place on a job marked applied, which cannot also be saved. The star's 36px target overhangs the footer's line above and below, so the footer keeps a lane tag's height, and its glyph ends on the card's text edge. A removed job shows neither until it is restored. It is never shorter than a lane tag, so a card with no lane, as some PhD calls have, keeps its hairline level with the rest of the row.
- **Closed:** the title and score turn ink-2.

### Logo
Three steps rising to a dot: the next role, just out of reach. A 32px SVG in `currentColor` (`Logo.tsx`), so it is ink in light mode and follows dark mode, beside the wordmark with a 10px gap. The same mark is the page's tab icon, an SVG data URI in `index.html` with its own dark-mode colours. It is used over a grid with one filled square, a lens, and a compass, which is too close to Safari's icon. It stays ink, since blue and green each keep their one job.

### Theme Button
An icon button (36px, ink-2, the page grey on hover) at the end of the logo's row. It shows a 20px moon in light mode and a sun in dark, the mode it switches to, and its label says so: "Switch to dark mode" or "Switch to light mode". `ThemeButton.tsx`. It reaches 8px past the gutter so its icon lines up over the edge of the slider below it, and 2px above and below so the row keeps the logo's height. With nothing saved the page follows the computer, also when the computer changes while the page is open. A click is saved as `standard.theme`, unless it lands on what the computer shows, which clears the choice so the page follows the computer again. The switch is instant: every colour changes in one frame, with transitions off for that frame, rather than each control fading over at its own speed. The tab icon is left to follow the computer, since the browser's tab bar does.

### Badges and Lane Tags
Small pills on the page grey in ink-2: 22px tall with 8px padding for badges, 3px by 10px for lane tags. New uses new-soft and new, and Closed uses danger-soft and danger. An employment type takes the neutral badge. In the panel an ad from another job site adds "via thehub.io" as a neutral badge that is a link to the ad on that site, with a 12px external-link icon, ink on hover with an underline.

### Navigation
- **Views:** Top picks, By lane, PhD and Rejected in one slider, then Saved, Applied and Removed in a second beside it, at the left of the toolbar. Removed lists the jobs removed since the last run, most recent first, under a line in ink-2 at 0.875rem saying they go for good at the next daily run. Its view id is `dismissed`, since `removed` already means JobTech closed the ad. The view is called Saved so the view, the Save button, the star's label and the count share one word; its id is `favourites`.
- **The end of the list:** no pager. A list opens with ten cards. `MoreJobs.tsx` shows a secondary button, "Show 10 more jobs" ("Show 3 more jobs" when fewer are left, "Loading more jobs" while disabled, "Try again" under a red line after an error), or "End of the list" in ink-2, and under either the count in tabular figures, "20 of 44 shown", read out when it changes. The ten it adds go below the others, and focus moves to the first of them without the page moving. They are fetched from the number of cards on screen, so a removal never makes the button skip a job. Nothing loads on scroll. Changing the view, lane, place or New starts the new list at the top of the page with ten cards. A job already on screen is never added twice, and ten that arrive for a list since left are dropped. With no pages, the arrow keys turn none.

### Job Panel
The chosen job beside the grid. It is a white 12px surface with a hairline ring and the panel shadow, and a sticky bar with a close button (Esc also closes it). Its content, in order: the employer (name and full place list), the headline title (it receives focus on open), badges, and a page-grey fact block with Apply by, Score and Place in this list in an auto-fit grid of 120px minimums. An applied job adds Applied, the day it was marked, to the fact block. The actions follow in one row: Write brief (primary), Open posting and Save, which an applied job does not show. A removed job shows Restore in Save's place and has no Mark applied, so it is restored before anything else is done with it. One brief serves both `/cv` and `/letter`, so one Write brief button stands where a button for the CV and a button for the cover letter would both write it. After them comes the brief note (accent-soft, or danger-soft on error): the folder, the command that opens Claude Code there, then `/cv` and `/letter`, each with a Copy button named for its command and sections behind line rules: Why this score (Want and Reach as tabular "n of 10"), Summary and Lanes with fit words. Last, behind its own rule, Mark applied: a secondary button with a paper plane that reads Applied when pressed and undoes the mark when pressed again, at the bottom of the panel.

### Motion
- **Glide:** list changes, opening and closing the panel run through `document.startViewTransition`. Every card has its own `view-transition-name` (`card-<id>`) so it glides to its new place over 220ms with ease `cubic-bezier(0.16, 1, 0.3, 1)`. Only the cards within a screen of view take part: App.tsx marks the rest `data-far` for that one transition, since capturing every card of a long scrolled list stalls the glide. The ten that load at the end of the list appear without it. A card removed or restored fades out over the same 220ms while the cards after it glide into its place, and focus moves to the card that took its place. The panel (`job-panel`) slides in from 24px right with a fade over 220ms and leaves over 160ms ease-in. The root cross-fade is 140ms.
- **Slider:** a slider's thumb glides to the chosen option over 240ms on the same ease, animating its clip-path, so the pill keeps round ends at every frame and nothing is laid out again. Animating transform and width instead would be a layout animation. It starts gliding only once the fonts are in, so the page does not open with a slide.
- **State:** colour and shadow changes run 150 to 200ms on the same ease. A card's shadow takes 180ms.
- **Theme:** flipping light and dark is instant, every colour in one frame, never a fade.
- **Reduced motion:** under `prefers-reduced-motion: reduce`, App.tsx skips the view transition entirely and CSS disables all transition animations. The lane arrows scroll instantly, the slider thumb jumps, and the skeleton pulse does not run.

## Do's and Don'ts

### Do:
- **Do** keep blue to its three jobs: the primary action, the selected card's 2px ring and the 2px focus outline.
- **Do** mark current and pressed states in ink: the chosen slider option, the lane chip fill and the filled star.
- **Do** keep green to New: the dot, the chip, the badge and the lane's "n new".
- **Do** set tabular figures on any number a reader compares.
- **Do** rest containers on a 1px hairline ring, and add a soft shadow only for hover, selection or the panel.
- **Do** make every control a pill and every container 12, 10 or 8px by depth.
- **Do** keep the panel at `clamp(380px, 34vw, 560px)` so its reading width stays capped on wide screens.
- **Do** clamp card text to whole lines that fit, never cut a line above blank space.
- **Do** give every new colour a dark value that keeps its role.
- **Do** keep motion instant under reduced motion.

### Don't:
- **Don't** use blue for starred, current view or pressed lane.
- **Don't** use green for success, confirmation or a good score.
- **Don't** build dense admin tables or crowd a card: the refused worlds are cold and corporate, crowded like an admin tool, and plain to the point of dull.
- **Don't** add a second type family for display or novelty.
- **Don't** cover the grid with the panel above the phone breakpoint.
