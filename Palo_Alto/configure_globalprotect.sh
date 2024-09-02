#!/bin/bash
# Version: 1.0.1
# Description: Checks for global preferences file and populates it with the default portal if needed

# References for this script can be found here
# https://docs.paloaltonetworks.com/globalprotect/10-1/globalprotect-admin/mobile-endpoint-management/manage-the-globalprotect-app-using-jamf/manage-the-globalprotect-app-for-macos-using-jamf-pro/deploy-the-globalprotect-mobile-app-using-jamf

echo_logger() {
    # echo_logger version 1.1
    log_folder="${log_folder:=/private/var/log}"
    /bin/mkdir -p "$log_folder"
    echo -e "$(date +'%Y-%m-%d %T%z') - ${log_prefix:+$log_prefix }${1}" | /usr/bin/tee -a "$log_folder/${log_name:=management.log}"
}

plistbuddy="/usr/libexec/PlistBuddy"
plist="/Library/Preferences/com.paloaltonetworks.GlobalProtect.settings.plist"
gp_gateway="$4"

echo_logger "Checking for existing GlobalProtect preferences"
if [[ -e "$plist" ]]; then
    echo_logger "$($plistbuddy "$plist" -c "print ':Palo Alto Networks:GlobalProtect:PanSetup'")"
else
    echo_logger "No existing preferences found"
fi

echo_logger "Setting GlobalProtect Preferences"
"$plistbuddy" -c "add ':Palo Alto Networks:GlobalProtect:PanSetup:Portal' string $gp_gateway" "$plist"
"$plistbuddy" -c "add ':Palo Alto Networks:GlobalProtect:PanSetup:Prelogon' string 0" "$plist"

echo_logger "$($plistbuddy "$plist" -c "print ':Palo Alto Networks:GlobalProtect:PanSetup'")"

exit 0
