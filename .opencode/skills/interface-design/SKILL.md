---
name: interface-design
description: Craft-first interface design for dashboards, admin panels, SaaS apps, tools, settings pages, data interfaces, and interactive products. Use when designing, building, reviewing, auditing, or refining product UI where visual craft, layout hierarchy, tokens, states, visual direction, or design-system consistency matter. Not for marketing pages, landing pages, campaigns, or brand-only work.
---

# Interface Design

Build product interfaces with the craft of a top design team ΓÇö Linear, Vercel, Stripe, Apple. The difference between those and generic output is not talent. It is that every decision was *decided*, the hierarchy is unmistakable, and a hundred small details are correct at once. This skill is how you get there.

## Scope

**Use for:** Dashboards, admin panels, SaaS apps, tools, settings pages, data interfaces.

**Not for:** Landing pages, marketing sites, campaigns, brand-only work. Use a marketing/frontend design skill for those.

This skill is self-contained: direction, visual hierarchy, design-system architecture, and the polish and motion essentials needed to ship production-grade UI all live here.

---

# The Problem

You will generate generic output. Your training has seen thousands of dashboards, and the patterns are strong. You can follow this entire process ΓÇö explore the domain, name a signature, state your intent ΓÇö and still produce a template: warm colors on cold structures, friendly fonts on generic layouts.

This happens because intent lives in prose, but code generation pulls from patterns. The gap between them is where defaults win. Process helps, but it doesn't guarantee craft. You have to catch yourself, and you have to know the concrete moves that defaults don't.

**The bar:** If another AI, given a similar prompt, would produce substantially the same output, you have failed. Not different for its own sake ΓÇö different because the interface emerged from *this* user, *this* task, *this* world. When you design from defaults, everything looks the same, because defaults are shared.

---

# Where Defaults Hide

Defaults disguise themselves as infrastructure ΓÇö the parts that feel like they just need to work, not be designed.

- **Typography feels like a container.** But type isn't holding your design, it *is* your design. The weight of a headline, the personality of a label, the texture of a paragraph shape how the product feels before anyone reads a word. Reaching for your usual font means you're not designing.
- **Navigation feels like scaffolding.** But navigation *is* the product ΓÇö where you are, where you can go, what matters. A page floating in space is a component demo, not software.
- **Data feels like presentation.** But a number on screen is not design. What does it *mean* to the person looking? A progress ring and a stacked label both show "3 of 10" ΓÇö one tells a story, one fills space.
- **Token names feel like implementation detail.** But `--ink` and `--parchment` evoke a world; `--gray-700` and `--surface-2` evoke a template. Someone reading only your tokens should guess what product this is.

There are no structural decisions. Everything is design. The moment you stop asking "why this?" is the moment defaults take over.

---

# Intent First

Before touching code, answer these. Keep it a compact working brief unless the direction needs user confirmation.

- **Who is this human?** Not "users." The actual person. Where are they when they open this? What did they do 5 minutes ago, what will they do 5 minutes after? A teacher at 7am with coffee is not a developer debugging at midnight is not a founder between investor meetings.
- **What must they accomplish?** The verb. Grade these submissions. Find the broken deployment. Approve the payment. The answer determines what leads, what follows, what hides.
- **What should this feel like?** In words that mean something. "Clean and modern" means nothing ΓÇö every AI says that. Warm like a notebook? Cold like a terminal? Dense like a trading floor? Calm like a reading app? This shapes color, type, spacing, density ΓÇö everything.

If the prompt is too vague to identify the human, task, and feel, ask one concise question. If context allows a responsible assumption, state it briefly and proceed.

**Intent must be systemic.** Saying "warm" then using cold colors is not following through. If the intent is warm: surfaces, text, borders, accents, semantic colors, type ΓÇö all warm. If dense: spacing, type size, information architecture ΓÇö all dense. Check every token against the stated intent. For every choice ΓÇö layout, color temperature, typeface, spacing scale, hierarchy ΓÇö you must be able to say *why*. "It's common" or "it works" means you defaulted.

