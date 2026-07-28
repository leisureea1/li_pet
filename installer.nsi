!define APPNAME "李彤彤桌面宠物"
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
  
  ; Include the executable
  File "dist\pet.exe"
  
  ; Include the images
  File "character_fullbody.png"
  File "pat_hand_nobg.png"
  
  ; Create shortcut on desktop
  CreateShortcut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\${APPEXE}"
  
  ; Create uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  
  ; Auto-launch after install
  ExecShell "" "$INSTDIR\${APPEXE}"
SectionEnd

Section "Uninstall"
  Delete "$INSTDIR\pet.exe"
  Delete "$INSTDIR\character_fullbody.png"
  Delete "$INSTDIR\pat_hand_nobg.png"
  Delete "$INSTDIR\config.json"
  Delete "$INSTDIR\uninstall.exe"
  
  Delete "$DESKTOP\${APPNAME}.lnk"
  
  RMDir "$INSTDIR"
SectionEnd
