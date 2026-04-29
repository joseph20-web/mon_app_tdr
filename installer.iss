#define AppName "TDR Payroll"
#define AppVersion "1.0.0"
#define AppPublisher "TDR Payroll"
#define AppExeName "launcher.exe"

[Setup]
AppId={{8B87AB40-AE78-4F2D-81C7-79A347C4CF93}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=installer_output
OutputBaseFilename=TDRPayroll_Setup_{#AppVersion}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
SetupIconFile=assets\app.ico

[Tasks]
Name: "desktopicon"; Description: "Creer un raccourci sur le Bureau"; GroupDescription: "Raccourcis:"

[Files]
Source: "dist\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
Name: "{app}\logs"

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Lancer {#AppName}"; Flags: nowait postinstall skipifsilent

; Signature numerique (activer quand certificat disponible)
; SignTool=mycodesign signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f "C:\certs\tdr-payroll.pfx" /p "{#MySignPassword}" $f
