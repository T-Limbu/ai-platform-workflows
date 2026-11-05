# Layout check

Loads each page of an app at 320/360/414/768/1024/1440 px in Chromium and fails on:
sideways scroll, off-screen content, overlapping controls, clipped text, and
must-be-reachable elements that are hidden, covered or missing. Controls under 24px are warnings.

Run from a folder where `playwright` is installed:
`node layout-check.mjs layout-check.config.json [--report-only]`

Config (see `example.config.json`): `baseUrl` (override with `LAYOUT_BASE_URL`), optional `login`
(signs in through the app's API with a seeded local account read from env vars, then seeds localStorage),
`pages`, `mustBeReachable` (selectors that must be visible and tappable, for example main nav links).

Ignore intentional cases with a `data-layout-ignore` attribute or `ignoreSelector`; anything inside a
sideways-scrolling box is skipped automatically.

Rollout: use `--report-only` (or `LAYOUT_REPORT_ONLY=true`) at first, then drop it to block.
Version 1 checks the page as loaded only, not drawers, modals or menus.
