"""
RemoteDesk - Ponto de Entrada Principal
Inicia o Servidor de Sinalização HTTP/WebSocket (porta 8080)
e o Agente Nativo de Injeção de Teclado/Mouse (porta 9999).
"""
import asyncio
import os
import sys
import socket
import webbrowser
import subprocess

# Trata caminho quando empacotado pelo PyInstaller (sys._MEIPASS)
if getattr(sys, "frozen", False):
    current_dir = sys._MEIPASS
else:
    current_dir = os.path.dirname(os.path.abspath(__file__))

if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from server.websocket_server import HTTPServerWithWebSocket
from server.signaling import SignalingService
from host.native_agent import NativeHostAgent

def get_local_ip():
    """Tenta descobrir o endereço IP da máquina na rede local."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def open_desktop_window(url):
    """Tenta abrir a janela dedicada de aplicativo ou navegador padrão."""
    try:
        if sys.platform == "darwin":
            cmd = ["open", "-na", "Google Chrome", "--args", f"--app={url}"]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return
        elif sys.platform.startswith("win"):
            edge_cmd = ["cmd", "/c", "start", "msedge", f"--app={url}"]
            res = subprocess.run(edge_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return
    except Exception:
        pass
    webbrowser.open(url)

async def main():
    print("=" * 65)
    print("   RemoteDesk - Sistema de Acesso Remoto P2P (Estilo AnyDesk)   ")
    print("=" * 65)

    local_ip = get_local_ip()
    port_web = 8080
    port_agent = 9999

    # 1. Inicializar Serviço de Sinalização
    signaling = SignalingService()

    # 2. Inicializar Servidor Web & WebSocket
    static_folder = os.path.join(current_dir, "web")
    web_server = HTTPServerWithWebSocket(
        host="0.0.0.0",
        port=port_web,
        static_dir=static_folder,
        on_message_handler=signaling.handle_message,
        on_disconnect_handler=signaling.handle_disconnect
    )
    await web_server.start()

    # 3. Inicializar Agente Nativo de Controle de Mouse e Teclado
    host_agent = NativeHostAgent(port=port_agent)
    await host_agent.start()

    # Se for executado como aplicativo de desktop (ou sem a flag --no-browser), abre a janela
    if "--no-browser" not in sys.argv:
        open_desktop_window(f"http://localhost:{port_web}")

    print("\n[Status] Tudo pronto e em execução!")
    print(f" -> Acesso local:          http://localhost:{port_web}")
    print(f" -> Acesso na rede local:  http://{local_ip}:{port_web}")
    print("\nInstruções de Uso:")
    print(" 1. Abra o link acima no navegador do computador que deseja acessar (Host).")
    print(" 2. Clique em 'Iniciar Compartilhamento de Tela'.")
    print(" 3. Em outro computador (ou outra aba/celular na mesma rede), abra o link,")
    print("    digite o ID exibido e clique em 'Conectar'.")
    print("\n* Nota macOS: Garanta que o Terminal/Python tenha permissão em:")
    print("  'Ajustes do Sistema' > 'Privacidade e Segurança' > 'Acessibilidade'.")
    print("\nPressione Ctrl+C para encerrar o servidor a qualquer momento.")
    print("=" * 65)

    # Mantém o loop ativo
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[RemoteDesk] Servidor encerrado com sucesso.")
