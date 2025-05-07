#!/bin/bash

JDK_VERSION="%JDK_VERSION%"
JDK_PLIST="/Library/Java/JavaVirtualMachines/zulu-${JDK_VERSION}.jdk/Contents/Info.plist"
KEY="CFBundleName"

if [[ -f "$JDK_PLIST" ]]; then
    PLIST_KEY=$(/usr/bin/defaults read "${JDK_PLIST}" "${KEY}" 2> /dev/null)
    VERSION=${PLIST_KEY#* }
    RESULT=${VERSION}
else
    RESULT="Not Installed"
fi

if [[ -n "${RESULT}" ]]; then
    /bin/echo "<result>${RESULT}</result>"
fi

exit 0
