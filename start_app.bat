@echo off
setlocal

set SKIP_INSTALL=
if /I "%~1"=="--skip-install" set SKIP_INSTALL=-SkipInstall

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_app.ps1" %SKIP_INSTALL%
if errorlevel 1 (
  echo.
  echo Failed to start application. See error above.
  exit /b 1
)

endlocal
