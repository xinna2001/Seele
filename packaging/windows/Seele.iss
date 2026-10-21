#ifndef MyAppVersion
  #define MyAppVersion "1.0.0"
#endif

#ifndef MyEdition
  #define MyEdition "windows"
#endif
#if MyEdition == "windows_byte"
  #define MyAppName "Seele 字节版"
  #define MyAppDir "Seele-WindowsByte"
  #define MyAppId "{{2AFB2C9D-2D29-4423-B52C-83F276308B34}"
#else
  #define MyAppName "Seele"
  #define MyAppDir "Seele"
  #define MyAppId "{{DA99B386-2A68-4FB0-8FB6-E84D8B5AEE28}"
#endif
#define MyAppPublisher "Seele Project"
#define MyAppExeName "Seele.exe"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppDir}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\release
OutputBaseFilename=Seele-{#MyAppVersion}-{#MyEdition}-x64-setup
SetupIconFile=..\..\exe.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Files]
Source: "..\..\dist\Seele\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent

#if MyEdition == "windows_byte"
[UninstallRun]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN Seele-WindowsByte-Resume /F"; Flags: runhidden; RunOnceId: "DeleteSeeleResumeTask"
Filename: "{sys}\schtasks.exe"; Parameters: "/End /TN Seele-Botmux-WSL"; Flags: runhidden; RunOnceId: "EndSeeleWSLTask"
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN Seele-Botmux-WSL /F"; Flags: runhidden; RunOnceId: "DeleteSeeleWSLTask"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueName: "SeeleWindowsByteResume"; Flags: uninsdeletevalue
#endif
