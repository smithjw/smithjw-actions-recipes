# AGENTS.md — smithjw-actions-recipes

This repository hosts AutoPkg parent recipes that downstream override repos consume via
the `autopkg-wrapper` running in GitHub Actions. Recipes here are the **upstream of
truth** — overrides downstream pin them by SHA via `ParentRecipeTrustInfo`.

## Repo layout

```
smithjw-actions-recipes/
├── _archived/                       # Recipes no longer in active use (kept for history)
├── _templates/                      # Jamf policy + smart group XML templates referenced
│                                    #   by the *.jamf.recipe.yaml recipes
│   ├── Policy_Template-Auto-Install.xml
│   ├── Policy_Template-Auto-Update.xml
│   ├── Policy_Template-Custom_Trigger_Only.xml
│   ├── Policy_Template-Self_Service.xml
│   ├── Policy_Template-Utilities*.xml
│   ├── Smart_Group-*.xml
│   └── Static_Group.xml
├── Generic/                         # Generic parent recipes used by other apps
├── Microsoft/
│   └── Microsoft_Package.download.recipe.yaml   # Parent for Microsoft fwlink-based pkgs
├── SharedProcessors/                # Custom processors used by recipes here
│   ├── CacheCleaner.py
│   ├── SharedProcessors.recipe.yaml
│   └── URLDownloaderPython.py
├── <APP_FOLDER>/                    # Per-app folders, named PascalCase_With_Underscores
│   ├── <App>.download.recipe.yaml   # Pulls binary from upstream + verifies signature
│   ├── <App>.pkg.recipe.yaml        # Wraps the downloaded artefact into a .pkg
│   ├── <App>.png                    # Self-Service icon (square, ~512×512)
│   ├── <App>.upload.jamf.recipe.yaml  # Uploads .pkg to Jamf and rotates old packages
│   └── <App>.jamf.recipe.yaml       # (Optional) full Self-Service policy + smart group flow
└── smithjw-autopkg-recipe.schema.json   # JSON schema for editor validation
```

## Recipe naming convention

| Recipe type | Filename | Identifier | Purpose |
|-------------|----------|------------|---------|
| Download | `<App>.download.recipe.yaml` | `com.github.smithjw-actions.download.<App>` | Get the upstream binary, verify its signature, stop early if the artefact is unchanged. |
| Package | `<App>.pkg.recipe.yaml` | `com.github.smithjw-actions.pkg.<App>` | Convert the downloaded artefact into a `.pkg` named `<SOFTWARE_TITLE>-<version>.pkg`. |
| Jamf upload (minimal) | `<App>.upload.jamf.recipe.yaml` | `com.github.smithjw-actions.jamf.upload.<App>` | Upload the package only — for downstream overrides that own their own policy. |
| Jamf full (legacy) | `<App>.jamf.recipe.yaml` | `com.github.smithjw-actions.jamf.<App>` | Upload + create a Self-Service policy from a template. New recipes should prefer the `.upload.` flavour and let downstream overrides own the policy. |

- `<App>` uses **PascalCase_With_Underscores** (e.g. `Microsoft_Edge`, `Mozilla_Firefox`).
  Mirror the folder name.
- `SOFTWARE_TITLE` should match `<App>` exactly (no spaces).
- `NAME` is the human-readable display string ("Microsoft Edge", "Mozilla Firefox").

## Required Input keys

Every download recipe must include:

```yaml
Input:
  NAME: <Display Name>
  SOFTWARE_TITLE: <App>
  DOWNLOAD_MISSING_FILE: null
  BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED: 'False'
```

Other recipes inherit these via `ParentRecipe`.

## Required `Description:` preamble

Every recipe (download / pkg / upload) must lead its `Description:` with a short
context block that captures:

1. **What the recipe does** — one line: "Downloads X", "Packages X", "Uploads X".
2. **The full chain requirement** — the `URLDownloaderPython` processor (this repo's
   `SharedProcessors/`) is what makes the cache idempotent. The recipes only
   short-circuit correctly when the **download → pkg → upload** chain runs in full.
   Pointing an upload recipe directly at a pre-built `.pkg` defeats the cache and
   re-uploads on every CI run.
3. **The per-recipe specifics** — vendor URL / GitHub repo / Sparkle feed / asset
   pattern / arch handling.

