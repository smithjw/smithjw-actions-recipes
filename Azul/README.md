Extension Attribute is using the version number from within the text of `CFBundleName`. This is located at `/Library/Java/JavaVirtualMachines/zulu-${JDK_VERSION}.jdk/Contents/Info.plist`.

Within the pkg recipe (`Azul_Zulu_JDK.pkg.recipe.yaml`), we are grabbing this same version number by extracting it before creating the final package. This also ensure the version number Jamf knows about, will match the EA we are uploading.
