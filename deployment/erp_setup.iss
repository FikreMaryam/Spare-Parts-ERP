[Setup]
AppName=ERP for My Shop
AppVersion=1.0.0
AppPublisher=Your Company Name
AppPublisherURL=https://yourwebsite.com
AppSupportURL=https://yourwebsite.com/support
AppUpdatesURL=https://yourwebsite.com/updates
DefaultDirName={pf}\ERP for My Shop
DefaultGroupName=ERP for My Shop
OutputDir=userdocs:Inno Setup Examples Output
OutputBaseFilename=ERPSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\manage.py

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "..\*"; DestDir: "{app}"; Flags: recursesubdirs

[Icons]
Name: "{group}\ERP for My Shop"; Filename: "{app}\run_app.exe"
Name: "{group}\Uninstall ERP"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\run_app.exe"; Description: "Launch ERP Application"; Flags: postinstall nowait