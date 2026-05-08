# Quick-reference: which existing recipe to copy

When starting a new app, copy the closest existing folder. This table maps situations to
templates so you don't have to grep for an example.

| Situation | Template to copy | Notes |
|-----------|------------------|-------|
| GitHub release `.pkg` from one repo, signed by vendor TeamID | `desktoppr/` | Simplest case. |
| GitHub release `.pkg`, multiple variants (essentials/suite) | `Mac_Admins_Nudge/` | Uses `PACKAGE_PREFIX` Input to switch. |
| GitHub release `.pkg` named exactly `<App>-<version>.pkg` | `Privileges/` | No need for an extra `pkg` recipe. |
| GitHub release `.dmg` with `.app` inside, ARM64-only asset | `Bruno/` | Uses `asset_regex: .*arm64_mac.dmg$`. |
| GitHub release `.app.zip` | `Maccy/` | Uses `Unarchiver` between download and signature check. |
| Vendor URL (no GitHub) `.dmg` with `.app` | `Microsoft_Visual_Studio_Code/` | Direct `url:` argument. |
| Microsoft fwlink `.pkg` | `Microsoft_Edge/` | Inherits from `Microsoft/Microsoft_Package.download.recipe.yaml`. |
| Sparkle feed `.dmg` | `Royal_TSX/` | Add user-agent override only if vendor blocks defaults. |
| Sparkle feed with `http://` URL needing https | `Suitcase_Fusion/` | Has a `FindAndReplace` step. |
| CLI binary, multi-arch | `wizcli/` | Custom `WizVersionExtractor` + `postinstall` script. |
| Java JDK / runtime | `Amazon_Corretto/` | Uses Azul / Corretto-style downloaders. |
| JetBrains IDE | `JetBrains/` | Family of recipes sharing patterns. |
| Adobe app from Creative Cloud (deferred) | _none yet_ | Adobe IPC server packaging — out of scope for parent recipes. |
| Tableau / commercial Mac apps with non-standard installers | `Tableau/` | Each has its own quirks. |

## Identifier prefix cheat sheet

```
com.github.smithjw-actions.download.<App>          — *.download.recipe.yaml
com.github.smithjw-actions.pkg.<App>               — *.pkg.recipe.yaml
com.github.smithjw-actions.jamf.<App>              — *.jamf.recipe.yaml (full SS flow)
com.github.smithjw-actions.jamf.upload.<App>       — *.upload.jamf.recipe.yaml (upload-only)
```

## Common processors used in this repo

| Processor | When to use |
|-----------|-------------|
| `GitHubReleasesInfoProvider` | App is on GitHub Releases. |
| `SparkleUpdateInfoProvider` | App has a Sparkle/AppCast XML feed. |
| `URLDownloaderPython` (custom) | **Always** use this over the legacy `URLDownloader`. Resumable, respects HTTP cache. |
| `EndOfCheckPhase` | Marks "we have a fresh artefact"; required between download and stop predicate. |
| `StopProcessingIf` | Short-circuits when upstream is unchanged. |
| `CodeSignatureVerifier` | Verifies upstream artefact is signed by the expected vendor. |
| `Unarchiver` | Required for `.zip` / `.tar.gz` archives. |
| `AppPkgCreator` | Wrap an `.app` into a `.pkg`. |
| `FlatPkgUnpacker` + `PkgPayloadUnpacker` | Unpack a flat `.pkg` to read the embedded `.app`'s Info.plist. |
| `Versioner` | Read `CFBundleShortVersionString` from a known plist. |
| `PkgCopier` | Re-stamp a pkg with a friendly name (used for Microsoft fwlinks). |
| `PkgRootCreator` + `PkgCreator` | Build a fresh pkg from scratch (CLI binaries). |
| `JamfPackageUploader` (graham-pugh) | Upload to Jamf Pro. |
| `JamfPackageCleaner` (graham-pugh) | Rotate old packages out. |
| `LastRecipeRunResult` (graham-pugh) | Capture output for the autopkg-wrapper. |
| `FriendlyPathDeleter` (custom) | Cleanup intermediate caches without failing on missing paths. |

## Signature requirement string templates

For most well-behaved app vendors the requirement looks like:

```
identifier "<bundle.id>"
  and anchor apple generic
  and certificate 1[field.1.2.840.113635.100.6.2.6] /* exists */
  and certificate leaf[field.1.2.840.113635.100.6.1.13] /* exists */
  and certificate leaf[subject.OU] = "<TeamID>"
```

(Concatenated to one line in the YAML — `requirement:` is a string.)

**Quote the team ID.** Team IDs that begin with a digit (`2BUA8C4S2C`,
`42B6MDKMW8`, `936EB786NH`, etc.) need quoting or the parser rejects them.
Letter-leading IDs work either way; quote them anyway for consistency.

### When the vendor signs with a different leaf cert OID

Some vendors (Apple, certain enterprise apps) use `field.1.2.840.113635.100.6.1.9`
instead of `100.6.1.13`. Generate the correct requirement once with `codesign -d -r-`
and reuse exactly.

### When a single bundle ID isn't unique

If a vendor signs multiple apps with the same bundle ID prefix (e.g. JetBrains
products), match more strictly:

```
identifier = "<bundle.id>"   # exact, not "starts with"
```
