/**
 * RemoteDesk - Lógica WebRTC, Sinalização e Manipulação de Eventos de Mouse/Teclado
 */

// Configuração dos servidores STUN públicos do Google para conexão P2P (NAT Traversal)
const RTC_CONFIG = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ]
};

// Função auxiliar para Hashing SHA-256 criptograficamente seguro via Web Crypto API
async function sha256(text) {
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  const hashBuffer = await crypto.subtle.digest('SHA-256', data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
}

class RemoteDeskApp {
  constructor() {
    this.signalingWs = null;
    this.nativeAgentWs = null;
    this.peerConnection = null;
    this.dataChannel = null;
    this.localStream = null;
    this.myHostId = null;
    this.connectedRemoteId = null;
    this.isInputControlActive = true;
    this.pendingClientId = null;

    this.cacheDOM();
    this.bindEvents();
    this.initUnattendedAccess();
    this.connectSignalingServer();
    this.connectNativeAgent();
  }

  cacheDOM() {
    this.serverStatusDot = document.getElementById('server-status-dot');
    this.serverStatusText = document.getElementById('server-status-text');
    this.hostIdDisplay = document.getElementById('host-id-display');
    this.btnCopyId = document.getElementById('btn-copy-id');
    this.btnStartSharing = document.getElementById('btn-start-sharing');
    this.agentStatusDot = document.getElementById('agent-status-dot');
    this.agentStatusText = document.getElementById('agent-status-text');

    // Elementos de Acesso Não Supervisionado
    this.toggleUnattended = document.getElementById('toggle-unattended');
    this.unattendedFields = document.getElementById('unattended-fields');
    this.unattendedPasswordInput = document.getElementById('unattended-password-input');
    this.btnSaveUnattended = document.getElementById('btn-save-unattended');
    this.unattendedStatusBadge = document.getElementById('unattended-status-badge');

    // Modal de Senha no Cliente
    this.passwordModal = document.getElementById('password-modal');
    this.clientPasswordInput = document.getElementById('client-password-input');
    this.passwordErrorText = document.getElementById('password-error-text');
    this.btnSubmitPassword = document.getElementById('btn-submit-password');
    this.btnRequestManual = document.getElementById('btn-request-manual');
    this.btnCancelPassword = document.getElementById('btn-cancel-password');
    
    this.remoteIdInput = document.getElementById('remote-id-input');
    this.btnConnectRemote = document.getElementById('btn-connect-remote');

    this.dashboardView = document.getElementById('dashboard-view');
    this.remoteSessionView = document.getElementById('remote-session-view');
    this.sessionTargetId = document.getElementById('session-target-id');
    this.remoteVideo = document.getElementById('remote-video');
    this.sessionOverlay = document.getElementById('session-overlay');
    this.overlayStatusText = document.getElementById('overlay-status-text');

    this.btnToggleInput = document.getElementById('btn-toggle-input');
    this.btnFullscreen = document.getElementById('btn-fullscreen');
    this.btnDisconnect = document.getElementById('btn-disconnect');

    this.accessModal = document.getElementById('access-modal');
    this.modalClientName = document.getElementById('modal-client-name');
    this.btnAcceptAccess = document.getElementById('btn-accept-access');
    this.btnRejectAccess = document.getElementById('btn-reject-access');
  }

  bindEvents() {
    this.btnCopyId.addEventListener('click', () => this.copyHostId());
    this.btnStartSharing.addEventListener('click', () => this.startScreenSharing());
    this.btnConnectRemote.addEventListener('click', () => this.initiateRemoteConnection());

    // Eventos de Acesso Não Supervisionado (Host)
    this.toggleUnattended.addEventListener('change', (e) => this.handleUnattendedToggle(e.target.checked));
    this.btnSaveUnattended.addEventListener('click', () => this.saveUnattendedPassword());
    this.unattendedPasswordInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.saveUnattendedPassword();
    });

    // Eventos do Modal de Senha (Cliente)
    this.btnSubmitPassword.addEventListener('click', () => this.submitRemotePassword());
    this.clientPasswordInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.submitRemotePassword();
    });
    this.btnRequestManual.addEventListener('click', () => this.requestManualApproval());
    this.btnCancelPassword.addEventListener('click', () => {
      this.passwordModal.classList.add('hidden');
      this.resetSessionUI();
    });
    
    // Formatação do ID com hífen automático (XXX-XXX-XXX)
    this.remoteIdInput.addEventListener('input', (e) => {
      let val = e.target.value.replace(/\D/g, '');
      if (val.length > 3 && val.length <= 6) {
        val = val.slice(0, 3) + '-' + val.slice(3);
      } else if (val.length > 6) {
        val = val.slice(0, 3) + '-' + val.slice(3, 6) + '-' + val.slice(6, 9);
      }
      e.target.value = val;
    });

    this.remoteIdInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') this.initiateRemoteConnection();
    });

    this.btnAcceptAccess.addEventListener('click', () => this.handleAccessDecision(true));
    this.btnRejectAccess.addEventListener('click', () => this.handleAccessDecision(false));

    this.btnToggleInput.addEventListener('click', () => this.toggleInputControl());
    this.btnFullscreen.addEventListener('click', () => this.toggleFullscreen());
    this.btnDisconnect.addEventListener('click', () => this.disconnectSession());

    // Eventos do mouse e teclado na visualização remota
    this.setupRemoteInputListeners();
  }

  // Conecta ao servidor de sinalização principal (porta 8080)
  connectSignalingServer() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;

    this.signalingWs = new WebSocket(wsUrl);

    this.signalingWs.onopen = () => {
      this.serverStatusDot.className = 'status-indicator online';
      this.serverStatusText.textContent = 'Servidor de Sinalização Online';
      // Registra como Host assim que conecta
      this.signalingWs.send(JSON.stringify({ type: 'register_host' }));
    };

    this.signalingWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleSignalingMessage(data);
      } catch (err) {
        console.error('Erro ao processar mensagem de sinalização:', err);
      }
    };

    this.signalingWs.onclose = () => {
      this.serverStatusDot.className = 'status-indicator offline';
      this.serverStatusText.textContent = 'Desconectado do servidor. Tentando reconectar...';
      setTimeout(() => this.connectSignalingServer(), 2500);
    };
  }

  // Conecta ao agente nativo de mouse/teclado que roda no computador local
  connectNativeAgent() {
    try {
      this.nativeAgentWs = new WebSocket('ws://127.0.0.1:9999');

      this.nativeAgentWs.onopen = () => {
        this.agentStatusDot.className = 'agent-dot online';
        this.agentStatusText.textContent = 'Agente nativo de mouse/teclado: Ativo e pronto';
      };

      this.nativeAgentWs.onclose = () => {
        this.agentStatusDot.className = 'agent-dot';
        this.agentStatusText.textContent = 'Agente nativo: Inativo (execute "python3 main.py")';
        setTimeout(() => this.connectNativeAgent(), 3000);
      };

      this.nativeAgentWs.onerror = () => {
        // Silencioso para evitar poluição no console quando reconectando
      };
    } catch (e) {
      setTimeout(() => this.connectNativeAgent(), 3000);
    }
  }

  // ==========================================
  // GERENCIAMENTO DE ACESSO NÃO SUPERVISIONADO
  // ==========================================

  initUnattendedAccess() {
    const isEnabled = localStorage.getItem('remotedesk_unattended_enabled') === 'true';
    const savedHash = localStorage.getItem('remotedesk_unattended_hash');

    this.toggleUnattended.checked = isEnabled;
    if (isEnabled) {
      this.unattendedFields.classList.remove('hidden');
    }
    
    if (savedHash) {
      this.unattendedStatusBadge.textContent = '✓ Senha ativa e salva com SHA-256';
      this.unattendedStatusBadge.className = 'unattended-status saved';
    } else {
      this.unattendedStatusBadge.textContent = 'Nenhuma senha definida';
      this.unattendedStatusBadge.className = 'unattended-status';
    }
  }

  handleUnattendedToggle(enabled) {
    localStorage.setItem('remotedesk_unattended_enabled', enabled ? 'true' : 'false');
    if (enabled) {
      this.unattendedFields.classList.remove('hidden');
      this.unattendedPasswordInput.focus();
    } else {
      this.unattendedFields.classList.add('hidden');
    }
  }

  async saveUnattendedPassword() {
    const rawPassword = this.unattendedPasswordInput.value.trim();
    if (!rawPassword) {
      alert('Digite uma senha para o acesso não supervisionado.');
      return;
    }

    const hash = await sha256(rawPassword);
    localStorage.setItem('remotedesk_unattended_hash', hash);
    this.unattendedPasswordInput.value = '';
    this.unattendedStatusBadge.textContent = '✓ Senha ativa e salva com SHA-256';
    this.unattendedStatusBadge.className = 'unattended-status saved';
    
    // Feedback visual
    const orig = this.btnSaveUnattended.innerHTML;
    this.btnSaveUnattended.innerHTML = `
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="20 6 9 17 4 12"></polyline>
      </svg>
    `;
    setTimeout(() => this.btnSaveUnattended.innerHTML = orig, 1500);
  }

  async submitRemotePassword() {
    const rawPass = this.clientPasswordInput.value.trim();
    if (!rawPass) return;

    this.passwordErrorText.classList.add('hidden');
    const hash = await sha256(rawPass);

    if (this.signalingWs && this.signalingWs.readyState === WebSocket.OPEN) {
      this.signalingWs.send(JSON.stringify({
        type: 'submit_auth',
        target_id: this.connectedRemoteId,
        password_hash: hash
      }));
    }
  }

  requestManualApproval() {
    this.passwordModal.classList.add('hidden');
    this.sessionOverlay.classList.remove('hidden');
    this.overlayStatusText.textContent = 'Solicitando aprovação manual ao usuário remoto...';

    if (this.signalingWs && this.signalingWs.readyState === WebSocket.OPEN) {
      this.signalingWs.send(JSON.stringify({
        type: 'request_manual_approval',
        target_id: this.connectedRemoteId,
        client_name: 'Usuário Remoto'
      }));
    }
  }

  handleSignalingMessage(data) {
    switch (data.type) {
      case 'host_registered':
        this.myHostId = data.host_id;
        this.hostIdDisplay.textContent = this.myHostId;
        break;

      case 'connection_requested':
        // Notificação de alguém tentando se conectar a este computador
        this.pendingClientId = data.client_id;
        this.modalClientName.textContent = data.client_name || `Cliente (${data.client_id})`;

        const unattendedEnabled = localStorage.getItem('remotedesk_unattended_enabled') === 'true';
        const hasSavedHash = !!localStorage.getItem('remotedesk_unattended_hash');

        if (unattendedEnabled && hasSavedHash) {
          // Computador tem senha configurada: envia desafio de autenticação para o cliente
          this.signalingWs.send(JSON.stringify({
            type: 'auth_challenge',
            client_id: data.client_id,
            requires_password: true
          }));
        } else {
          // Sem senha configurada: exibe modal de aprovação manual
          this.accessModal.classList.remove('hidden');
        }
        break;

      case 'verify_auth':
        // Host valida o hash de senha enviado pelo cliente
        const currentHash = localStorage.getItem('remotedesk_unattended_hash');
        if (currentHash && data.password_hash === currentHash) {
          console.log('[Host] Autenticação de Acesso Não Supervisionado BEM SUCEDIDA!');
          this.handleAccessDecision(true, data.client_id);
        } else {
          console.warn('[Host] Tentativa com senha incorreta de:', data.client_id);
          this.signalingWs.send(JSON.stringify({
            type: 'auth_failed',
            client_id: data.client_id,
            message: 'Senha incorreta. Verifique e tente novamente.'
          }));
        }
        break;

      case 'auth_challenge':
        // Cliente recebe pedido de senha do host
        this.passwordErrorText.classList.add('hidden');
        this.clientPasswordInput.value = '';
        this.passwordModal.classList.remove('hidden');
        setTimeout(() => this.clientPasswordInput.focus(), 100);
        break;

      case 'auth_failed':
        // Cliente recebeu erro de senha
        this.passwordErrorText.textContent = data.message || 'Senha incorreta.';
        this.passwordErrorText.classList.remove('hidden');
        this.clientPasswordInput.focus();
        break;

      case 'manual_approval_requested':
        // Cliente pediu aprovação manual ao invés de senha
        this.pendingClientId = data.client_id;
        this.modalClientName.textContent = data.client_name || `Cliente (${data.client_id})`;
        this.accessModal.classList.remove('hidden');
        break;

      case 'access_accepted':
        this.passwordModal.classList.add('hidden');
        this.overlayStatusText.textContent = 'Acesso permitido! Estabelecendo fluxo P2P...';
        this.startClientWebRTC();
        break;

      case 'access_rejected':
        this.passwordModal.classList.add('hidden');
        alert(data.message || 'O acesso foi recusado pelo computador remoto.');
        this.resetSessionUI();
        break;

      case 'webrtc_offer':
        this.handleWebRTCOffer(data.sender_id, data.sdp);
        break;

      case 'webrtc_answer':
        this.handleWebRTCAnswer(data.sdp);
        break;

      case 'webrtc_candidate':
        this.handleNewICECandidate(data.candidate);
        break;

      case 'peer_disconnected':
        alert(data.message || 'A sessão foi encerrada pela outra ponta.');
        this.resetSessionUI();
        break;

      case 'error':
        alert(data.message);
        this.resetSessionUI();
        break;
    }
  }

  // ==========================================
  // LÓGICA DO HOST (QUEM COMPARTILHA A TELA)
  // ==========================================

  async startScreenSharing() {
    try {
      this.localStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
          frameRate: { ideal: 60, max: 60 }
        },
        audio: false
      });

      this.btnStartSharing.classList.remove('btn-primary');
      this.btnStartSharing.classList.add('btn-success');
      this.btnStartSharing.innerHTML = `
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        Tela Pronta para Transmissão
      `;

      this.localStream.getVideoTracks()[0].onended = () => {
        this.btnStartSharing.classList.remove('btn-success');
        this.btnStartSharing.classList.add('btn-primary');
        this.btnStartSharing.textContent = 'Iniciar Compartilhamento de Tela';
        this.localStream = null;
      };
    } catch (err) {
      console.error('Erro ao capturar tela:', err);
      alert('Não foi possível capturar a tela. Verifique as permissões do navegador.');
    }
  }

  async handleAccessDecision(accepted, specificClientId = null) {
    this.accessModal.classList.add('hidden');
    const clientId = specificClientId || this.pendingClientId;
    if (!clientId) return;

    this.signalingWs.send(JSON.stringify({
      type: 'respond_access',
      client_id: clientId,
      accepted: accepted
    }));

    if (accepted) {
      if (!this.localStream) {
        await this.startScreenSharing();
      }
      this.setupHostPeerConnection(clientId);
    }
    this.pendingClientId = null;
  }

  async setupHostPeerConnection(clientId) {
    this.peerConnection = new RTCPeerConnection(RTC_CONFIG);

    // Adiciona os tracks da tela local para serem transmitidos ao cliente
    if (this.localStream) {
      this.localStream.getTracks().forEach(track => {
        this.peerConnection.addTrack(track, this.localStream);
      });
    }

    // Escuta pelo canal de dados criado pelo cliente (para receber mouse e teclado)
    this.peerConnection.ondatachannel = (event) => {
      this.dataChannel = event.channel;
      this.dataChannel.onmessage = (e) => {
        // Repassa o evento diretamente para o agente nativo executar no SO
        if (this.nativeAgentWs && this.nativeAgentWs.readyState === WebSocket.OPEN) {
          this.nativeAgentWs.send(e.data);
        }
      };
    };

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.signalingWs.send(JSON.stringify({
          type: 'webrtc_candidate',
          target_id: clientId,
          candidate: event.candidate
        }));
      }
    };

    // Cria a oferta WebRTC
    const offer = await this.peerConnection.createOffer();
    await this.peerConnection.setLocalDescription(offer);

    this.signalingWs.send(JSON.stringify({
      type: 'webrtc_offer',
      target_id: clientId,
      sdp: offer
    }));
  }

  // ==========================================
  // LÓGICA DO CLIENTE (QUEM ACESSA REMOTAMENTE)
  // ==========================================

  initiateRemoteConnection() {
    const targetId = this.remoteIdInput.value.trim();
    if (!targetId || targetId.length < 9) {
      alert('Por favor, digite um ID de computador válido.');
      return;
    }

    this.connectedRemoteId = targetId;
    this.sessionTargetId.textContent = `Conectado a: ${targetId}`;
    this.dashboardView.classList.add('hidden');
    this.remoteSessionView.classList.remove('hidden');
    this.sessionOverlay.classList.remove('hidden');
    this.overlayStatusText.textContent = 'Solicitando autorização ao computador remoto...';

    // Envia pedido de conexão ao servidor de sinalização
    this.signalingWs.send(JSON.stringify({
      type: 'request_access',
      target_id: targetId,
      client_name: 'Usuário Remoto'
    }));
  }

  startClientWebRTC() {
    this.peerConnection = new RTCPeerConnection(RTC_CONFIG);

    // Cria o DataChannel para envio de mouse e teclado em ultra baixa latência (UDP sem retransmissão)
    this.dataChannel = this.peerConnection.createDataChannel('input-events', {
      ordered: false,
      maxRetransmits: 0
    });

    this.peerConnection.ontrack = (event) => {
      if (event.streams && event.streams[0]) {
        this.remoteVideo.srcObject = event.streams[0];
        this.sessionOverlay.classList.add('hidden');
      }
    };

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.signalingWs.send(JSON.stringify({
          type: 'webrtc_candidate',
          target_id: this.connectedRemoteId,
          candidate: event.candidate
        }));
      }
    };
  }

  async handleWebRTCOffer(senderId, sdp) {
    if (!this.peerConnection) {
      this.startClientWebRTC();
    }
    await this.peerConnection.setRemoteDescription(new RTCSessionDescription(sdp));
    const answer = await this.peerConnection.createAnswer();
    await this.peerConnection.setLocalDescription(answer);

    this.signalingWs.send(JSON.stringify({
      type: 'webrtc_answer',
      target_id: senderId,
      sdp: answer
    }));
  }

  async handleWebRTCAnswer(sdp) {
    if (this.peerConnection) {
      await this.peerConnection.setRemoteDescription(new RTCSessionDescription(sdp));
    }
  }

  async handleNewICECandidate(candidate) {
    if (this.peerConnection && candidate) {
      try {
        await this.peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
      } catch (err) {
        console.error('Erro ao adicionar candidato ICE:', err);
      }
    }
  }

  // ==========================================
  // CAPTURA E INJEÇÃO DE EVENTOS DE ENTRADA
  // ==========================================

  setupRemoteInputListeners() {
    let lastMoveTime = 0;

    // Movimento do Mouse (com limitação suave para 60fps)
    this.remoteVideo.addEventListener('mousemove', (e) => {
      if (!this.isInputControlActive || !this.dataChannel || this.dataChannel.readyState !== 'open') return;

      const now = performance.now();
      if (now - lastMoveTime < 16) return; // ~60 FPS
      lastMoveTime = now;

      const norm = this.getNormalizedCoordinates(e);
      if (norm) {
        this.dataChannel.send(JSON.stringify({
          action: 'mouse_move',
          x: norm.x,
          y: norm.y
        }));
      }
    });

    // Clique pressionado (MouseDown)
    this.remoteVideo.addEventListener('mousedown', (e) => {
      if (!this.isInputControlActive || !this.dataChannel || this.dataChannel.readyState !== 'open') return;
      e.preventDefault();

      const norm = this.getNormalizedCoordinates(e);
      const btn = e.button === 0 ? 'left' : (e.button === 2 ? 'right' : 'middle');
      if (norm) {
        this.dataChannel.send(JSON.stringify({
          action: 'mouse_down',
          button: btn,
          x: norm.x,
          y: norm.y
        }));
      }
    });

    // Clique solto (MouseUp)
    this.remoteVideo.addEventListener('mouseup', (e) => {
      if (!this.isInputControlActive || !this.dataChannel || this.dataChannel.readyState !== 'open') return;
      e.preventDefault();

      const norm = this.getNormalizedCoordinates(e);
      const btn = e.button === 0 ? 'left' : (e.button === 2 ? 'right' : 'middle');
      if (norm) {
        this.dataChannel.send(JSON.stringify({
          action: 'mouse_up',
          button: btn,
          x: norm.x,
          y: norm.y
        }));
      }
    });

    // Scroll da Roda do Mouse
    this.remoteVideo.addEventListener('wheel', (e) => {
      if (!this.isInputControlActive || !this.dataChannel || this.dataChannel.readyState !== 'open') return;
      e.preventDefault();

      this.dataChannel.send(JSON.stringify({
        action: 'mouse_scroll',
        dy: -Math.sign(e.deltaY) * 5,
        dx: Math.sign(e.deltaX) * 5
      }));
    }, { passive: false });

    // Bloqueia menu de contexto do navegador para repassar botão direito do mouse
    this.remoteVideo.addEventListener('contextmenu', (e) => e.preventDefault());

    // Teclado
    window.addEventListener('keydown', (e) => {
      if (!this.isInputControlActive || this.remoteSessionView.classList.contains('hidden')) return;
      if (!this.dataChannel || this.dataChannel.readyState !== 'open') return;

      // Evita atalhos do navegador como F5 ou Cmd+R acidentais na sessão
      if (e.key === 'Tab' || e.key === 'Backspace' || e.key === 'Escape') {
        e.preventDefault();
      }

      if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        // Envia caracteres normais com acentos via Unicode
        this.dataChannel.send(JSON.stringify({
          action: 'type_text',
          text: e.key
        }));
      } else {
        // Teclas especiais (Enter, Backspace, Setas, etc.)
        this.dataChannel.send(JSON.stringify({
          action: 'key_down',
          key: e.key
        }));
      }
    });

    window.addEventListener('keyup', (e) => {
      if (!this.isInputControlActive || this.remoteSessionView.classList.contains('hidden')) return;
      if (!this.dataChannel || this.dataChannel.readyState !== 'open') return;

      this.dataChannel.send(JSON.stringify({
        action: 'key_up',
        key: e.key
      }));
    });
  }

  // Converte posição do cursor no elemento <video> para percentual exato da tela remota (0.0 a 1.0)
  getNormalizedCoordinates(e) {
    const rect = this.remoteVideo.getBoundingClientRect();
    const videoWidth = this.remoteVideo.videoWidth;
    const videoHeight = this.remoteVideo.videoHeight;

    if (!videoWidth || !videoHeight) return null;

    // Trata aspect-ratio com letterbox/pillarbox dentro da tag video
    const videoRatio = videoWidth / videoHeight;
    const containerRatio = rect.width / rect.height;

    let displayWidth, displayHeight, offsetX, offsetY;

    if (containerRatio > videoRatio) {
      displayHeight = rect.height;
      displayWidth = rect.height * videoRatio;
      offsetX = (rect.width - displayWidth) / 2;
      offsetY = 0;
    } else {
      displayWidth = rect.width;
      displayHeight = rect.width / videoRatio;
      offsetX = 0;
      offsetY = (rect.height - displayHeight) / 2;
    }

    const mouseX = e.clientX - rect.left - offsetX;
    const mouseY = e.clientY - rect.top - offsetY;

    const normX = Math.max(0, Math.min(1, mouseX / displayWidth));
    const normY = Math.max(0, Math.min(1, mouseY / displayHeight));

    return { x: normX, y: normY };
  }

  // ==========================================
  // FERRAMENTAS & CONTROLES DA SESSÃO
  // ==========================================

  toggleInputControl() {
    this.isInputControlActive = !this.isInputControlActive;
    if (this.isInputControlActive) {
      this.btnToggleInput.classList.add('active');
      this.btnToggleInput.textContent = 'Controle Ativo';
    } else {
      this.btnToggleInput.classList.remove('active');
      this.btnToggleInput.textContent = 'Apenas Visualização';
    }
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      this.remoteSessionView.requestFullscreen().catch(err => console.error(err));
    } else {
      document.exitFullscreen().catch(err => console.error(err));
    }
  }

  disconnectSession() {
    if (this.signalingWs && this.signalingWs.readyState === WebSocket.OPEN) {
      this.signalingWs.send(JSON.stringify({ type: 'disconnect_session' }));
    }
    this.resetSessionUI();
  }

  resetSessionUI() {
    if (this.peerConnection) {
      this.peerConnection.close();
      this.peerConnection = null;
    }
    if (this.dataChannel) {
      this.dataChannel.close();
      this.dataChannel = null;
    }
    this.remoteVideo.srcObject = null;
    this.remoteSessionView.classList.add('hidden');
    this.dashboardView.classList.remove('hidden');
    this.connectedRemoteId = null;
    if (document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
  }

  copyHostId() {
    if (!this.myHostId) return;
    navigator.clipboard.writeText(this.myHostId).then(() => {
      const orig = this.btnCopyId.innerHTML;
      this.btnCopyId.innerHTML = `
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
      `;
      setTimeout(() => this.btnCopyId.innerHTML = orig, 1500);
    });
  }
}

// Inicializa a aplicação quando a página carregar
window.addEventListener('DOMContentLoaded', () => {
  window.app = new RemoteDeskApp();
});
