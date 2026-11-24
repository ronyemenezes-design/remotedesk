"""
Servidor WebSocket e HTTP estático embutido utilizando apenas a biblioteca padrão (asyncio).
Compatível com a RFC 6455 para WebSockets.
"""
import asyncio
import base64
import hashlib
import json
import mimetypes
import os
import struct
import urllib.parse

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class WebSocketClient:
    def __init__(self, reader, writer, path):
        self.reader = reader
        self.writer = writer
        self.path = path
        self.closed = False
        self.id = None
        self.role = None  # 'host' ou 'client'
        self.remote_id = None

    async def send_json(self, data):
        """Envia um objeto serializado em JSON como frame de texto WebSocket."""
        await self.send_text(json.dumps(data))

    async def send_text(self, text):
        if self.closed:
            return
        payload = text.encode("utf-8")
        length = len(payload)
        
        # Byte 0: FIN (0x80) | Opcode Text (0x01)
        header = bytearray([0x81])
        
        # Byte 1+: Sem máscara (servidor -> cliente) + Comprimento
        if length <= 125:
            header.append(length)
        elif length <= 65535:
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))
            
        try:
            self.writer.write(header + payload)
            await self.writer.drain()
        except Exception:
            self.closed = True

    async def send_pong(self, data):
        if self.closed:
            return
        header = bytearray([0x8A, len(data)])
        try:
            self.writer.write(header + data)
            await self.writer.drain()
        except Exception:
            self.closed = True

    async def close(self):
        if not self.closed:
            self.closed = True
            try:
                # Frame Close (0x88)
                self.writer.write(bytearray([0x88, 0x00]))
                await self.writer.drain()
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

    async def read_frame(self):
        """Lê e decodifica um frame WebSocket vindo do cliente."""
        try:
            header = await self.reader.readexactly(2)
        except (asyncio.IncompleteReadError, ConnectionResetError):
            return None, None
            
        byte0, byte1 = header[0], header[1]
        fin = bool(byte0 & 0x80)
        opcode = byte0 & 0x0F
        is_masked = bool(byte1 & 0x80)
        payload_len = byte1 & 0x7F

        if opcode == 0x8:  # Close
            await self.close()
            return None, None

        if payload_len == 126:
            ext_len = await self.reader.readexactly(2)
            payload_len = struct.unpack("!H", ext_len)[0]
        elif payload_len == 127:
            ext_len = await self.reader.readexactly(8)
            payload_len = struct.unpack("!Q", ext_len)[0]

        mask = None
        if is_masked:
            mask = await self.reader.readexactly(4)

        payload = await self.reader.readexactly(payload_len)
        if is_masked and mask:
            unmasked = bytearray(payload_len)
            for i in range(payload_len):
                unmasked[i] = payload[i] ^ mask[i % 4]
            payload = bytes(unmasked)

        if opcode == 0x9:  # Ping
            await self.send_pong(payload)
            return await self.read_frame()

        if opcode == 0x1:  # Text frame
            return "text", payload.decode("utf-8")
        elif opcode == 0x2:  # Binary frame
            return "binary", payload
            
        return opcode, payload


class HTTPServerWithWebSocket:
    def __init__(self, host="0.0.0.0", port=8080, static_dir="web", on_message_handler=None, on_disconnect_handler=None):
        self.host = host
        self.port = port
        self.static_dir = os.path.abspath(static_dir)
        self.on_message = on_message_handler
        self.on_disconnect = on_disconnect_handler
        self.clients = set()

    async def start(self):
        server = await asyncio.start_server(self.handle_connection, self.host, self.port)
        print(f"[Servidor] Rodando em http://localhost:{self.port} e http://{self.host}:{self.port}")
        return server

    async def handle_connection(self, reader, writer):
        try:
            request_line = await reader.readline()
            if not request_line:
                writer.close()
                return

            line = request_line.decode("utf-8", errors="ignore").strip()
            parts = line.split(" ")
            if len(parts) < 2:
                writer.close()
                return

            method, path = parts[0], parts[1]
            headers = {}
            while True:
                header_line = await reader.readline()
                if not header_line or header_line == b"\r\n":
                    break
                h_str = header_line.decode("utf-8", errors="ignore").strip()
                if ":" in h_str:
                    k, v = h_str.split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            # Upgrade para WebSocket se solicitado
            if headers.get("upgrade", "").lower() == "websocket":
                await self.upgrade_websocket(reader, writer, path, headers)
            elif method == "GET":
                await self.serve_static_file(writer, path)
            else:
                writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
                await writer.drain()
                writer.close()
        except Exception as e:
            try:
                writer.close()
            except Exception:
                pass

    async def upgrade_websocket(self, reader, writer, path, headers):
        ws_key = headers.get("sec-websocket-key")
        if not ws_key:
            writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
            await writer.drain()
            writer.close()
            return

        accept_val = base64.b64encode(hashlib.sha1((ws_key + GUID).encode("utf-8")).digest()).decode("utf-8")
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept_val}\r\n\r\n"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()

        client = WebSocketClient(reader, writer, path)
        self.clients.add(client)

        try:
            while not client.closed:
                msg_type, payload = await client.read_frame()
                if msg_type is None:
                    break
                if msg_type == "text" and self.on_message:
                    try:
                        data = json.loads(payload)
                        await self.on_message(client, data)
                    except json.JSONDecodeError:
                        pass
        finally:
            self.clients.discard(client)
            if self.on_disconnect:
                await self.on_disconnect(client)
            await client.close()

    async def serve_static_file(self, writer, raw_path):
        url_path = urllib.parse.urlparse(raw_path).path
        if url_path == "/" or url_path == "":
            url_path = "/index.html"

        # Proteção contra Directory Traversal
        safe_path = os.path.normpath(url_path.lstrip("/"))
        file_path = os.path.join(self.static_dir, safe_path)

        if not os.path.commonpath([self.static_dir, file_path]) == self.static_dir or not os.path.exists(file_path) or os.path.isdir(file_path):
            body = b"<h1>404 Not Found</h1>"
            response = (
                f"HTTP/1.1 404 Not Found\r\n"
                f"Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body)}\r\n"
                f"Connection: close\r\n\r\n"
            ).encode("utf-8") + body
            writer.write(response)
            await writer.drain()
            writer.close()
            return

        mime_type, _ = mimetypes.guess_type(file_path)
        mime_type = mime_type or "application/octet-stream"

        with open(file_path, "rb") as f:
            content = f.read()

        response_header = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: {mime_type}\r\n"
            f"Content-Length: {len(content)}\r\n"
            f"Access-Control-Allow-Origin: *\r\n"
            f"Cache-Control: no-cache\r\n"
            f"Connection: close\r\n\r\n"
        ).encode("utf-8")

        writer.write(response_header + content)
        await writer.drain()
        writer.close()