---

# Product Domain Exploration

This is where defaults get caught ΓÇö or don't. Generic path: Task type ΓåÆ visual template ΓåÆ theme. Crafted path: Task type ΓåÆ product domain ΓåÆ signature ΓåÆ structure + expression. The difference is time spent in the product's world before any visual thinking.

**Produce all four before proposing any direction:**

- **Domain** ΓÇö concepts, metaphors, vocabulary from this product's world. Not features ΓÇö territory. Minimum 5.
- **Color world** ΓÇö what colors exist *naturally* here? Not "warm" or "cool" ΓÇö go to the actual world. If this product were a physical space, what would you see? List 5+.
- **Signature** ΓÇö one element (visual, structural, or interaction) that could only exist for THIS product. If you can't name one, keep exploring.
- **Defaults** ΓÇö 3 obvious choices for this interface type, visual AND structural. You can't avoid patterns you haven't named.

**The test:** Read your proposal with the product name removed. Could someone identify what it's for? If not, explore deeper.

---

# Render It When You Can

If an inline visual-rendering tool is available in the session (e.g. a `show_widget` / `visualize` tool that renders HTML or SVG inline in the conversation), prefer **showing** the design over describing it. A direction trapped in prose is a fraction as useful as one the person can look at. This is conditional: when no such tool is present (CI, headless agents, plain terminals), fall back to code, tokens, and a written proposal. Never assume the tool exists; check, then use it.

Render at three moments:

1. **Proposing a direction.** Alongside the Suggest + Ask block, render a small live specimen: the palette as actual swatches, the type scale in the real typeface, the surface-elevation steps as stacked cards, the signature element as a real component. The person should *see* "warm like a notebook," not read the words.
2. **Designing a component.** Render the actual component (or a tight before/after, both variants side by side) so the craft decisions ΓÇö spacing, borders, hierarchy, states ΓÇö are visible, not asserted. Render the real states (default, hover, empty, error) where they matter.
3. **Critiquing or auditing.** Render the current version and the improved version together so the gap is shown, not narrated.

Rules when rendering:

- The widget shows the **visual only**. All reasoning, the domain exploration, the rejected-defaults list, and the recommendation stay in your response text ΓÇö never paste prose into the widget.
- Match the rendering tool's own design-system contract (load its `read_me`/guidance if it has one). Use its theme variables so the specimen inherits light/dark mode and sits native in the host. Don't fight the host chrome.
- The specimen must still pass the checks below. A rendered default is still a default ΓÇö rendering is how craft gets *seen*, not a substitute for it.
- This renders to the *conversation*, not the project. The actual implementation still lands in the codebase through normal edits.

The point: collapse the loop between "here's my thinking" and "here's what it looks like" into a single message the person can react to.

---

# Visual Hierarchy & Composition

The single biggest driver of "this looks designed" versus "this looks generated." Defaults produce *flatness* ΓÇö everything the same size, weight, and spacing, so nothing leads and the eye has nowhere to go. Craft produces *hierarchy* ΓÇö the eye knows instantly what matters. These are concrete moves, not vibes.

## One focal point per view

Every screen has one thing the user came to do. That thing dominates ΓÇö through size, contrast, position, or the space around it. When everything competes equally, nothing wins and the interface reads like a parking lot. Before building, name the focal element out loud. Then make it win: bigger, higher-contrast, or ringed in whitespace. Demote everything else deliberately.

## Type scale is a ratio, and weight beats size

Don't pick sizes by feel. Pick a ratio and step it: ~1.2 (minor third) for dense/calm UI, ~1.25 for most product UI, ~1.333 for expressive. From a 14ΓÇô16px body that yields a *visibly* distinct scale, not 15/16/17 mush. A 14px base at 1.25: `caption 11 ┬╖ body 14 ┬╖ h4 16 ┬╖ h3 18 ┬╖ h2 22 ┬╖ h1 28 ┬╖ display 44+`. Round to whole pixels and to your spacing grid.

