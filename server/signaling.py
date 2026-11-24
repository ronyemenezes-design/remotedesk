"""
Módulo de Sinalização WebRTC e Gestão de IDs de Acesso Remoto (estilo AnyDesk).
"""
import random
import asyncio

class SignalingService:
    def __init__(self):
        # host_id -> WebSocketClient
        self.hosts = {}
        # client_id -> WebSocketClient
        self.clients = {}
        # client_id -> host_id
        self.active_sessions = {}

    def generate_unique_id(self):
        """Gera um ID numérico no formato XXX-XXX-XXX único."""
        while True:
            n = random.randint(100_000_000, 999_999_999)
            formatted = f"{str(n)[:3]}-{str(n)[3:6]}-{str(n)[6:]}"
            if formatted not in self.hosts:
                return formatted

    async def handle_message(self, client, data):
        action = data.get("type")
        
        # 1. Registro de um Host (o computador que disponibiliza a tela para acesso)
        if action == "register_host":
            requested_id = data.get("host_id")
            if not requested_id or requested_id in self.hosts:
                host_id = self.generate_unique_id()
            else:
                host_id = requested_id

            client.id = host_id
            client.role = "host"
            self.hosts[host_id] = client
            
            print(f"[Signaling] Host registrado: {host_id}")
            await client.send_json({
                "type": "host_registered",
                "host_id": host_id,
                "status": "online"
            })

        # 2. Cliente solicita conexão com um Host pelo ID (ex: 482-195-301)
        elif action == "request_access":
            target_id = data.get("target_id", "").strip()
            client_name = data.get("client_name", "Cliente Remoto")
            
            client.role = "client"
            client.remote_id = target_id
            
            # Gera um ID temporário para o cliente
            temp_client_id = f"client-{random.randint(1000, 9999)}"
            client.id = temp_client_id
            self.clients[temp_client_id] = client

            target_host = self.hosts.get(target_id)
            if not target_host or target_host.closed:
                await client.send_json({
                    "type": "error",
                    "message": f"O computador com ID {target_id} não está online ou não foi encontrado."
                })
                return

            print(f"[Signaling] Cliente {temp_client_id} solicitando acesso ao Host {target_id}")
            # Avisa o Host sobre o pedido de conexão
            await target_host.send_json({
                "type": "connection_requested",
                "client_id": temp_client_id,
                "client_name": client_name
            })

        # 3. Host aceita ou rejeita o pedido
        elif action == "respond_access":
            client_id = data.get("client_id")
            accepted = data.get("accepted", False)
            target_client = self.clients.get(client_id)

            if target_client and not target_client.closed:
                if accepted:
                    self.active_sessions[client_id] = client.id
                    print(f"[Signaling] Host {client.id} ACEITOU conexão de {client_id}")
                    await target_client.send_json({
                        "type": "access_accepted",
                        "host_id": client.id
                    })
                else:
                    print(f"[Signaling] Host {client.id} REJEITOU conexão de {client_id}")
                    await target_client.send_json({
                        "type": "access_rejected",
                        "message": "O usuário remoto recusou o pedido de conexão."
                    })

        # 3.1 Desafio de Senha / Acesso Não Supervisionado (Host -> Cliente)
        elif action == "auth_challenge":
            client_id = data.get("client_id")
            target_client = self.clients.get(client_id)
            if target_client and not target_client.closed:
                await target_client.send_json({
                    "type": "auth_challenge",
                    "host_id": client.id,
                    "requires_password": data.get("requires_password", True)
                })

        # 3.2 Cliente envia a senha para validação (Cliente -> Host)
        elif action == "submit_auth":
            target_id = data.get("target_id")
            target_host = self.hosts.get(target_id)
            if target_host and not target_host.closed:
                await target_host.send_json({
                    "type": "verify_auth",
                    "client_id": client.id,
                    "password_hash": data.get("password_hash")
                })

        # 3.3 Host notifica falha de senha (Host -> Cliente)
        elif action == "auth_failed":
            client_id = data.get("client_id")
            target_client = self.clients.get(client_id)
            if target_client and not target_client.closed:
                await target_client.send_json({
                    "type": "auth_failed",
                    "message": data.get("message", "Senha incorreta. Tente novamente.")
                })

        # 3.4 Cliente pede aprovação manual ao invés de usar senha (Cliente -> Host)
        elif action == "request_manual_approval":
            target_id = data.get("target_id")
            target_host = self.hosts.get(target_id)
            if target_host and not target_host.closed:
                await target_host.send_json({
                    "type": "manual_approval_requested",
                    "client_id": client.id,
                    "client_name": data.get("client_name", "Cliente Remoto")
                })

        # 4. Troca de Oferta SDP (WebRTC Offer)
        elif action == "webrtc_offer":
            target_id = data.get("target_id")
            target = self.hosts.get(target_id) or self.clients.get(target_id)
            if target and not target.closed:
                await target.send_json({
                    "type": "webrtc_offer",
                    "sender_id": client.id,
                    "sdp": data.get("sdp")
                })

        # 5. Troca de Resposta SDP (WebRTC Answer)
        elif action == "webrtc_answer":
            target_id = data.get("target_id")
            target = self.hosts.get(target_id) or self.clients.get(target_id)
            if target and not target.closed:
                await target.send_json({
                    "type": "webrtc_answer",
                    "sender_id": client.id,
                    "sdp": data.get("sdp")
                })

        # 6. Troca de ICE Candidates (WebRTC P2P Traversal)
        elif action == "webrtc_candidate":
            target_id = data.get("target_id")
            target = self.hosts.get(target_id) or self.clients.get(target_id)
            if target and not target.closed:
                await target.send_json({
                    "type": "webrtc_candidate",
                    "sender_id": client.id,
                    "candidate": data.get("candidate")
                })

        # 7. Finalização de sessão
        elif action == "disconnect_session":
            await self.handle_disconnect(client)

    async def handle_disconnect(self, client):
        """Notifica o par quando uma ponta se desconecta."""
        if client.role == "host":
            if client.id in self.hosts:
                del self.hosts[client.id]
                print(f"[Signaling] Host {client.id} desconectado.")
                
            # Avisa clientes conectados
            for cid, hid in list(self.active_sessions.items()):
                if hid == client.id:
                    c = self.clients.get(cid)
                    if c and not c.closed:
                        await c.send_json({"type": "peer_disconnected", "message": "O computador remoto encerrou a sessão."})
                    del self.active_sessions[cid]

        elif client.role == "client":
            if client.id in self.clients:
                del self.clients[client.id]
                print(f"[Signaling] Cliente {client.id} desconectado.")
                
            host_id = self.active_sessions.pop(client.id, None)
            if host_id:
                h = self.hosts.get(host_id)
                if h and not h.closed:
                    await h.send_json({"type": "peer_disconnected", "client_id": client.id})
