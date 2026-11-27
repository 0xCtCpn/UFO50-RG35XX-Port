@echo off
REM Stage a clean, ready-to-copy UFO50.pak - NO zip is created.
REM Game-free (no data.win/audio groups/textures/fonts). Ships NO libasound
REM and NO share\alsa: those would shadow the system audio stack at runtime.
REM Output: out\UFO50.pak\ (copy this folder into PORTS/ on the SD card).
setlocal
set D=%~dp0
set OUT=%~dp0out
set PAK=%OUT%\UFO50.pak
if not exist "%D%out\butterscotch" (
  echo Missing out\butterscotch - run build.bat first
  exit /b 1
)
if not exist "%D%out\libSDL-1.2.so.0" (
  echo Missing out\libSDL-1.2.so.0 - run build.bat first
  exit /b 1
)
rmdir /S /Q "%PAK%" 2>nul
mkdir "%PAK%" 2>nul
copy /Y "%D%launch.sh" "%PAK%\launch.sh" >nul
copy /Y "%D%out\butterscotch" "%PAK%\butterscotch" >nul
copy /Y "%D%out\libSDL-1.2.so.0" "%PAK%\" >nul
if exist "%D%out\libSDL-1.2.so.0.11.4" copy /Y "%D%out\libSDL-1.2.so.0.11.4" "%PAK%\" >nul
copy /Y "%D%out\gamecontrollerdb.txt" "%PAK%\" >nul
copy /Y "%D%LICENSE" "%PAK%\LICENSE" >nul
copy /Y "%D%NOTICE.MiaUI" "%PAK%\NOTICE.MiaUI" >nul
copy /Y "%D%README.md" "%PAK%\README.md" >nul
mkdir "%PAK%\licenses" 2>nul
copy /Y "%D%licenses\THIRD_PARTY.txt" "%PAK%\licenses\" >nul
echo === Staged pak (must NOT contain libasound or game data) ===
dir "%PAK%"
where powershell >nul 2>&1
REM NOTE: -Include only filters with -Path wildcards (dir\*), NOT -LiteralPath.
REM A leak exits 1 so the errorlevel check below actually fails packaging.
powershell -NoProfile -Command "$bad = @(Get-ChildItem -Path '%PAK%\*' -Recurse -Include 'libasound*','data.win','*.dat','*.ogg','*.wav','*.mp3','*.sav','*.ini'); if ($bad.Count -gt 0) { $bad | ForEach-Object { Write-Host ('LEAK: ' + $_.FullName) }; exit 1 }; if (Test-Path -LiteralPath '%PAK%\share') { Write-Host 'LEAK: bundled share\alsa in pak'; exit 1 }"
if errorlevel 1 (
  echo Package failed
  exit /b 1
)
echo.
echo Done: out\UFO50.pak (ready to copy - no zip is created)
echo Install: copy this folder to /userdata/Ports/UFO50.pak/ then
echo copy your Windows UFO 50 folder contents into UFO50.pak/gamefiles/
endlocal
