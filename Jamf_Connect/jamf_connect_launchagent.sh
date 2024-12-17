#!/bin/bash

launchagent_dir="/Library/LaunchAgents"

cat << EOF > "${launchagent_dir}/com.jamf.connnect.plist"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>KeepAlive</key>
        <true/>
        <key>Label</key>
        <string>com.jamf.connect</string>
        <key>LimitLoadToSessionType</key>
        <array>
            <string>Aqua</string>
        </array>
        <key>Program</key>
        <string>/Applications/Jamf Connect.app/Contents/MacOS/Jamf Connect</string>
        <key>RunAtLoad</key>
        <true/>
    </dict>
</plist>
EOF

chown root:wheel "${launchagent_dir}/com.jamf.connnect.plist"

exit 0
