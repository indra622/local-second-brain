---
version: alpha
name: Local Second Brain monitor
colors:
  primary: "#176e69"
  text: "#182b2b"
  muted: "#4d6262"
  background: "#f5f7f7"
  surface: "#fdfefe"
  border: "#718686"
  warning: "#823b17"
typography:
  heading:
    fontFamily: system-ui
    fontSize: 32px
    fontWeight: 700
    lineHeight: 1.4
  body:
    fontFamily: system-ui
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.65
rounded:
  control: 5px
  panel: 10px
spacing:
  small: 8px
  medium: 16px
  panel: 24px
---

## Overview

A quiet reading surface for the person who monitors an agent-maintained CLI bundle.
Reuse the existing site's teal palette without its marketing layout. Content, source
availability and uncertainty take priority over decorative charts or scores.

## Colors

Teal identifies selection and keyboard focus. Dark neutral text and muted explanatory
text remain readable on the pale background. Warnings use text as well as color.

## Typography

Use local system fonts without network requests. Long Korean content uses generous
line spacing. Technical metadata uses monospace inside collapsed details.

## Layout

A current-note sidebar and a reading pane share the desktop. On narrow screens, filters
and notes precede the content. Revision comparison stacks vertically on mobile.

## Elevation & Depth

Use subtle borders and tonal surfaces instead of shadows or animation.

## Shapes

Small control radii and restrained panel corners match the existing product palette.

## Components

All navigation uses native buttons, labeled inputs, selects and expandable details.
Keyboard focus is visible. Refresh errors retain the last successful content. Metadata,
hashes and paths belong behind expandable details; readable source content stays primary.

## Do's and Don'ts

- Show missing, unknown and partial states explicitly.
- Keep source text and interpreted note text distinct without authenticating actor names.
- Do not render stored HTML, execute links or suggest editing actions.
- Do not add invented metrics or decorative graphs.