Use this template (concatenated into a YAML literal block under `Description:`):

```yaml
Description: |
  Downloads <App> from <source> and produces a verified artefact for downstream
  packaging.

  Run as part of the full download → pkg → upload chain. The `URLDownloaderPython`
  processor (in `SharedProcessors/`) caches by ETag/Last-Modified and the
  `StopProcessingIf download_changed == False` predicate short-circuits the chain
  on no-op re-runs.

  <per-recipe specifics: source URL, asset regex, arch handling, etc.>
```

## Required Process steps

### Download recipe (in order)

1. **Source-specific info provider** — one of:
   - `GitHubReleasesInfoProvider` (most common — open-source apps on GitHub)
   - `SparkleUpdateInfoProvider` (apps with a Sparkle appcast)
   - direct URL via `URLDownloaderPython` argument `url:` (vendor-hosted statics)
2. **`URLDownloaderPython`** — uses the custom processor that **does not redownload** on
   re-runs and respects HTTP caching headers. Always pass `download_missing_file:
   '%DOWNLOAD_MISSING_FILE%'`.

   > **Pending migration to core.** `URLDownloaderPython` here is a fork
   > (`SharedProcessors/URLDownloaderPython.py`) referenced as
   > `com.github.smithjw-actions.processors/URLDownloaderPython`. AutoPkg core now ships a
   > built-in `URLDownloaderPython`, but it lacks the `download_missing_file` input our
   > recipes rely on. Once autopkg/autopkg PR #1056 (adds those inputs/validation) is
   > merged **and in a released AutoPkg**, drop the fork, switch recipes to the core
   > `URLDownloaderPython` (no processor-identifier prefix), and bump `MinimumVersion`
   > accordingly. This happens as the recipes are written back to `autopkg/smithjw-recipes`
   > (namespace `com.github.smithjw-actions.*` → `com.github.smithjw.*`). Until then, keep
   > the fork.
3. **`EndOfCheckPhase`** — boundary marker; below this is "we have a new file".
4. **`StopProcessingIf`** — short-circuit when the file is unchanged so we don't waste
   CI minutes. Predicate: `download_changed == False AND %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED% == False`.
5. **`CodeSignatureVerifier`** — verify the downloaded artefact (`.pkg`, `.app`, or binary).
   Always include this; it's our trust boundary against upstream compromise.

### Package recipe (when source is not already a `.pkg`)

For `.dmg` containing `.app`:
- `AppPkgCreator` with `app_path` pointing to `%RECIPE_CACHE_DIR%/downloads/.../<App>.app`
  and `pkg_path: '%RECIPE_CACHE_DIR%/%SOFTWARE_TITLE%-%version%.pkg'`.

For `.zip`/`.tar` containing `.app`:
- `Unarchiver` to a known path
- `CodeSignatureVerifier` on the extracted app
- `AppPkgCreator` from the extracted location

For Microsoft fwlink `.pkg`:
- See `Microsoft/Microsoft_Package.download.recipe.yaml` — uses `FlatPkgUnpacker` +
  `PkgPayloadUnpacker` + `Versioner` + `PkgCopier` to re-stamp with a friendly name.

## Architecture strategy

Pick the arch approach by this priority. Stop at the first that the vendor supports.

### 1. True universal artefact (preferred)

If the vendor publishes a **single universal** `.app`, `.pkg`, or binary (native on both
Apple silicon and Intel), use it: one download, one verify, no arch inputs. Always prefer
this over anything below.

- If the universal artefact is itself signed, verify it directly (`CodeSignatureVerifier`
  by authority chain or requirement string). **Reference:** `Zoom/` (universal IT pkg).
- If only a *wrapper* is unsigned but it carries a signed universal binary (common for
  GitHub-released CLI pkgs), unpack it (`FlatPkgUnpacker` → `FileFinder '*.pkg/Payload'` →
  `PkgPayloadUnpacker`) and verify the extracted binary — that binary is the trust
  boundary. The `pkg` recipe is then just a `PkgCopier` rename. **Reference:**
  `GitHub_CLI/` (universal `gh` pkg; `lipo -archs` confirms `x86_64 arm64`).

Don't hand-merge two per-arch builds into a pseudo-universal pkg — if the vendor doesn't
ship a true universal artefact, drop to a single-arch recipe (below) instead.

### 2. Single-arch, defaulting to Apple silicon (when there's no universal)

