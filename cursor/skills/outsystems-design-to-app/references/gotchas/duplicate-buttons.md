# Duplicate primary actions on one screen

**The trap:** a screen ends up with two primary-action buttons doing the same thing (e.g. a "Sign In" and a "Secure Login", both navigating to the dashboard). The user sees two overlapping, redundant buttons.

**Why it happens:** the source shows a primary button, and the anatomy also specifies one for the same action, so both get built. Or the source renders an action as a plain `<button>`/link and the anatomy models a second Button for the same intent without reconciling.

## What this means for the anatomy

- **One primary action per screen = one widget = one wired event.** When you author the anatomy, model each action ONCE. If the source shows a "Sign In" button, put a single Button node for it (wired to the login action); don't also add a separate "Login/Submit" Button.
- Common duplicate spots: login screens (Sign In + Submit), forms (Submit + Save), search bars (search + Apply filter), card actions ("View details" link + "Open" button).
- If the source renders an action as a link but it behaves like a primary action, model it as one Button, not both a Link and a Button.

## How to detect during source inspection

For each screen, list the source's primary-action buttons and confirm the anatomy has exactly one node per distinct action, with no second node sharing the same label/target.

```bash
grep -nE '<button[^>]*>(Sign In|Login|Submit|Save|Continue|Next|Apply|Search)' source.html
```

## How to prevent (what the anatomy states)

> *"One primary action per screen. Model each action as a single Button node wired to its screen action; do not author a second Button (or a Link + Button) for the same label/target."*

## Field-test evidence

APP1387 (2026-06-02): a login page rendered TWO buttons, a "Sign In" and a separately-authored "Secure Login", both targeting the dashboard.

## Attribution

- [`claude-oml-tool/oml-tool/skills/odc/validated/duplicate-primary-action.md`](https://github.com/OutSystems/claude-oml-tool/blob/main/oml-tool/skills/odc/validated/duplicate-primary-action.md), validated 2026-06-02 (APP1387)

> Note: reframed from `claude-oml-tool`'s chunk flow (chunk button + authored Button) to "model each primary action once in the anatomy."
