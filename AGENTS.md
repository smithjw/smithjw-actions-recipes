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
2. **`URLDownloaderPython`** — uses the new processor that **does not redownload** on
   re-runs and respects HTTP caching headers. Always pass `download_missing_file:
   '%DOWNLOAD_MISSING_FILE%'`.
3. **`EndOfCheckPhase`** — boundary marker; below this is "we have a new file".
4. **`StopProcessingIf`** — short-circuit when the file is unchanged so we don't waste
   CI minutes. Predicate: `download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%`.
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

## Universal binaries vs separate-arch builds

**Always prefer universal binaries when the vendor publishes them.** A universal `.app`
or `.pkg` runs natively on both Apple Silicon and Intel macs and downloads with one
fetch.

**When the vendor publishes separate `arm64` and `x86_64` artefacts**, the recipe pair
must:

1. **Download recipe** — fetch BOTH artefacts via two separate `URLDownloaderPython`
   steps. Verify the signature on each before continuing.
2. **Package recipe** — produce a single pkg that contains both `.app` bundles in
   `/Applications/` with arch suffixes (`AppName-arm64.app`, `AppName-x86_64.app`),
   plus a `postinstall` script that detects the device's architecture, removes the
   wrong-arch bundle, and renames the right one to `AppName.app`.

**Reference (CLI binary):** `wizcli/wizcli.pkg.recipe.yaml` — multi-arch postinstall
that picks the right binary for `/usr/local/bin/wizcli` based on `arch`.

**Reference (.app bundle, this repo):** `DBeaver/`, `KeePassXC/`, `OBS_Studio/`,
`Figma/`, `Zoom/` (all added 2026-05-07 with the universal multi-arch pattern).

### Multi-arch download skeleton

```yaml
Process:
  - Processor: <SourceInfoProvider>            # GitHubReleasesInfoProvider, etc.
    Arguments:
      asset_regex: <pattern matching arm64 asset>
      ...

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-arm64.dmg'
      # uses %url% from the SourceInfoProvider step

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-x86_64.dmg'
      url: <explicit Intel URL or %url% with re-fetched info>

  - Processor: EndOfCheckPhase

  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier   # arm64
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-arm64.dmg/<App>.app'
      requirement: <full requirement string>

  - Processor: CodeSignatureVerifier   # x86_64
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-x86_64.dmg/<App>.app'
      requirement: <full requirement string — usually identical to arm64>
```

### Multi-arch package skeleton

```yaml
Process:
  - Processor: PkgRootCreator
    Arguments:
      pkgroot: '%RECIPE_CACHE_DIR%/payload'
      pkgdirs:
        Applications: '0755'
        scripts: '0755'

  - Processor: Copier
    Arguments:
      source_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-arm64.dmg/<App>.app'
      destination_path: '%RECIPE_CACHE_DIR%/payload/Applications/<App>-arm64.app'

  - Processor: Copier
    Arguments:
      source_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-x86_64.dmg/<App>.app'
      destination_path: '%RECIPE_CACHE_DIR%/payload/Applications/<App>-x86_64.app'

  - Processor: FileCreator
    Arguments:
      file_path: '%RECIPE_CACHE_DIR%/payload/scripts/postinstall'
      file_mode: '0755'
      file_content: |
        #!/bin/bash
        set -euo pipefail
        if [[ $( /usr/bin/arch ) = arm64* ]]; then
          /bin/rm -rf "/Applications/<App>-x86_64.app"
          /bin/mv "/Applications/<App>-arm64.app" "/Applications/<App>.app"
        else
          /bin/rm -rf "/Applications/<App>-arm64.app"
          /bin/mv "/Applications/<App>-x86_64.app" "/Applications/<App>.app"
        fi
        exit 0

  - Processor: PkgCreator
    Arguments:
      pkg_request:
        id: <bundle.id>
        options: purge_ds_store
        pkgdir: '%RECIPE_CACHE_DIR%'
        pkgname: '%SOFTWARE_TITLE%-%version%'
        pkgroot: '%RECIPE_CACHE_DIR%/payload'
        scripts: '%RECIPE_CACHE_DIR%/payload/scripts'
        version: '%version%'

  - Processor: com.github.smithjw.processors/FriendlyPathDeleter
    Arguments:
      fail_deleter_silently: true
      path_list:
        - '%RECIPE_CACHE_DIR%/payload'
```

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
