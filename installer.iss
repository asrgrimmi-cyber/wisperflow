; Wisper — Inno Setup Installer Script
; Produces a single WisperSetup.exe that installs the app properly.
;
; Requirements:
;   1. Build Wisper.exe first: pyinstaller build.spec
;   2. Install Inno Setup: https://jrsoftware.org/isinfo.php
;   3. Compile this script: iscc installer.iss
;
; Output: dist/WisperSetup.exe

[Setup]
AppName=Wisper
AppVersion=1.0.0
AppPublisher=Wisper
AppPublisherURL=https://github.com/wisper
DefaultDirName={autopf}\Wisper
DefaultGroupName=Wisper
UninstallDisplayIcon={app}\Wisper.exe
OutputDir=dist
OutputBaseFilename=WisperSetup
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
WizardStyle=modern

[Files]
; Main executable (built by PyInstaller)
Source: "dist\Wisper.exe"; DestDir: "{app}"; Flags: ignoreversion

; Default config (will be overwritten by first-run wizard)
Source: "config.yaml"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\Wisper"; Filename: "{app}\Wisper.exe"
Name: "{group}\Uninstall Wisper"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\Wisper"; Filename: "{app}\Wisper.exe"

[Run]
; Launch after install
Filename: "{app}\Wisper.exe"; Description: "Launch Wisper"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up config and logs on uninstall
Type: files; Name: "{app}\config.yaml"
Type: files; Name: "{app}\server.log"
Type: dirifempty; Name: "{app}"
