; Grayson Windows installer - compiled by CI (windows-latest) with Inno Setup 6.
; Produces Grayson-Setup.exe: per-user install (no admin needed), Start menu
; entry, optional desktop shortcut, optional start-with-Windows entry,
; uninstaller, and a post-install LibreOffice hint for Office conversions.
; NOT code-signed: Windows SmartScreen will warn on first run.

#define MyAppName "Grayson"
#define MyAppVersion "0.2.3"
#define MyAppPublisher "M J Anthony"
#define MyAppURL "https://github.com/mjanthony819/grayson"
#define MyAppExeName "Grayson.exe"

[Setup]
AppId={{3F7A2E51-9C4B-4A1D-8E6F-2B5D0C9A7E31}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\Grayson
PrivilegesRequired=lowest
DefaultGroupName={#MyAppName}
SourceDir={#SourcePath}..
LicenseFile=LICENSE
OutputDir={#SourcePath}..\installer-output
OutputBaseFilename=Grayson-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile={#SourcePath}..\assets\grayson.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startup"; Description: "&Start Grayson automatically when you sign in to Windows"; GroupDescription: "Startup:"

[Files]
Source: "dist\Grayson\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Grayson\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Code]
function LibreOfficePresent(): Boolean;
begin
  Result := FileExists(ExpandConstant('{autopf}\LibreOffice\program\soffice.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not LibreOfficePresent()) then
    MsgBox('Grayson was installed successfully.' + #13#10#13#10 +
      'Note: Word, PowerPoint and Excel conversions need LibreOffice (free).' + #13#10 +
      'Install it with:  winget install TheDocumentFoundation.LibreOffice' + #13#10#13#10 +
      'Image, video, audio, PDF and text conversions work without it.',
      mbInformation, MB_OK);
end;
