# smithjw-actions-recipes

Contains recipes specifically used within CICD contexts such as GitHub Actions.

Download recipes are tailored to use the newer versions of `URLDownloaderPython` which does not redownload packages if they've already been downloaded in the past.

Additionally, recipes will stop processing if no new file has been downloaded if already present.
