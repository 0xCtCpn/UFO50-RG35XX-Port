@echo off
REM Build UFO 50 (Butterscotch runtime, WAD17, SDL1 fbcon) for MiaUI RG35XX
REM Toolchain: glibc armhf cross (MiaUI SYSTEM is glibc 2.37, INTERP
REM /lib/ld-linux-armhf.so.3 - NO musl /tmp loader staging like Garlic).
docker build --load -t ufo50-miau .
if errorlevel 1 (
  echo Build failed - check docker log above
  exit /b 1
)
if not exist out mkdir out
docker run --rm -v "%cd%\out:/out" ufo50-miau
echo.
echo === Built ===
dir out
echo.
echo Install (MiaUI ROMs partition is EXT4, not FAT32):
echo 1. Copy out\butterscotch, libSDL-1.2*, gamecontrollerdb.txt to
echo    ROMs/Ports/UFO50.pak/ and copy launch.sh there as launch.sh
echo 2. Copy your Windows UFO 50 folder contents into
echo    ROMs/Ports/UFO50.pak/gamefiles/ (data.win + audiogroup*.dat +
echo    textures/ fonts/ ext/)
echo 3. Reboot, PORTS -^> UFO50
echo 4. Debug: read ROMs/Ports/UFO50.pak/debug.log