When the vendor ships **separate** `arm64` and `x86_64` artefacts and no universal, build a
**single-arch** recipe that **defaults to arm64** and is switchable via two inputs.
Document the switch in the `Description`. Do **not** download both arches.

Two distinct inputs, because the Jamf-facing name and the vendor's download token often
differ:

- **`ARCHITECTURE`** — names the artefact for Jamf. Always one of `arm64` / `x86_64`.
- **`DOWNLOAD_ARCH`** — matches the vendor's own asset/URL naming (e.g. `arm64`, `x64`,
  `amd64`). Used only in the `asset_regex` / `url` / `re_pattern`.

If the vendor's naming already uses `arm64` / `x86_64`, set `DOWNLOAD_ARCH: '%ARCHITECTURE%'`
and drive both from one value. When they differ (e.g. Intel is `x64` or `amd64`), default
`DOWNLOAD_ARCH: arm64` explicitly and document the Intel pairing.

**References:** `Microsoft_Scout/` (vendor uses `arm64`/`x64`), `GitHub_Copilot/` (vendor
uses `arm64`/`x64`).

```yaml
Input:
  NAME: <App>
  SOFTWARE_TITLE: <App>
  ARCHITECTURE: arm64          # arm64 | x86_64 — names the artefact for Jamf
  DOWNLOAD_ARCH: arm64         # vendor token: arm64 | x64 | amd64 — or '%ARCHITECTURE%'
  INCLUDE_PRERELEASES: null
  DOWNLOAD_MISSING_FILE: null
  BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED: 'False'

Process:
  - Processor: <SourceInfoProvider>            # GitHubReleasesInfoProvider, URLTextSearcher, etc.
    Arguments:
      asset_regex: '<App>-.*-%DOWNLOAD_ARCH%\.dmg$'

  - Processor: com.github.smithjw-actions.processors/URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-%ARCHITECTURE%.dmg'

  - Processor: EndOfCheckPhase

  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == False AND %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED% == False'

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-%ARCHITECTURE%.dmg/<App>.app'
      requirement: <full requirement string>
```

The `pkg` (and any `upload`) recipe carries `ARCHITECTURE: arm64` too and references the
downloaded artefact by `%SOFTWARE_TITLE%-%ARCHITECTURE%.dmg`, so an Intel override just
sets `ARCHITECTURE=x86_64` + `DOWNLOAD_ARCH=x64` on the whole chain.

### 3. Deprecated: download-both-and-merge wrapper pkg

Older recipes download **both** arches and wrap them in a top-level pkg whose `postinstall`
installs only the matching component. **Don't use this for new recipes** — prefer a true
universal artefact (1) or a single-arch default (2). It survives only for maintenance of
existing recipes: `wizcli/`, `DBeaver/`, `KeePassXC/`, `OBS_Studio/`, `Figma/`,
`GitHub_Desktop/`. If one of those vendors starts shipping a universal artefact, migrate it
down to (1).

### Jamf upload recipe (`.upload.jamf.recipe.yaml`)

Standard tail:

```yaml
Process:
  - Processor: com.github.grahampugh.jamf-upload.processors/JamfPackageUploader
    Arguments:
      pkg_category: '%CATEGORY%'
      pkg_info: '%PACKAGE_INFO%'

  - Processor: com.github.grahampugh.recipes.postprocessors/LastRecipeRunResult

  - Processor: StopProcessingIf
    Arguments:
      predicate: '%REMOVE_OLD_PACKAGES% == false'

  - Processor: com.github.grahampugh.jamf-upload.processors/JamfPackageCleaner
    Arguments:
      pkg_name_match: '%PKG_NAME_MATCH%'
      versions_to_keep: '%PKG_TO_KEEP%'
```

Default `PKG_TO_KEEP` is `'2'` (current + previous). `PKG_NAME_MATCH` is
`'%SOFTWARE_TITLE%-'` so the cleaner only deletes our own packages.

## Code-signature verification — non-negotiable

Every `.download.` recipe must verify what it just downloaded. Two flavours:

**By certificate authority chain** (works for `.pkg` files):

```yaml
- Processor: CodeSignatureVerifier
  Arguments:
    expected_authority_names:
      - 'Developer ID Installer: <Vendor> (<TeamID>)'
      - Developer ID Certification Authority
      - Apple Root CA
    input_path: '%pathname%'
```

