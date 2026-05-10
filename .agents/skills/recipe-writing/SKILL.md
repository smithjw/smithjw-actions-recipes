# Skill: Writing AutoPkg recipes for smithjw-actions-recipes

## When to load this skill

Use this skill when adding a new app's recipes to this repo, refactoring an existing
recipe, or refreshing a code-signature requirement string. It expects a downstream
override repo to consume the parent recipes you produce here.

## What you'll produce

For each app, three YAML recipes plus an icon:

```
<App>/
├── <App>.download.recipe.yaml      # Get artefact + verify signature
├── <App>.pkg.recipe.yaml           # Wrap into <App>-<version>.pkg
├── <App>.upload.jamf.recipe.yaml   # Upload + clean old packages
└── <App>.png                       # Square 512×512 Self-Service icon
```

The `.upload.jamf` flavour is preferred over the legacy full `.jamf.recipe.yaml` —
downstream overrides own the policy and smart-group lifecycle, so the parent here only
needs to upload the package.

## Decision tree — pick the right pattern

```
What kind of artefact does the vendor publish?
├── A signed .pkg via GitHub Releases       → Pattern A (e.g. desktoppr, Privileges, Nudge)
├── A signed .dmg containing a .app
│   ├── via GitHub Releases                 → Pattern B (e.g. Bruno)
│   └── via direct vendor URL               → Pattern C (e.g. Visual Studio Code)
├── A signed .zip / .tar.gz of a .app       → Pattern D (e.g. Maccy)
├── A Microsoft fwlink to a .pkg            → Pattern E (use Microsoft_Package parent)
├── A Sparkle/AppCast feed                  → Pattern F (e.g. Royal TSX, Suitcase Fusion)
├── Universal binary in a single artefact   → use any of A–F above; one URL, one verify
├── Separate arm64 + x86_64 artefacts       → Pattern H (multi-arch — DBeaver, OBS, etc.)
└── A standalone unsigned binary            → Pattern G (e.g. wizcli — multi-arch CLI)
```

If two patterns could apply, prefer the most stable one in this order:
**A > B > C > D > E > F > H > G** (lower-numbered = simpler signature lifecycle).

**Rule:** always prefer a single universal artefact when the vendor publishes one. Drop
to Pattern H only when arm64 and x86_64 ship as distinct files.

## Pattern A — GitHub release `.pkg`

The vendor ships a signed `.pkg` directly on GitHub Releases. No `pkg` recipe needed
beyond a thin rename — the upload recipe can `ParentRecipe` the download directly if
you don't need to rename or re-stamp.

**Skeleton (`download`):**

```yaml
Description: ''
Identifier: com.github.smithjw-actions.download.<App>
MinimumVersion: '2.9'

Input:
  NAME: <App>
  SOFTWARE_TITLE: <App>
  INCLUDE_PRERELEASES: null
  DOWNLOAD_MISSING_FILE: null
  BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED: 'False'

Process:
  - Processor: GitHubReleasesInfoProvider
    Arguments:
      asset_regex: '<regex matching the .pkg asset>'
      github_repo: <owner>/<repo>
      include_prereleases: '%INCLUDE_PRERELEASES%'

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-%version%.pkg'

  - Processor: EndOfCheckPhase

  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier
    Arguments:
      expected_authority_names:
        - 'Developer ID Installer: <Vendor> (<TeamID>)'
        - Developer ID Certification Authority
        - Apple Root CA
      input_path: '%pathname%'
```

**Skeleton (`pkg`)** — minimal, just renames:

```yaml
Description: Renames the upstream pkg to <SOFTWARE_TITLE>-<version>.pkg.
Identifier: com.github.smithjw-actions.pkg.<App>
ParentRecipe: com.github.smithjw-actions.download.<App>
MinimumVersion: '2.9'

Input:
  NAME: <App>
  SOFTWARE_TITLE: <App>

Process:
  - Processor: PkgCopier
    Arguments:
      pkg_path: '%RECIPE_CACHE_DIR%/%SOFTWARE_TITLE%-%version%.pkg'
      source_pkg: '%pathname%'
```

