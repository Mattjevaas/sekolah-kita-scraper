@echo off
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%"

if "%~1"=="" (
  python "scrape_sekolah_kita.py" --tui
) else (
  python "scrape_sekolah_kita.py" %*
)

popd
endlocal