The Apple/Linear move: **weight and color do more hierarchy work than size.** A single 14px size holds three tiers through weight + opacity alone ΓÇö `value: 600 / primary`, `label: 500 / secondary`, `meta: 400 / muted` ΓÇö separating more cleanly than two regular weights two points apart. Build from three levers together (size, weight, color/opacity), never size alone. If you squint and can't tell headline from body from label, the hierarchy is too weak.

Worked example ΓÇö a metric, flat vs decided. *Flat:* `Revenue` / `$48,200` both 14px regular gray, three identical boxes, no focal point. *Decided:* `REVENUE` 11px/500/muted/tracked ┬╖ `$48,200` 28px/600/primary/tabular-nums (the hero) ┬╖ `Γåæ12%` 12px/500/success. Same data, opposite legibility ΓÇö the figure leads through size+weight+one accent, the label is demoted, secondary metrics drop to a lower tier.

## Density is a decision, expressed in px

Linear is tight; Stripe is airy. Neither is default ΓÇö both are *chosen*, and the choice is the same number repeated everywhere. Decide the density up front and name the values: a tool panel at 12ΓÇô16px padding feels workbench-tight; the same card at 24px feels like a brochure. The same number can be right in one context and lazy in another. Pick deliberately, then hold it.

## Spatial rhythm ΓÇö breathe unevenly

Great interfaces don't space everything equally. Dense control zones give way to open content; heavy elements balance against light ones; the eye travels with purpose. Monotone layouts ΓÇö same card size, same gap, same density everywhere ΓÇö are the sound of no one deciding. Vary the rhythm on purpose: group tightly-related things, then put real air between groups.

## Proportions speak

A 280px sidebar next to full-width content says "navigation serves content." A 360px sidebar says "these are peers." The specific number declares what matters. If you can't articulate what a proportion is saying, it isn't saying anything. Choose widths and ratios that state a relationship.

## Distribution and restraint (the "expensive" look)

- **~60/30/10**: a dominant neutral surface, a secondary tone, and ~10% accent. Color is a scarce resource ΓÇö most of the screen is structure.
- **One accent, used with intention**, beats five colors used without thought. Gray builds structure; color *communicates* (status, action, identity). Unmotivated color is noise.
- **Hierarchy through space and weight, not lines.** Reach for whitespace and tonal shift before borders and dividers. The most premium interfaces are mostly invisible structure.
- **Optical sizing on large type**: tighten letter-spacing as type gets bigger (headings slightly negative tracking); loosen line-height on body for readability (~1.5). Tight type reads as crafted; default tracking on a 32px heading reads as a document.

---

# Craft Foundations

## Subtle Layering (the backbone)

Regardless of direction, this applies to everything. You should *barely notice the system working* ΓÇö when you look at Vercel's dashboard you don't think "nice borders," you just understand the structure. Invisible craft is working craft.

**Surface elevation.** Surfaces stack: a dropdown sits above a card sits above the page. Build a numbered system ΓÇö base, then increasing levels. Each jump is only a few percentage points of lightness ΓÇö e.g. dark mode base ΓåÆ +7% ΓåÆ +9% ΓåÆ +12%; light mode stays light and adds shadow instead. You can barely see one step in isolation, but stacked, the hierarchy emerges. Whisper-quiet shifts you feel rather than see.

- **Sidebars:** same background as canvas, not a different color. Different colors fragment the space into "sidebar world" and "content world." A subtle border is enough.
- **Dropdowns/popovers:** one level above their parent surface, or they blend in and layering is lost.
- **Inputs:** slightly *darker* than surroundings, not lighter. Inputs are inset ΓÇö they receive content. A darker fill signals "type here" without heavy borders.

