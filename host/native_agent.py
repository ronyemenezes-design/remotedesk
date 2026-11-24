"""
Agente local para o Host.
Recebe comandos de mouse e teclado via WebSocket local (ws://127.0.0.1:9999)
e injeta no Sistema Operacional (macOS ou Windows).
"""
import asyncio
import json
from host.input_injector import InputInjector
from server.websocket_server import WebSocketClient

class NativeHostAgent:
    def __init__(self, port=9999):
        self.port = port
        self.injector = InputInjector()
        self.server = None

    async def start(self):
        from server.websocket_server import HTTPServerWithWebSocket
        server_instance = HTTPServerWithWebSocket(
            host="127.0.0.1",
            port=self.port,
            on_message_handler=self.handle_input_event
        )
        self.server = await server_instance.start()
        print(f"[HostAgent] Agente nativo ativo em ws://127.0.0.1:{self.port} (pronto para controlar mouse/teclado)")
        return self.server

    async def handle_input_event(self, client, data):
        action = data.get("action")
        
        if action == "mouse_move":
            self.injector.mouse_move(data.get("x", 0), data.get("y", 0))

        elif action == "mouse_down":
            self.injector.mouse_down(data.get("x", 0), data.get("y", 0), data.get("button", "left"))

        elif action == "mouse_up":
            self.injector.mouse_up(data.get("x", 0), data.get("y", 0), data.get("button", "left"))

        elif action == "mouse_click":
            self.injector.mouse_click(data.get("x", 0), data.get("y", 0), data.get("button", "left"))

        elif action == "mouse_scroll":
            self.injector.mouse_scroll(data.get("dy", 0), data.get("dx", 0))

        elif action == "key_down":
            self.injector.key_press(data.get("key", ""), down=True)

        elif action == "key_up":
            self.injector.key_press(data.get("key", ""), down=False)

        elif action == "type_text":
            self.injector.type_unicode(data.get("text", ""))

        elif action == "get_screen_info":
            await client.send_json({
                "type": "screen_info",
                "info": self.injector.get_screen_resolution()
            })
