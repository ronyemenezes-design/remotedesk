@echo off
echo ==============================================
echo    Compilando RemoteDesk para Windows (.exe)  
echo ==============================================

:: 1. Garante que o PyInstaller esteja instalado
python -m pip install pyinstaller

:: 2. Limpa builds anteriores
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 3. Executa a compilação
echo [Build] Gerando executavel RemoteDesk.exe...
pyinstaller --clean remotedesk.spec

if exist dist\RemoteDesk.exe (
    echo.
    echo ==============================================
    echo SUCESSO! Executavel gerado:
    echo    -^> dist\RemoteDesk.exe
    echo ==============================================
    
    :: Se tiver o Inno Setup instalado, gera o instalador .exe
    if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
        echo [Build] Compilando instalador com Inno Setup...
        "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" installer_windows.iss
        echo SUCESSO! Instalador gerado em: dist\RemoteDesk-Setup.exe
    )
) else (
    echo [Erro] Falha ao gerar o executavel.
)
pause
