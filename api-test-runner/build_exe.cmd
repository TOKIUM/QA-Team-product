@echo off
REM API Test Runner GUI を .exe にビルド
REM 使い方: build_exe.cmd

cd /d "%~dp0"

python -m PyInstaller ^
    --name "API Test Runner" ^
    --onedir ^
    --windowed ^
    --noconfirm ^
    --clean ^
    --hidden-import "yaml" ^
    --hidden-import "requests" ^
    launcher.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ビルド失敗
    pause
    exit /b 1
)

REM .exe と同階層に設定ファイル・CSV をコピー
set DIST=dist\API Test Runner
copy /Y config.yaml "%DIST%\" >nul
copy /Y .env "%DIST%\" >nul 2>nul
xcopy /Y /E /I document "%DIST%\document" >nul
copy /Y .env.example "%DIST%\" >nul 2>nul

echo.
echo ========================================
echo   ビルド成功!
echo   %DIST%\API Test Runner.exe
echo ========================================
echo.
echo   配布時は "%DIST%" フォルダごと渡してください。
echo   results フォルダは初回実行時に自動作成されます。
pause
