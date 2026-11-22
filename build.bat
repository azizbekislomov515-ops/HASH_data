@echo off
setlocal
set "HASHFORGE_ONEFILE=0"
if "%~1"=="" goto args_done
if /I "%~1"=="--onedir" goto args_done
if /I "%~1"=="--onefile" (
    set "HASHFORGE_ONEFILE=1"
    goto args_done
)
goto usage
:args_done
if not "%~2"=="" goto usage
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher not found. Install Python 3.11 or newer from python.org.
    exit /b 1
)
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
    echo Python 3.11 or newer is required.
    exit /b 1
)
if not exist .venv\Scripts\python.exe (
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :failed
set QT_QPA_PLATFORM=offscreen
set QT_QPA_PLATFORMTHEME=
set QT_STYLE_OVERRIDE=Fusion
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 goto :failed
set QT_QPA_PLATFORM=
.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean hashforge.spec
if errorlevel 1 goto :failed
echo.
if "%HASHFORGE_ONEFILE%"=="1" (
    echo Build complete: %CD%\dist\HashForge.exe
) else (
    echo Build complete: %CD%\dist\HashForge\HashForge.exe
    echo Distribute the entire dist\HashForge folder.
)
exit /b 0
:failed
echo Build failed. See the error above.
exit /b 1
:usage
echo Usage: build.bat [--onedir^|--onefile]
exit /b 2
