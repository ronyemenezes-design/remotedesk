#!/usr/bin/env bash
set -e

echo "=============================================="
echo "    Compilando RemoteDesk para macOS (.dmg)   "
echo "=============================================="

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# 1. Garante que o PyInstaller esteja instalado
if ! command -v pyinstaller &> /dev/null; then
    echo "[Build] Instalando PyInstaller..."
    python3 -m pip install pyinstaller
fi

# 2. Limpa builds anteriores
echo "[Build] Limpando pastas de compilação antigas..."
rm -rf build dist

# 3. Executa a compilação com o arquivo de especificação
echo "[Build] Gerando aplicativo nativo RemoteDesk.app..."
pyinstaller --clean remotedesk.spec

# 4. Gera a imagem de disco .dmg (Instalador Mac)
if [ -d "dist/RemoteDesk.app" ]; then
    echo "[Build] Criando instalador .dmg com hdiutil..."
    hdiutil create -volname "RemoteDesk" -srcfolder "dist/RemoteDesk.app" -ov -format UDZO "dist/RemoteDesk-macOS.dmg"
    echo ""
    echo "=============================================="
    echo "🎉 SUCESSO! Instalador gerado:"
    echo "   -> dist/RemoteDesk.app"
    echo "   -> dist/RemoteDesk-macOS.dmg"
    echo "=============================================="
else
    echo "❌ Erro: O arquivo dist/RemoteDesk.app não foi gerado."
    exit 1
fi
