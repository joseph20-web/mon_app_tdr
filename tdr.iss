[Setup]
AppName=TDR Payroll
AppVersion=1.0.0
DefaultDirName={autopf}\TDR Payroll
DefaultGroupName=TDR Payroll
OutputDir=installer_output
OutputBaseFilename=TDRPayroll_Setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\launcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\TDR Payroll"; Filename: "{app}\launcher.exe"
Name: "{commondesktop}\TDR Payroll"; Filename: "{app}\launcher.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci bureau"; GroupDescription: "Raccourcis:"