If the upstream filename already matches `<SOFTWARE_TITLE>-<version>.pkg`, you can omit
the `pkg` recipe and have the upload recipe parent the download directly.

**Reference recipes:** `desktoppr/`, `Privileges/`, `Mac_Admins_Nudge/`.

## Pattern B — GitHub release `.dmg` containing `.app`

**Skeleton (`download`):**

```yaml
Description: |
  Downloads the most recent signed release pkg of <App> from GitHub.

  In order to get the latest pre-release, set INCLUDE_PRERELEASES to a non-empty string.
Identifier: com.github.smithjw-actions.download.<App>
MinimumVersion: '2.9'

Input:
  NAME: <App>
  SOFTWARE_TITLE: '%NAME%'
  INCLUDE_PRERELEASES: 'True'
  DOWNLOAD_MISSING_FILE: null
  BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED: 'False'

Process:
  - Processor: GitHubReleasesInfoProvider
    Arguments:
      asset_regex: <regex matching the .dmg asset>
      github_repo: <owner>/<repo>
      include_prereleases: '%INCLUDE_PRERELEASES%'

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%.dmg'

  - Processor: EndOfCheckPhase

  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier
    Arguments:
      deep_verification: true
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%.dmg/<App>.app'
      requirement: identifier "<bundle.id>" and anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and certificate leaf[subject.OU] = <TeamID>
      strict_verification: true
```

**Skeleton (`pkg`):**

```yaml
Description: Wraps the downloaded <App>.app into an installer pkg.
Identifier: com.github.smithjw-actions.pkg.<App>
ParentRecipe: com.github.smithjw-actions.download.<App>
MinimumVersion: '2.9'

Input:
  NAME: <App>
  SOFTWARE_TITLE: '%NAME%'

Process:
  - Processor: AppPkgCreator
    Arguments:
      app_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%.dmg/<App>.app'
      pkg_path: '%RECIPE_CACHE_DIR%/%SOFTWARE_TITLE%-%version%.pkg'
```

**Reference recipes:** `Bruno/`.

## Pattern C — Direct vendor URL `.dmg`

Same as Pattern B but no `GitHubReleasesInfoProvider`. The `URLDownloaderPython` step
takes a `url:` argument directly.

**Skeleton (`download`):**

```yaml
Process:
  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%.dmg'
      url: '<vendor download URL>'

  - Processor: EndOfCheckPhase
  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%.dmg/<App>.app'
      requirement: <full requirement string>
```

**Reference recipe:** `Microsoft_Visual_Studio_Code/`.

## Pattern D — `.zip` / `.tar.gz` of `.app`

Add an `Unarchiver` step after the download, then verify the signature on the extracted
`.app`, then `AppPkgCreator` from the extracted location.

**Reference recipe:** `Maccy/`.

## Pattern E — Microsoft fwlink `.pkg`

Microsoft hosts pkgs behind `https://go.microsoft.com/fwlink/?linkid=<PRODUCT_ID>`. The
`Microsoft/Microsoft_Package.download.recipe.yaml` parent handles the download +
signature verification. Your child `pkg` recipe unpacks the flat pkg, finds the embedded
component, extracts the version from the bundled app's `Info.plist`, then re-stamps the
pkg with `<SOFTWARE_TITLE>-<version>.pkg`.

**Steps:**

1. Find the Microsoft `linkid=` for the product. Some common ones:
   - Microsoft Edge: `2093504`
   - Company Portal: `853070`
   - Microsoft Defender: `2097502`
   - Microsoft Teams: `2249065`