**Borders.** Should disappear when you're not looking for them, but be findable when you need structure. Low-opacity rgba blends with the background and defines an edge without demanding attention; solid hex borders look harsh by comparison. Dark mode lives around `rgba(255,255,255,0.06ΓÇô0.12)`, light mode slightly higher. Build a progression ΓÇö standard, softer separation, emphasis, focus-ring ΓÇö and match intensity to the importance of the boundary.

**The squint test:** blur your eyes at the interface. You should still perceive hierarchy ΓÇö what's above what, where sections divide ΓÇö but nothing should jump out. No harsh lines, no jarring shifts. Just quiet structure. Get this wrong and nothing else matters.

## Infinite Expression

Every pattern has infinite expressions ΓÇö **no two interfaces should look the same.** A metric display could be a hero number, inline stat, sparkline, gauge, progress bar, comparison delta, or trend badge. Same sidebar width, same card grid, same icon-left-number-big-label-small metric boxes every time *signals AI-generated immediately* and is forgettable. Linear's cards don't look like Notion's; Vercel's metrics don't look like Stripe's. Same concepts, infinite expressions. Before building, ask: what's the ONE thing users do here, and what product solves a similar problem brilliantly?

## Color Lives Somewhere

Every product exists in a world, and that world has colors. Before reaching for a palette, walk into the physical version of this space ΓÇö what materials, what light, what objects? Your palette should feel like it came FROM somewhere, not applied TO something. Temperature is one axis; also ask quiet or loud, dense or spacious, serious or playful, geometric or organic. A trading terminal and a meditation app are both "focused" ΓÇö completely different kinds of focus.

---

# Before Writing Each Component

**Every time** you write UI code ΓÇö even small additions ΓÇö state:

```
Intent:     [who is this human, what must they do, how should it feel]
Hierarchy:  [the focal element, and how it wins ΓÇö size / weight / contrast / space]
Palette:    [colors from your exploration ΓÇö and WHY they fit this world]
Depth:      [borders / subtle shadows / layered ΓÇö and WHY it fits the intent]
Surfaces:   [your elevation scale ΓÇö and WHY this temperature]
Typography: [typeface + the size/weight/color levers ΓÇö and WHY]
Spacing:    [base unit + chosen density]
```

This checkpoint is mandatory. If you can't explain WHY for each, you're defaulting ΓÇö stop and think.

---

# Use What Exists

The most common way AI degrades a codebase: it hand-rolls what already exists. A bespoke `<div onClick>` "button" beside the project's real `Button`. A from-scratch dropdown with no keyboard support beside an installed primitive that has it. A 14-class Tailwind string copy-pasted onto every card instead of the component or token that's right there. Every one of these is the same failure ΓÇö generating new instead of using what's present ΓÇö and the result is inconsistent, inaccessible, and unmaintainable. **Before you build a control or style an element, look at what the project already gives you.**

## Controls: native ΓåÆ primitive ΓåÆ hand-roll

1. **Native HTML first** where it works. A `<button>` is a button; an `<a>` is a link; `<input type="text">`, `<dialog>`, `<details>` exist. Never `<div onClick>` something the platform already provides ΓÇö you lose focus, keyboard, and semantics for free.
2. **A battle-tested headless primitive** for anything stateful and hard to get right ΓÇö select, combobox, dialog, popover, tooltip, dropdown menu, tabs, date picker. These ship keyboard navigation, focus management, ARIA, and collision/positioning that take days to reproduce correctly. Reach for what the ecosystem already trusts (e.g. Radix UI, React Aria, Ark, Headless UI, Vaul, `cmdk` in React; the equivalent accessible primitive in other frameworks), then style it to your direction. "Build custom" means *compose and style a primitive*, not write the behavior from scratch.
3. **Hand-roll only as a genuine last resort** ΓÇö no primitive fits, or there's no dependency budget. Then you owe the complete behavior contract: keyboard nav (arrow keys, Enter, Escape), focus trap/return, full ARIA roles and state, click-outside, and scroll-lock for overlays. A styled control missing these is broken, however good it looks.

## Styling: system ΓåÆ component ΓåÆ token ΓåÆ utility

