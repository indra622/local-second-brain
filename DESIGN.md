---
version: alpha
name: Local Second Brain monitor
colors:
  primary: "#73cbb9"
  text: "#e7e9ef"
  muted: "#aab2c0"
  background: "#111217"
  surface: "#1b1d24"
  border: "#596373"
  warning: "#ffc078"
typography:
  heading:
    fontFamily: system-ui
    fontSize: 24px
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: system-ui
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.65
rounded:
  control: 5px
  panel: 7px
spacing:
  small: 8px
  medium: 16px
  panel: 20px
---

## Overview

A compact monitoring home precedes the existing knowledge explorer. Panel rows and
snapshot distributions provide an operational overview without invented telemetry.
The dark-neutral aesthetic takes inspiration from monitoring dashboards, not Grafana
branding or a Grafana dependency. Reading and uncertainty remain primary.

## Colors

Use a near-black background and charcoal panels. Teal indicates selection and known
counts, amber indicates attention, and muted blue-gray indicates unspecified state.
Every semantic color is accompanied by readable text. These are observed states, not
confidence or health scores. The explorer shares the same normative palette.

## Typography

Use local system fonts, a 24px page title, 16px body text, compact panel captions and
large tabular counts. Technical metadata uses monospace behind disclosure controls.

## Layout

Desktop home has four statistic panels, three distribution panels and source/recent
record rows. Mobile uses a two-column statistic grid and stacked distribution panels.
Top navigation switches Home and Explore. Explore retains the collapsible mobile list.

## Elevation & Depth

Subtle borders and tonal layers separate panels. Do not use hero blocks or animation.

## Shapes

Use 5px control corners and restrained 7px panel corners, consistent across views.

## Components

Panels and distribution rows use native keyboard-focusable buttons to drill into the
explorer. Native disclosures hold mechanics and declaration context. Visible refresh
errors retain the last successful home and explorer. Unknown and partial states remain
explicit. Recent rows use declared metadata times, never authenticated activity telemetry.

## Do's and Don'ts

- Separate current concepts, loaded historical revisions and unique current source bindings.
- Show unspecified deadlines, malformed records and unread files separately.
- Keep preserved sources and interpreted note text distinct without authenticating actors.
- Do not render stored HTML or execute links.
- Do not add uptime, growth, cost, confidence or time-series without observed evidence.