**By full requirement string** (preferred for `.app` bundles — survives certificate
rotations):

```yaml
- Processor: CodeSignatureVerifier
  Arguments:
    deep_verification: true
    input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%.dmg/<App>.app'
    requirement: identifier "<bundle.id>" and anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and certificate leaf[subject.OU] = <TeamID>
    strict_verification: true
```

Get the `requirement` string by running on a known-good copy:
`codesign -d -r- /path/to/App.app`. Replace `cdhash` references with `OU`-based predicates
to keep them resilient to vendor updates.

**Quote the team ID** in `subject.OU = "<TeamID>"`. The CodeSignatureVerifier parser
treats team IDs that start with a digit (e.g. `2BUA8C4S2C`, `42B6MDKMW8`, `936EB786NH`)
as numeric tokens unless quoted, which causes
`error: invalid or corrupted code requirement(s)`. Always quote, even when the team ID
starts with a letter — it's never wrong to quote.

**Skip `deep_verification`** for apps that bundle Sparkle.framework or similar
third-party update frameworks. Those frameworks carry `com.apple.FinderInfo` xattrs on
header / nib files that fail strict deep-verification on macOS 14+ with
`resource fork, Finder information, or similar detritus not allowed`. Affected apps in
this repo include Brave Browser and OBS Studio. The top-level bundle signature match
against the requirement string is still enforced — the deep-walk is the only thing
disabled.

**Skip `strict_verification`** when the vendor's designated requirement uses an OR
clause (e.g. OBS Studio's
`(certificate leaf[field.1.2.840.113635.100.6.1.9] /* exists */ or … and Team-ID)`).
Strict mode requires the recipe's requirement to match the designated requirement
byte-for-byte; OR clauses can't be re-expressed cleanly. Drop strict mode and use a
simpler `identifier + anchor + Team-ID` predicate.

## Schema validation

Every YAML recipe is validated against `smithjw-autopkg-recipe.schema.json`. Editors with
JSON Schema support (VS Code, Zed, IntelliJ) auto-validate when the schema is associated
with `*.recipe.yaml`. Add this to your `.vscode/settings.json` (workspace-level):

```jsonc
{
  "yaml.schemas": {
    "./smithjw-autopkg-recipe.schema.json": "*.recipe.yaml"
  }
}
```

## Toolchain

`mise.toml` pins:

- `usage` (CLI for shell-task generators)
- `uv` (Python toolchain for the `URLDownloaderPython` shared processor)
- `prek` (pre-commit replacement)

Bootstrap:

```bash
mise install
prek install
```

## Recipe authoring workflow (TL;DR)

1. **Pick a pattern** (see `skills/recipe-writing/SKILL.md` decision tree).
2. **Copy the closest existing folder** as a starting template.
3. **Replace every `<App>` reference** consistently (folder name, filenames, identifiers,
   bundle IDs, signature requirement, NAME, SOFTWARE_TITLE).
4. **Run `autopkg run -vv` locally** (or via the wrapper) to verify the recipe.
5. **Verify the signature requirement string** matches a known-good app from the same
   vendor — never copy a requirement string from a different vendor.
6. **Add a square 512×512 PNG icon** (`<App>.png`) — used by Self-Service.
7. **Validate** via `prek run -a` before committing.

## Commits

- Use Conventional Commits. `feat(<App>): add download/pkg/upload recipes` is the
  canonical message for a new app. Bug fixes: `fix(<App>): ...`. Trust info refreshes:
  `chore(trust): ...`. Repo-wide doc/scaffolding changes: `docs(repo): ...` /
  `chore(repo): ...`.
- Sign-off: `--no-gpg-sign`. The CI pipeline doesn't verify signatures and adding them
  here only complicates downstream PR-driven workflows.
- **Don't commit on behalf of a reviewer.** Leave staged changes for review unless the
  contributor explicitly says "commit".

## Trust info & downstream overrides

This repo is the upstream. Downstream override repos pin each parent recipe by SHA via
`ParentRecipeTrustInfo`. Whenever a recipe here changes, the downstream trust must be
refreshed.

Refresh path (handled in the **downstream override repo**, not here):

```bash
autopkg update-trust-info <Override>.recipe
```

Don't try to update trust info from this repo — it's only valid relative to the override.