1. **If the project has a design system, use it.** shadcn/`Button`, a CVA variant set, a theme, a component library ΓÇö use `<Button variant="ΓÇª">` and the existing variants before writing a one-off. Match the codebase's styling convention (Tailwind, CSS modules, CSS-in-JS), don't introduce your own.
2. **When a styled element repeats, extract a component.** The same utility string on nine buttons is duplication, not design. One component (or one CVA/variant) owns it; call sites stay clean. Extract on the second real reuse, not the first.
3. **Bind to semantic tokens, not hardcoded literals.** `bg-card border-border text-muted-foreground`, not `bg-white border-gray-200 text-gray-500`. Hardcoded `gray-200`/`#fff`/`px-4` raw values are the Tailwind form of random hex ΓÇö they break theming and dark mode and signal no system. (See Token Architecture below.)
4. **Inline utilities are for genuine one-offs** ΓÇö a layout nudge used once. The tell of slop is the *same* long className sprayed everywhere; that's a missing component or token, not styling.

---

# Design System Essentials

The token, spacing, and depth architecture beneath every craft decision.

- **Token architecture.** Every color traces to a small set of primitives: foreground (text), background (surface), border, brand, semantic (destructive/warning/success). No random hex ΓÇö everything maps to primitives.
- **Text hierarchy ΓÇö four levels.** Primary, secondary, tertiary, muted (default / supporting / metadata / disabled). Using only two means the hierarchy is too flat.
- **Spacing.** Pick a base unit (4 or 8px), use multiples only. Scale by context: micro (icon gaps), component (within buttons/cards), section (between groups), major (between areas). Random values signal no system.
- **Padding.** Symmetrical ΓÇö if one side has a value, the others match unless content genuinely demands asymmetry.
- **Depth ΓÇö choose ONE and commit.** Borders-only (clean, technical, dense tools) ┬╖ subtle shadows (approachable) ┬╖ layered shadows (premium, dimensional) ┬╖ surface-color shifts (tints, no shadows). Don't mix strategies.
- **Border radius ΓÇö a scale.** Small for inputs/buttons, medium for cards, large for modals. Don't mix sharp and soft randomly.
- **Control tokens.** Inputs/selects/checkboxes get dedicated background, border, and focus tokens ΓÇö don't reuse surface tokens, so you can tune controls independently. Native `<select>`/`<input type="date">` can't be styled ΓÇö compose a headless primitive instead of hand-rolling one (see "Use What Exists").
- **Dark mode.** Shadows are weak on dark ΓÇö lean on borders. Desaturate semantic colors slightly. Same hierarchy system, inverted values. Keep one hue; shift only lightness across surfaces.

---

# Polish & Motion Essentials

A hundred small details compound into "feels great." These are the highest-leverage ones ΓÇö enough to ship genuinely polished UI.

## Static polish

