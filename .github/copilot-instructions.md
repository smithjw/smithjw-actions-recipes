## Autopkg Recipes
- The following instructions relate to autopkg recipes that end in the extension `.recipe.yaml`
- The 4 main types of recipes that will be contained in this repo are:
  - Download recipes - ending in `download.recipe.yaml`
  - Package recipes - ending in `pkg.recipe.yaml`
  - Jamf recipes - ending in `jamf.recipe.yaml`
- Recipes that are the first in the recipe chain (generally only download recipes) should have 5 required top-level keys separated into 3 sections:
  - `Description`, `Identifier`, & `MinimumVersion`
  - `Input`
  - `Process`
- All other recipe formats that depend on a parent recipe first will have 6 required top-level keys separated into 3 sections:
  - `Description`, `Identifier`, `ParentRecipe`, & `MinimumVersion`
  - `Input`
  - `Process`

### All Recipes
- The `Input` dict should always start with a `NAME` key, followed by a `SOFTWARE_TITLE` key.
- The `NAME` key should always correspond to the name of the application as it appears on disk:
  - Microsoft Teams.app - `NAME: Microsoft Teams`
  - Google Chrome.app - `NAME: Google Chrome`
  - Docker.app - `NAME: Docker`
- The `SOFTWARE_TITLE` key is used to name the resulting packge and for any custom triggers in Jamf recipes.
- It is important that `SOFTWARE_TITLE` does not include any spaces and replaces these with an underscore:
  - Microsoft Teams.app - `SOFTWARE_TITLE: Microsoft_Teams`
  - Google Chrome.app - `SOFTWARE_TITLE: Google_Chrome`
- In cases where the `NAME` of an app is only one word, `SOFTWARE_TITLE` can be set to the `NAME` input - `SOFTWARE_TITLE: '%NAME%'`

### Download recipes
- The final `Processor` of each download recipe should be `CodeSignatureVerifier`
- Immediately following the `URLDownloaderPython` Processor should be an `EndOfCheckPhase` and then `com.github.jgstew.SharedProcessors/StopProcessingIfDownloadUnchanged`
