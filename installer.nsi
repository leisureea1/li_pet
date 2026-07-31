!define APPNAME "李瞳瞳桌宠"
!define APPEXE "pet.exe"

Name "${APPNAME}"
OutFile "LiTongtong_Setup.exe"
InstallDir "$LOCALAPPDATA\LiTongtongPet"
RequestExecutionLevel user
Unicode true

Page directory
Page instfiles

Section "Install"
  SetOutPath $INSTDIR
  
  ; Include the executable and dependencies
  File /r "dist\pet\*.*"
  
  ; Create shortcut on desktop
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Auto-launch after install
  ExecShell "" "$INSTDIR\${APPEXE}"
SectionEnd

Section "Uninstall"
  ; Terminate the running pet process before deleting files
  nsExec::Exec 'taskkill /F /IM "${APPEXE}"'
  Sleep 1000

  Delete "$INSTDIR\uninstall.exe"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