- **Concentric radius.** Nested rounded elements: `outerRadius = innerRadius + padding`. Same radius on parent and child is the most common thing that makes UI feel off.
- **Tabular numbers.** Any dynamic number (counters, prices, timers, table columns) gets `font-variant-numeric: tabular-nums` to prevent layout shift.
- **Optical alignment.** When geometric centering looks off, fix it optically ΓÇö icon-side padding Γëê text-side ΓêÆ 2px; nudge play triangles ~2px right.
- **States are not optional.** Every interactive element needs default, hover, active, focus, disabled. Data needs loading, empty, error. Missing states feel broken ΓÇö they're the fastest tell of an unfinished interface.
- **Hit areas ΓÇö 44├ù44px (WCAG), 40 at minimum.** If the visible control is smaller (a 20px checkbox), extend with a pseudo-element. Never let two hit areas overlap.
- **Shadows over borders for elevation.** For cards/buttons/containers that lift, prefer a layered transparent `box-shadow` (it adapts to any background); keep real borders for dividers and input outlines. Light-mode lift stacks three layers ΓÇö a 1px ring + two soft depths, e.g. `0 0 0 1px rgba(0,0,0,.06), 0 1px 2px -1px rgba(0,0,0,.06), 0 2px 4px rgba(0,0,0,.04)`; dark mode collapses to a single ring `0 0 0 1px rgba(255,255,255,.08)` (depth shadows don't read on dark).
- **Text wrapping.** `text-wrap: balance` on headings; `text-wrap: pretty` on body/captions to kill orphans.
- **Font smoothing.** `-webkit-font-smoothing: antialiased` on the root (macOS renders heavy otherwise).
- **Image outlines.** 1px inset outline, pure `rgba(0,0,0,0.1)` light / `rgba(255,255,255,0.1)` dark ΓÇö never a tinted near-black/white (reads as dirt on the edge).

## Motion

Motion should be felt, not watched. Fast, purposeful, and *never* in the way.

- **Should it animate at all?** Actions repeated 100+├ù/day (keyboard shortcuts, command palette) get **no** animation ΓÇö it makes them feel slow. Occasional surfaces (modals, drawers, toasts) get standard animation. Rare/first-run moments can add delight.
- **Duration < 300ms** for UI. Button press 100ΓÇô160ms; tooltips/popovers 125ΓÇô200ms; dropdowns 150ΓÇô250ms; modals/drawers 200ΓÇô500ms. A 180ms dropdown feels more responsive than a 400ms one.
- **Custom ease-out, never ease-in.** Built-in curves are too weak. Use `cubic-bezier(0.23, 1, 0.32, 1)` for entering/interactive; ease-in-out (`cubic-bezier(0.77, 0, 0.175, 1)`) for on-screen movement. `ease-in` delays the first frame ΓÇö the moment the user is watching ΓÇö and feels sluggish.
- **Press feedback.** `transform: scale(0.97)` on `:active` (never below 0.95). Tactile confirmation the UI heard the click.
- **Never animate from `scale(0)`.** Nothing appears from nothing ΓÇö start at `scale(0.95)` + `opacity: 0`.
- **Origin-aware popovers.** Popovers scale from their trigger (`transform-origin` set to the trigger), not center. Modals are the exception ΓÇö they stay centered.
- **Only animate `transform` and `opacity`** (GPU-composited). Animating width/height/margin/padding triggers layout + paint and drops frames. Never `transition: all` ΓÇö name exact properties.
- **Stagger entrances** 30ΓÇô80ms between items for a natural cascade; keep exits faster and subtler than enters.
- **Respect `prefers-reduced-motion`** ΓÇö keep opacity/color transitions, drop movement.

---

# Avoid

- **Harsh borders** ΓÇö if borders are the first thing you see, they're too strong
- **Dramatic surface jumps** ΓÇö elevation should be whisper-quiet
- **Flat hierarchy** ΓÇö everything one size/weight; no clear focal point
- **Monotone layout** ΓÇö same card size, gap, and density everywhere
- **Inconsistent spacing** ΓÇö the clearest sign of no system
- **Mixed depth strategies** ΓÇö pick one and commit
- **Missing states** ΓÇö hover, focus, disabled, loading, empty, error
- **Dramatic drop shadows** ΓÇö subtle, not attention-grabbing
- **Large radius on small elements**; **thick decorative borders**
- **Gradients and color for decoration** ΓÇö color should mean something
- **Multiple accent colors** ΓÇö dilutes focus
- **Different hues for different surfaces** ΓÇö keep one hue, shift only lightness
- **Default typography** ΓÇö system/Inter fonts and size-only hierarchy where a direction was set
- **Structural hacks** ΓÇö negative margins undoing parent padding, escape-hatch `calc()`, absolute positioning to dodge layout flow

---

# Workflow

## Communication
Be invisible. Don't announce modes or narrate process. Never say "I'm in ESTABLISH MODE" or "Let me check system.md." Jump into the work; state suggestions with reasoning.

## Execution discipline
Use this skill as a working discipline, not just advice. When editing UI:

1. Inspect the existing app, design tokens, component patterns, and `.interface-design/system.md` if present.
2. Make the domain exploration concrete before choosing layout, color, type, density, and navigation.
3. For greenfield screens, major redesigns, or vague direction, consider a visual reference pass *if an image-generation tool is available* (skip otherwise ΓÇö it's a companion, never the deliverable). Four modes: **direction board** (2ΓÇô3 abstract mood/material/color explorations before code ΓÇö no real UI), **UI reference** (medium-fidelity composition for a chosen direction), **paintover** (a stronger version of an existing screenshot), **raster asset** (empty-state art, textures ΓÇö never icons/logos/charts). Always reject generic SaaS, illegible text, off-domain palettes; extract palette/density/proportions/signature, then build it in real code and verify in the browser.
4. Patch the implementation, then run the relevant build/typecheck/tests when available.
5. Verify visually for non-trivial UI. Use the inline render tool, a local browser, or screenshots at desktop and mobile widths; fix overlap, broken spacing, blank states, unreadable text, missing assets, and generic composition before presenting.
6. Keep user-facing updates short. Don't expose long private design monologues ΓÇö surface the useful recommendation or decision.

## Suggest + Ask
Lead with exploration and recommendation, then confirm:

```
Domain:     [5+ concepts from the product's world]
Color world:[5+ colors that exist in this domain]
Signature:  [one element unique to this product]
Rejecting:  [default 1] ΓåÆ [alternative], [default 2] ΓåÆ [alternative], [default 3] ΓåÆ [alternative]
Direction:  [approach connecting to the above]
```

Then ask: "Does that direction feel right?" If an inline render tool is available, render a live specimen of the direction in the same message ΓÇö show the palette, type, and signature, don't just name them.

## Build flow
- **If `.interface-design/system.md` exists:** read it and apply ΓÇö decisions are made.
- **If not:** explore domain (all four outputs) ΓåÆ propose (reference all four) ΓåÆ confirm when the direction is ambiguous or costly to change ΓåÆ build ΓåÆ run the checks below ΓåÆ offer to save.

## The checks (before showing)
Run these against your output; if any fails, iterate before presenting.

- **Swap test** ΓÇö swap your typeface for the usual one, your layout for a standard template: would anything feel different? Where swapping wouldn't matter is where you defaulted.
- **Squint test** ΓÇö blur your eyes: hierarchy still readable? Nothing jumping out harshly?
- **Signature test** ΓÇö point to five specific elements where your signature appears. "The overall feel" doesn't count.
- **Token test** ΓÇö read your CSS variables aloud: do they belong to this product's world, or any project?

---

# After Completing a Task

Always offer to save: "Want me to save these patterns for future sessions?" If yes, write to `.interface-design/system.md`:

- Direction and feel
- Depth strategy (borders/shadows/layered) and spacing base unit
- Hierarchy decisions (type scale ratio, density values, focal pattern)
- Key component patterns ΓÇö add when a component is used 2+ times, is reusable, or has measurements worth remembering (not one-offs or prop variations). Record the values, e.g. `Button primary ΓÇö 36px h ┬╖ 12px 16px pad ┬╖ 6px radius ┬╖ 14px/500`.
- Visual direction notes and selected references when an image pass shaped the design

**Consistency checks.** If system.md defines values, hold to them: spacing on the grid, the declared depth strategy throughout, colors from the palette, documented patterns reused not reinvented. This compounds ΓÇö each save makes future work faster and more consistent.

---

# Commands

- `/interface-design:design-review` ΓÇö strict craft + hierarchy review of a build, with an approval bar; renders before/after when possible
- `/interface-design:design-deslop` ΓÇö fast, diff-scoped pass that strips visual slop from a branch

If a user asks for design status, audit, or pattern extraction in natural language: read `.interface-design/system.md` and summarize it, check UI files against it for drift, or scan for repeated spacing/radius/color/component values and propose a system.md ΓÇö perform the equivalent inline.