2. Find the bundle ID and the embedded `*-Component.pkg` filename pattern.
3. Copy `Microsoft_Edge/Microsoft_Edge.pkg.recipe.yaml` and adjust:
   - `Identifier`
   - `NAME`, `SOFTWARE_TITLE`
   - `PRODUCT_ID`
   - `FileFinder.pattern` (the inner `*-Component.pkg` name)
   - `Versioner.input_plist_path` (the `.app` Info.plist path inside the payload)

**Reference recipes:** `Microsoft_Edge/`, `Microsoft_Company_Portal/`,
`Microsoft_Defender/`.

## Pattern F — Sparkle / AppCast feed

The vendor publishes a Sparkle update feed. `SparkleUpdateInfoProvider` parses the feed
to find the latest URL and version.

**Skeleton (`download`):**

```yaml
Process:
  - Processor: SparkleUpdateInfoProvider
    Arguments:
      appcast_url: <feed URL>
      # Some feeds reject default user agents; spoof curl if needed:
      # appcast_request_headers:
      #   user-agent: 'curl/8.7.1'

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%.dmg'   # or .zip / .pkg as appropriate

  - Processor: EndOfCheckPhase
  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: '%pathname%/<App>.app'
      requirement: <full requirement string>
```

If the Sparkle feed gives an `http://` URL when `https://` works fine, add a
`FindAndReplace` step (see `Suitcase_Fusion/` for an example) to upgrade the URL before
download.

**Reference recipes:** `Royal_TSX/`, `Suitcase_Fusion/`, `Principle/`.

## Pattern H — Multi-arch `.app` bundle (separate arm64 + x86_64)

Use when the vendor publishes architecture-specific `.dmg` / `.zip` / `.pkg` files and
no universal artefact exists. The recipe pulls both and verifies both. The package
recipe uses `AppPkgCreator` to build separate arm64 and x86_64 component pkgs,
then uses `PkgCreator` for a top-level wrapper pkg whose `postinstall` runs only
the matching component pkg.

**Skeleton (`download` — two URLs in one recipe):**

```yaml
Process:
  - Processor: GitHubReleasesInfoProvider     # or vendor URL / Sparkle / etc.
    Arguments:
      asset_regex: '<App>.*-arm64\.dmg$'
      github_repo: <owner>/<repo>

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-arm64.dmg'
      # uses %url% from GitHubReleasesInfoProvider

  - Processor: URLDownloaderPython
    Arguments:
      download_missing_file: '%DOWNLOAD_MISSING_FILE%'
      filename: '%SOFTWARE_TITLE%-x86_64.dmg'
      url: <explicit Intel URL or use a second InfoProvider step>

  - Processor: EndOfCheckPhase
  - Processor: StopProcessingIf
    Arguments:
      predicate: 'download_changed == %BYPASS_STOP_PROCESSING_IF_DOWNLOAD_UNCHANGED%'

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-arm64.dmg/<App>.app'
      requirement: <full requirement string>

  - Processor: CodeSignatureVerifier
    Arguments:
      input_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-x86_64.dmg/<App>.app'
      requirement: <usually the same string as arm64>
```

**Skeleton (`pkg`):**

