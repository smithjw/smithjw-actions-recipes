# Recipe authoring checklist

A short pre-flight list to run through before declaring a new app's recipes "done".

## Before you start

- [ ] Confirmed we don't already have a folder for this app in our repos (a quick `ls` /
  search of `smithjw-actions-recipes` and `smithjw-recipes`). Don't rely on
  `autopkg search` to dedupe against other people's repos — any external recipe gets
  rewritten to our chain (`URLDownloaderPython` + the two-clause `StopProcessingIf`) anyway.
- [ ] Picked the closest existing chain as a template to copy (same delivery format:
  GitHub `.pkg`, `.dmg` of `.app`, Sparkle, single-arch, universal-with-unsigned-wrapper).
- [ ] Went **direct to the vendor** for the binary/version — not a third-party aggregator
  (Homebrew, MacUpdate). Each hop is a supply-chain trust cost.
- [ ] Picked the arch approach by priority: **true universal** artefact if the vendor ships
  one; otherwise a **single-arch recipe defaulting to arm64** via `ARCHITECTURE` /
  `DOWNLOAD_ARCH`. Do not download-both-and-merge into a wrapper pkg for new recipes.

## Per-app folder

- [ ] Folder is named `<App>` in PascalCase_With_Underscores.
- [ ] `<App>.download.recipe.yaml` exists and validates against
  `smithjw-autopkg-recipe.schema.json`.
- [ ] `<App>.pkg.recipe.yaml` exists (if the source is not already a `.pkg`).
- [ ] `<App>.upload.jamf.recipe.yaml` exists.
- [ ] `<App>.png` icon exists, ~512×512, square, transparent background.

## Per recipe — Identifier

- [ ] `Identifier:` is `com.github.smithjw-actions.<type>.<App>`.
- [ ] `<type>` is one of `download`, `pkg`, `jamf`, or `jamf.upload`.
- [ ] `<App>` matches the folder name and `SOFTWARE_TITLE`.

## Per recipe — Input

- [ ] `NAME:` is the human-readable display string.
- [ ] `SOFTWARE_TITLE:` matches the folder name (no spaces, may include `_`).
- [ ] Download recipes have `DOWNLOAD_MISSING_FILE: null` and
  `BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED: 'False'`.
- [ ] Upload recipes have `CATEGORY`, `PKG_TO_KEEP: '2'`, `PKG_NAME_MATCH:
  '%SOFTWARE_TITLE%-'`.

## Per recipe — Process

- [ ] Source-specific info provider (GitHub / Sparkle / direct URL) is the first step.
- [ ] `URLDownloaderPython` is used (not the legacy `URLDownloader`).
- [ ] `EndOfCheckPhase` is present.
- [ ] `StopProcessingIf` follows `EndOfCheckPhase` with the correct predicate.
- [ ] `CodeSignatureVerifier` runs on the downloaded artefact.
- [ ] Signature requirement uses `OU` (TeamID), not `cdhash`.
- [ ] Output package path is `%RECIPE_CACHE_DIR%/%SOFTWARE_TITLE%-%version%.pkg`.

## Pre-commit

- [ ] `prek run -a` is clean.
- [ ] Recipe runs successfully end-to-end via `autopkg run -vv` on a clean cache.
- [ ] Re-running on an unchanged upstream stops at `StopProcessingIf` (no upload).
- [ ] Resulting `.pkg` matches the expected name: `<SOFTWARE_TITLE>-<version>.pkg`.
- [ ] Resulting `.pkg` is signed by the expected vendor team.

## Gotchas

- [ ] **GitHub release tag with a `/`** (e.g. `releases/0.8`) embeds raw into `%version%`,
  producing a broken download filename like `App-releases/0.8.dmg` and a "can't move file"
  failure. Check the tag format if a download recipe fails that way; strip or rewrite the
  version if needed.
- [ ] **Confirmed the info provider matched the single asset you intended** (read the
  `Matched regex ... among asset(s)` line) — not a helper binary, sig file, or a different
  arch.
- [ ] **Quoted the Team ID** in `subject.OU = "<TeamID>"` — digit-leading IDs fail unquoted
  at runtime even though they lint fine.

## Downstream

- [ ] After merging here, refresh trust info in your downstream override repo:
  `autopkg update-trust-info <Override>.recipe`.
- [ ] Open a PR in the downstream override repo adding the override file(s) for this
  app (e.g. `<App>.upload.jamf.recipe.yaml` plus any environment-specific policies
  you attach in the override) with `ParentRecipeTrustInfo` populated.
