; Inno Setup script — builds UdiFy-Setup.exe, a proper Windows installer.
;
; Installs into a per-user location (no admin rights required, no UAC
; prompt), so the app's SQLite DB/diagnostics/.env/credentials — all
; resolved next to the .exe by src/config/settings.py's PROJECT_ROOT
; (frozen-build fix, 2026-09-26) — land somewhere genuinely user-
; writable. Installing to Program Files would need admin elevation just
; to write the first-run database, for no benefit on a single-user
; school desktop tool.
;
; Packages installer-onefile.spec's single-file UdiFy.exe (built with
; `pyinstaller installer-onefile.spec` first) — build that before
; compiling this script.
;
; Build with: ISCC.exe installer.iss
; Output: dist_installer\UdiFy-Setup.exe

#define MyAppName "UdiFy"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Satyam Stars International School"
#define MyAppExeName "UdiFy.exe"

[Setup]
AppId={{B4B6E4F0-6C4A-4B9E-9F1A-9C1E2E9C3A21}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist_installer
OutputBaseFilename=UdiFy-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "UdiFy.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: ".env.example"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName} now"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; The DB/diagnostics/.env are real school data, not build artifacts —
; never silently delete them on uninstall. Uninstalling removes only
; the program itself; data stays until the user removes it by hand.