```yaml
Process:
  - Processor: PkgRootCreator
    Arguments:
      pkgroot: '%RECIPE_CACHE_DIR%/wrapper'
      pkgdirs:
        pkgroot: '0755'
        scripts: '0755'

  - Processor: AppPkgCreator
    Arguments:
      app_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-arm64.dmg/<App>.app'
      force_pkg_build: true
      pkg_path: '%RECIPE_CACHE_DIR%/wrapper/scripts/%SOFTWARE_TITLE%-arm64.pkg'

  - Processor: AppPkgCreator
    Arguments:
      app_path: '%RECIPE_CACHE_DIR%/downloads/%SOFTWARE_TITLE%-x86_64.dmg/<App>.app'
      force_pkg_build: true
      pkg_path: '%RECIPE_CACHE_DIR%/wrapper/scripts/%SOFTWARE_TITLE%-x86_64.pkg'

  - Processor: FileCreator
    Arguments:
      file_path: '%RECIPE_CACHE_DIR%/wrapper/scripts/postinstall'
      file_mode: '0755'
      file_content: |
        #!/bin/bash
        set -euo pipefail
        if [[ $( /usr/bin/arch ) = arm64* ]]; then
          /usr/sbin/installer -pkg "%SOFTWARE_TITLE%-arm64.pkg" -target "$3"
        else
          /usr/sbin/installer -pkg "%SOFTWARE_TITLE%-x86_64.pkg" -target "$3"
        fi
        exit 0

  - Processor: PkgCreator
    Arguments:
      pkg_request:
        id: <bundle.id>
        options: purge_ds_store
        pkgdir: '%RECIPE_CACHE_DIR%'
        pkgname: '%SOFTWARE_TITLE%-%version%'
        pkgroot: '%RECIPE_CACHE_DIR%/wrapper/pkgroot'
        scripts: '%RECIPE_CACHE_DIR%/wrapper/scripts'
        version: '%version%'

  - Processor: com.github.smithjw.processors/FriendlyPathDeleter
    Arguments:
      fail_deleter_silently: true
      path_list:
        - '%RECIPE_CACHE_DIR%/wrapper'
```

**Reference recipes:** `DBeaver/`, `KeePassXC/`, `OBS_Studio/`, `Figma/`, `Zoom/`.

## Pattern G — Standalone binary (multi-arch)

For CLI tools or daemons published as raw binaries.

1. Download both `arm64` and `x86_64` variants with separate `URLDownloaderPython` steps
   (each with a distinct `filename:`).
2. Verify each binary's signature.
3. In the `pkg` recipe, use `PkgRootCreator`, `Copier` (per arch), `FileCreator` for a
   `postinstall` script that picks the right binary at install time, then `PkgCreator`.

**Reference recipe:** `wizcli/`.

## How to find each piece of metadata

### Bundle identifier

```bash
defaults read /path/to/App.app/Contents/Info.plist CFBundleIdentifier
```

### Code-signing requirement string

```bash
codesign -d -r- /path/to/App.app 2>&1 | grep "designated"
```

Strip the `designated => ` prefix. **Always replace `cdhash` predicates with `OU`-based
predicates** so the requirement survives version updates.

**Always quote the team ID** in `subject.OU = "<TeamID>"`. Team IDs starting with a digit
fail the requirement parser otherwise. Quoting also costs nothing for letter-leading IDs.

Good (resilient):
```
identifier "com.example.App" and anchor apple generic and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */ and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */ and certificate leaf[subject.OU] = "ABCDE12345"
```

Bad (breaks every release):
```
identifier "com.example.App" and anchor apple generic and certificate leaf = H"<sha1>" and ...
```

### Team ID

It's the `OU` field in the cert chain — visible in the `codesign` output above. Also
visible from:

```bash
codesign -dv /path/to/App.app 2>&1 | grep "TeamIdentifier"
```

### Microsoft `PRODUCT_ID`

Visit `https://docs.microsoft.com/en-us/officeupdates/macupdates#download-links`. The
product ID is the trailing digits in `https://go.microsoft.com/fwlink/?linkid=<digits>`.

### GitHub `asset_regex`

Inspect releases manually:

```bash
gh release view --repo <owner>/<repo> --json assets --jq '.assets[].name'
```

Pick a regex that matches **only** the macOS asset (and the architecture you want).
Common patterns:

| Goal | Regex |
|------|-------|
| ARM64 universal `.dmg` | `.*[Aa]rm64.*\.dmg$` |
| Universal `.pkg` | `<App>.*\.pkg$` |
| `.app.zip` | `<App>\.app\.zip$` |
| Signed Apple-silicon DMG | `.*arm64_mac\.dmg$` |

## Verification before committing

1. **Run the recipe** locally:
   ```bash
   autopkg run -vv <App>.upload.jamf.recipe.yaml \
       --override-dir=/path/to/test-overrides \
       --search-dir=$(pwd)
   ```
