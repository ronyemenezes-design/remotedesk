# -*- mode: python ; coding: utf-8 -*-
import sys
import os

block_cipher = None

# Diretório base
BASE_DIR = os.path.abspath(SPECPATH)

# Inclui todos os arquivos estáticos da interface web
datas = [
    (os.path.join(BASE_DIR, 'web'), 'web')
]

hiddenimports = [
    'asyncio',
    'ctypes',
    'server',
    'server.websocket_server',
    'server.signaling',
    'host',
    'host.input_injector',
    'host.native_agent'
]

a = Analysis(
    [os.path.join(BASE_DIR, 'main.py')],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Configuração de Executável (.exe para Windows / binário para macOS)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RemoteDesk',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Não abre janela de prompt/terminal preta (abre direto como app GUI)
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(BASE_DIR, 'assets', 'icon.icns') if sys.platform == 'darwin' and os.path.exists(os.path.join(BASE_DIR, 'assets', 'icon.icns')) else None
)

# Configuração do Pacote .app para macOS
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='RemoteDesk.app',
        icon=os.path.join(BASE_DIR, 'assets', 'icon.icns') if os.path.exists(os.path.join(BASE_DIR, 'assets', 'icon.icns')) else None,
        bundle_identifier='com.remotedesk.app',
        info_plist={
            'CFBundleName': 'RemoteDesk',
            'CFBundleDisplayName': 'RemoteDesk',
            'CFBundleIdentifier': 'com.remotedesk.app',
            'CFBundleVersion': '1.0.0',
            'CFBundleShortVersionString': '1.0.0',
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '11.0',
            'NSScreenCaptureUsageDescription': 'RemoteDesk precisa de permissão para capturar a tela para transmissão remota.',
            'NSAccessibilityUsageDescription': 'RemoteDesk precisa de permissão de acessibilidade para controlar o mouse e teclado.',
        }
    )
