# Recipes to add

## Done — original list

- [x] [Mac Admins Python](https://github.com/macadmins/python)
- [x] [Nudge](https://github.com/macadmins/nudge)
- [x] [desktoppr](https://github.com/scriptingosx/desktoppr)
- [x] [Support App](https://github.com/root3nl/SupportApp)
- [x] [Privileges](https://github.com/SAP/macOS-enterprise-privileges)
- [x] [dockutil](https://github.com/kcrawford/dockutil)
- [x] [Microsoft Company Portal](https://github.com/autopkg/smithjw-recipes/blob/master/Microsoft/Microsoft_Company_Portal.jamf.recipe.yaml)
- [x] [Microsoft Edge](https://github.com/smithjw/smithjw-actions-recipes/blob/main/Microsoft_Edge/Microsoft_Edge.jamf.recipe.yaml)
- [x] [Microsoft Teams](https://github.com/autopkg/smithjw-recipes/blob/master/Microsoft/Microsoft_Teams.jamf.recipe.yaml)

## App Installer migration — Tier 1 (added 2026-05-07)

These are migrations from Jamf App Installers (JAI) to AutoPkg-driven uploads. See
`_platform/planning/20260507-app-installer-recipes-and-cleanup/` for context.

- [x] [swiftDialog](https://github.com/swiftDialog/swiftDialog)
- [x] [Sourcetree](https://www.sourcetreeapp.com/)
- [x] [GitHub Desktop](https://desktop.github.com/)
- [x] [Rectangle](https://github.com/rxhanson/Rectangle)
- [x] [draw.io](https://github.com/jgraph/drawio-desktop)
- [x] [Figma](https://www.figma.com/downloads/)
- [x] [Keka](https://www.keka.io/)
- [x] [Slack](https://slack.com/downloads/mac)
- [x] [Zoom (IT Installer)](https://zoom.us/download#client_4meeting)
- [x] [1Password](https://1password.com/downloads/mac/)
- [x] [Brave Browser](https://brave.com/download/)
- [x] [Obsidian](https://github.com/obsidianmd/obsidian-releases)
- [x] [Sublime Text](https://www.sublimetext.com/download)
- [x] [KeePassXC](https://keepassxc.org/download/)
- [x] [Ghostty](https://github.com/ghostty-org/ghostty)
- [x] [Ollama](https://ollama.com/download)
- [x] [DBeaver](https://dbeaver.io/download/)
- [x] [OBS Studio](https://github.com/obsproject/obs-studio)
- [x] [Suspicious Package](https://www.mothersruin.com/software/SuspiciousPackage/)

## App Installer migration — Tier 2 (pending)

Build during follow-up sessions. Some require Microsoft fwlink lookups, vendor auth, or
extra packaging steps.

- [ ] Microsoft PowerShell (Microsoft fwlink)
- [ ] Microsoft OneDrive (Microsoft fwlink)
- [ ] iMazing Profile Editor
- [ ] Jamf Composer (private download — needs auth)
- [ ] Omnissa Horizon Client (vendor login wall)
- [ ] Citrix Workspace
- [ ] GitKraken
- [ ] Sketch
- [ ] Spotify
- [ ] The Unarchiver (App Store distribution; may stay JAI)
- [ ] Cursor
- [ ] Insomnia ([Kong/insomnia](https://github.com/Kong/insomnia))
- [ ] Karabiner-Elements ([pqrs-org/Karabiner-Elements](https://github.com/pqrs-org/Karabiner-Elements))
- [ ] TeX Live Utility ([amaxwell/tlutility](https://github.com/amaxwell/tlutility))
- [ ] BibDesk (sourceforge)
- [ ] MongoDB Compass
- [ ] Adobe Creative Cloud (launcher only — not the individual apps)
- [ ] Proxyman
- [ ] Zed
- [ ] IINA ([iina/iina](https://github.com/iina/iina))
- [ ] Alfred
- [ ] Arc Browser
- [ ] Beyond Compare
- [ ] Webex
- [ ] Adobe Acrobat Reader DC Continuous
- [ ] Google Web Designer
- [ ] Podman Desktop ([podman-desktop/podman-desktop](https://github.com/podman-desktop/podman-desktop))
- [ ] GIMP

## App Installer migration — out of scope

These will not get parent recipes here (see plan doc for rationale):

- Adobe Creative Cloud individual apps (Photoshop / Illustrator / 19 SKUs) — require
  Adobe IPC server packaging.
- VMware Fusion 13 — commercial license; needs license workflow.
- Microsoft Visual Studio 2022 (Mac) — discontinued, retire instead.
