# RemoteDesk - Sistema de Acesso Remoto Multiplataforma (AnyDesk Clone)

Um sistema completo de acesso remoto ponto a ponto (P2P) com suporte a **macOS** e **Windows**, inspirado no AnyDesk e RustDesk.

---

## 🏛️ Arquitetura do Sistema

```
[Cliente Remoto / Visualizador]                   [Servidor de Sinalização (Porta 8080)]                   [Host Remoto (Controlado)]
  - Interface Web (HTML5/CSS3)                      - HTTP estático + WebSocket (RFC 6455)                    - Captura de Tela (ScreenCaptureKit/DXGI)
  - Visualização de Vídeo 60 FPS                    - Gera IDs amigáveis (ex: 482-195-301)                    - Servidor WebRTC Host
  - Captura eventos de mouse/teclado                - Troca SDP Offer/Answer e ICE Candidates                 - Agente Nativo (Porta 9999 / ctypes)
         │                                                      │                                                  │
         │──────────────── Conexão Inicial / Sinalização ───────┴──────────────── Conexão Inicial ─────────────────│
         │                                                                                                         │
         │◄═══════════════════ Fluxo Direto P2P (WebRTC / UDP Criptografado) ═════════════════════════════════════►│
                 (Stream de vídeo baixa latência  +  DataChannel binário para mouse/teclado)
```

---

## 🚀 Como Executar

### 1. Iniciar o Servidor e o Agente Nativo
Abra o terminal na pasta do projeto e execute:
```bash
python3 main.py
```

O script iniciará:
- O **Servidor Web e de Sinalização** em `http://localhost:8080` (e no seu IP de rede local).
- O **Agente Nativo de Injeção de Input** em `ws://127.0.0.1:9999`.

---

## 💻 Como Conectar Duas Máquinas (Mac e Windows)

1. **No Computador que será controlado (Host):**
   - Acesse `http://localhost:8080` no navegador.
   - Veja o seu **ID de Conexão** gerado (ex: `123-456-789`).
   - Clique em **"Iniciar Compartilhamento de Tela"** e selecione a tela desejada.

2. **No Computador que vai controlar (Cliente):**
   - Abra o navegador e acesse o IP da outra máquina (ex: `http://192.168.1.50:8080`).
   - No card **"Outro Computador (Cliente)"**, digite o ID do Host e clique em **"Conectar"**.

3. **Confirmação e Acesso Não Supervisionado:**
   - **Modo Padrão (Supervisionado):** O Host exibe uma janela perguntando se aceita ou recusa a conexão.
   - **Modo Não Supervisionado (com Senha):** No Host, ative o botão **"Acesso Não Supervisionado"** e defina uma senha. Quando o Cliente tentar conectar, abrirá uma tela para inserir a senha. Ao digitar a senha correta, a conexão é liberada instantaneamente **sem precisar de ninguém no computador remoto!**
   - As senhas são protegidas com criptografia **SHA-256** de ponta a ponta.

---

## ⚙️ Permissões do Sistema Operacional

### No macOS:
O macOS possui proteção rigorosa de segurança:
1. **Gravação de Tela:** O navegador (Chrome/Safari) solicitará permissão para gravar a tela na primeira vez.
2. **Acessibilidade (para controlar mouse e teclado):**
   - Acesse **Ajustes do Sistema** > **Privacidade e Segurança** > **Acessibilidade**.
   - Habilite o **Terminal** (ou seu aplicativo de terminal, como iTerm / Antigravity).

### No Windows:
- A injeção de mouse e teclado funciona diretamente via API nativa `user32.dll`.
- Para controlar janelas de permissão do sistema (UAC) e tela de bloqueio (Ctrl+Alt+Del), em versões futuras o agente pode ser registrado como um *Windows Service*.

---

## 📦 Como Gerar os Instaladores Executáveis (.dmg e .exe)

Configuramos todo o pipeline para transformar o RemoteDesk em um aplicativo de desktop com dois cliques, sem precisar abrir terminal:

### 1. No macOS (Gera o aplicativo `RemoteDesk.app` e a imagem `RemoteDesk-macOS.dmg`):
No terminal da pasta do projeto:
```bash
./build_mac.sh
```
O script usará o PyInstaller e a ferramenta nativa `hdiutil` do macOS para criar:
- `dist/RemoteDesk.app` (Aplicativo clicável)
- `dist/RemoteDesk-macOS.dmg` (Instalador clássico do Mac)

### 2. No Windows (Gera o `RemoteDesk.exe` e o `RemoteDesk-Setup.exe`):
No Prompt de Comando (CMD) ou PowerShell na máquina Windows:
```cmd
build_windows.bat
```
Será gerado:
- `dist\RemoteDesk.exe` (Executável portátil sem tela preta de terminal)
- `dist\RemoteDesk-Setup-Windows.exe` (Instalador completo estilo Wizard/Inno Setup)

### 3. Compilação Automática na Nuvem (GitHub Actions CI/CD):
O arquivo `.github/workflows/build-release.yml` já está configurado. Ao subir o projeto para o GitHub:
- O GitHub Actions compilará automaticamente em máquinas reais Mac e Windows.
- Os instaladores `.dmg` e `.exe` ficam disponíveis para download direto na aba **Actions** ou **Releases**!

---

## 📁 Estrutura de Arquivos

```
remote-desktop/
├── server/
│   ├── websocket_server.py  # Servidor HTTP e WebSocket RFC 6455 puro (asyncio, sem dependências externas)
│   └── signaling.py         # Roteamento de sessões, IDs de 9 dígitos e troca WebRTC SDP/ICE
├── host/
│   ├── input_injector.py    # Injetor nativo de mouse e teclado via ctypes (macOS ApplicationServices & Win32)
│   └── native_agent.py      # Agente WebSocket local que executa os comandos de mouse/teclado
├── web/
│   ├── index.html           # Interface visual no estilo AnyDesk (Dashboard, Modal e Viewport)
│   ├── style.css            # Tema escuro moderno com detalhes em vermelho
│   └── app.js               # Motor WebRTC (STUN, PeerConnection, DataChannel e normalização de cursor)
├── main.py                  # Ponto de entrada unificado
└── README.md                # Documentação do projeto
```
