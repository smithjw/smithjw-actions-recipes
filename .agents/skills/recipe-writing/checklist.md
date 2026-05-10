# Recipe authoring checklist

A short pre-flight list to run through before declaring a new app's recipes "done".

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

## Downstream

- [ ] After merging here, refresh trust info in your downstream override repo:
  `autopkg update-trust-info <Override>.recipe`.
- [ ] Open a PR in the downstream override repo adding the override file(s) for this
  app (e.g. `<App>.upload.jamf.recipe.yaml` plus any environment-specific policies
  you attach in the override) with `ParentRecipeTrustInfo` populated.
