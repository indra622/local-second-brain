---
version: alpha
name: Local Second Brain Workbench
colors:
  primary: '#176e69'
  background: '#f5f7f7'
  surface: '#fdfefe'
  text: '#182b2b'
  muted: '#4d6262'
  border: '#718686'
  tint: '#e3efed'
  dark-primary: '#87d0c6'
  dark-background: '#142222'
  dark-surface: '#1b2d2d'
  dark-text: '#e9f2f1'
  dark-muted: '#b1c7c5'
  dark-border: '#789592'
  dark-tint: '#263f3d'
typography:
  headline:
    fontFamily: system-ui
    fontSize: 46px
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: -0.035em
  body:
    fontFamily: system-ui
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.6
  code:
    fontFamily: ui-monospace
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.7
rounded:
  control: 6px
  panel: 12px
spacing:
  xs: 8px
  sm: 16px
  md: 24px
  lg: 32px
  xl: 48px
components:
  primary-button:
    backgroundColor: '{colors.primary}'
    textColor: '{colors.surface}'
    rounded: '{rounded.control}'
---

## Overview

A new explanatory site for AI-assisted knowledge workers, attached to an existing CLI repository. Practical, bright workbench surfaces; no imitation of a named design system. Native static HTML/CSS/JS is intentional. DESIGN_VARIANCE=6, MOTION_INTENSITY=3, VISUAL_DENSITY=4.

Existing README hero, benefit headings, examples and installation instructions remain intact. The generated mark supplied by the parent is preserved as logo-original.png; logo.png is a resized derivative, not new artwork.

## Colors

One teal accent, neutral surfaces. System color preference applies to the entire page, with a session-only manual override. Terminal replay is a captured asset with a fixed light background in either theme. No theme state or personal data is stored.

## Typography

System sans-serif for live text; system monospace for actual file content. No external fonts. Headline scales to 34px on mobile. Long paths and source hashes wrap.

## Layout

1180px maximum content width, introductory headline and actions above full-width future-vision artwork, then a functioning sample workbench. The supplied artwork replaces the large logo panel; the header mark remains. Preserve the entire image at its original aspect ratio at every width, including mobile. Live English/Korean captions explain the intended connection between sources, past decisions, today’s question and the next output, and distinguish this vision from the current CLI. Below 768px, the workbench and replay become single-column. No horizontal scrolling at 390px.

## Elevation & Depth

Flat tonal surfaces and one border around the workbench establish hierarchy. No shadows, glows, stock imagery or fabricated screenshots.

## Shapes

6px controls and content blocks, 12px major panels. No decorative pills.

## Components

Native buttons, input, select and details elements provide keyboard interaction. Selected notes use aria-pressed. Loading, error and no-result states are explicit. Focus uses a 3px teal outline with 4px offset. GIF playback requires an explicit click and can be stopped; no automatic animation. Reduced-motion CSS disables transitions and animations.

## Do's and Don'ts

Preserve actual source and CLI text when translating labels. Label synthetic prepared text, file explanation, draft trust and deadline semantics. Use real captured output, the supplied mark and the supplied future-vision artwork. The vision is an illustration, not a current screenshot. Do not imply shipped GUI, authenticated review, model generation, semantic retrieval, customer proof or measured speed.

Skill preflight context: real component preview applies; React, Tailwind, icon packages, GSAP, stock photography, social proof, forms beyond search, marquees, bento, SEO migration and consumer product palettes are N/A. The complete visitor journey is introduction, sample exploration, real CLI evidence, portable files and installation. Hosting is this repository's Pages only.