2. **Check the package**: `pkgutil --check-signature ~/Library/AutoPkg/Cache/.../*.pkg`.
3. **Verify the resulting Jamf package** is named `<SOFTWARE_TITLE>-<version>.pkg`.
4. **Validate YAML schema**: `prek run -a` (will catch most schema mistakes).
5. **Test the cleaner** runs once on a second invocation by lowering `PKG_TO_KEEP` to
   `'1'` temporarily.

## Anti-patterns to avoid

- **Don't** use absolute paths in `app_path` or `input_path` — always use
  `%RECIPE_CACHE_DIR%`.
- **Don't** use `cdhash` in `CodeSignatureVerifier.requirement` — they break on every
  vendor release.
- **Don't** forget the `EndOfCheckPhase + StopProcessingIf` pair — without it, the
  recipe runs the upload steps every time even when the binary is unchanged.
- **Don't** copy a different vendor's signature requirement string. Always derive from
  a known-good copy of the actual app.
- **Don't** leave team IDs unquoted in the requirement string. The CodeSignatureVerifier
  parser produces `invalid or corrupted code requirement(s)` for digit-leading IDs
  (e.g. `2BUA8C4S2C`). Always wrap in double-quotes: `subject.OU] = "<TeamID>"`.
- **Don't** enable `deep_verification: true` on apps that bundle Sparkle.framework or
  similar third-party frameworks (Brave, OBS, many Chromium-based browsers). Those
  frameworks ship with `com.apple.FinderInfo` xattrs on header / nib files that fail
  strict deep verification on macOS 14+. The top-level bundle requirement match is
  still enforced — that's enough.
- **Don't** use `strict_verification: true` with an OR-clause designated requirement
  (e.g. OBS). Strict mode requires the recipe's requirement to match the designated
  requirement byte-for-byte; the OR can't be re-expressed cleanly. Drop strict mode
  and use a simpler `identifier + anchor + Team-ID` predicate instead.
- **Don't** name a `<App>` folder differently from the `SOFTWARE_TITLE`. They must
  match for the cleaner regex (`%PKG_NAME_MATCH%`) to work.
- **Don't** add a Sparkle feed user-agent override unless you've actually seen the
  vendor reject the default UA. It causes silent breakage if the vendor decides to
  block curl in future.
- **Don't** commit until asked. Push the branch only after the user reviews.

## Adding the icon

1. Source the icon from the official vendor press kit / website. Avoid third-party icon
   sites — they're often out of date.
2. Render at 512×512 PNG with transparent background.
3. Save as `<App>.png` next to the recipes.
4. Re-use existing icons where the vendor has multiple products that look identical
   (e.g. multiple JetBrains IDEs may share a theme but each has a unique product icon).

## Common edge cases

### App version key is non-standard

Some apps use `CFBundleVersion` instead of `CFBundleShortVersionString`. Set
`VERSION_TYPE` accordingly in the `pkg` recipe `Input:` block. Default is
`CFBundleShortVersionString`.

### App is named differently inside vs outside the dmg

Use the actual filename inside the DMG mount in the `app_path` / `input_path` — that
will be what `hdiutil` mounts. If the DMG mounts as `App Foo` but the bundle is
`Foo.app`, your path is `%RECIPE_CACHE_DIR%/downloads/<DMG>/Foo.app`.

### Vendor renames the asset between releases

If the regex stops matching, `GitHubReleasesInfoProvider` fails with "no matching
asset". Pick a more permissive regex (e.g. drop a version number that's now embedded in
the filename).

### Two arches in one DMG

If the vendor publishes `arm64_mac.dmg` and `x86_64_mac.dmg` but they're functionally
identical (universal binary inside), pick the `arm64` one — Apple Silicon is the modern
default.

### Universal binary

If the upstream is already a universal binary, no special handling needed — verify
signature once on the bundle and you're done.
