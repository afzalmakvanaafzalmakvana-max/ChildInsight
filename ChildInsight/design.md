# ChildInsight — design.md

## 1. UI/UX Principles
- Clean, intuitive, mobile-first, professional-but-friendly (not cartoonish).
- Parent/Teacher/Admin: modern analytics-dashboard feel (cards, charts, tables).
- Child: large buttons, minimal text, colourful, forgiving of misclicks, instant feedback.
- Consistent spacing, rounded corners, soft shadows, smooth (not distracting) transitions.

## 2. Colour & Theme
- **Primary:** a calm, trustworthy blue/teal (e.g. `#2F6FED`) — used for primary actions,
  active nav, chart primary series.
- **Secondary:** a warm supporting colour (e.g. amber `#F5A623`) for highlights/badges.
- **Accent:** soft purple or coral for the child-facing screens only, to differentiate them.
- **Background:** near-white (`#F7F9FC`) for dashboards; pure white cards on top.
- **Text:** dark slate (`#1F2937`) for body, muted grey (`#6B7280`) for secondary text.
- **Status:** success green, warning amber, error red — used consistently across all
  dashboards (progress up = green, stable = neutral grey, practice-suggested = amber).
- Light theme by default; dark theme optional/stretch goal, remembered in `design.md`
  §4 preferences.

## 3. Fonts & Typography
- Primary font: a clean humanist sans-serif (e.g. Inter / Poppins for headings, Inter
  for body) loaded from Google Fonts or self-hosted.
- Headings: H1 28–32px bold, H2 22–24px semibold, H3 18px semibold.
- Body: 15–16px regular, 1.5 line-height for readability.
- Child-facing screens: slightly larger body text (18px+) and bold button labels.
- Weights used: Regular (400), Medium (500), SemiBold (600), Bold (700) — avoid mixing
  in more than 3 weights per screen.

## 4. Memory (UI Preferences to persist per user)
- Theme mode (light/dark) if implemented
- Language preference
- Sidebar collapsed/expanded state
- Last-viewed child (for parents/teachers with multiple children)

## 5. Page-Level Notes
- **Landing page:** hero + "How it works" (4 steps) + features grid + dashboard preview
  mockup + "Why ChildInsight" + Privacy & Responsible Use section + footer.
- **Child home:** single screen, category buttons only, no nested menus.
- **Parent/Teacher dashboards:** 3 summary cards up top, then a 2-column layout —
  category performance chart + trend line chart, recommendations list below.
- **Reports:** print-friendly layout, responsible-use notice always in the footer of
  the report.
