"""
Injetor de eventos de teclado e mouse multiplataforma (macOS e Windows)
usando apenas a biblioteca padrão (ctypes).
"""
import sys
import time
import ctypes
from ctypes import Structure, c_double, c_uint32, c_void_p, c_bool, c_ulong, create_unicode_buffer

# Estrutura para pontos (x, y) no macOS
class CGPoint(Structure):
    _fields_ = [("x", c_double), ("y", c_double)]

class InputInjector:
    def __init__(self):
        self.platform = sys.platform
        self.screen_width = 1920
        self.screen_height = 1080
        self._init_platform()

    def _init_platform(self):
        if self.platform == "darwin":
            try:
                self.app = ctypes.cdll.LoadLibrary("/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices")
                
                # Configurar chamadas de exibição
                main_display = self.app.CGMainDisplayID()
                self.screen_width = self.app.CGDisplayPixelsWide(main_display)
                self.screen_height = self.app.CGDisplayPixelsHigh(main_display)
                
                # Assinaturas das funções do macOS
                self.app.CGEventCreateMouseEvent.restype = c_void_p
                self.app.CGEventCreateMouseEvent.argtypes = [c_void_p, c_uint32, CGPoint, c_uint32]
                
                self.app.CGEventPost.argtypes = [c_uint32, c_void_p]
                
                self.app.CGEventCreateKeyboardEvent.restype = c_void_p
                self.app.CGEventCreateKeyboardEvent.argtypes = [c_void_p, c_uint32, c_bool]
                
                self.app.CGEventKeyboardSetUnicodeString.restype = None
                self.app.CGEventKeyboardSetUnicodeString.argtypes = [c_void_p, c_ulong, ctypes.c_wchar_p]

                self.app.CGEventCreateScrollWheelEvent2.restype = c_void_p
                self.app.CGEventCreateScrollWheelEvent2.argtypes = [c_void_p, c_uint32, c_uint32, ctypes.c_int32, ctypes.c_int32]
                
                print(f"[InputInjector] macOS inicializado com sucesso. Resolução: {self.screen_width}x{self.screen_height}")
            except Exception as e:
                print(f"[InputInjector] Erro ao carregar ApplicationServices no macOS: {e}")

        elif self.platform.startswith("win"):
            try:
                self.user32 = ctypes.windll.user32
                self.screen_width = self.user32.GetSystemMetrics(0)
                self.screen_height = self.user32.GetSystemMetrics(1)
                print(f"[InputInjector] Windows inicializado com sucesso. Resolução: {self.screen_width}x{self.screen_height}")
            except Exception as e:
                print(f"[InputInjector] Erro ao carregar user32 no Windows: {e}")
        else:
            print(f"[InputInjector] Aviso: Plataforma {self.platform} não suporta injeção nativa direta.")

    def get_screen_resolution(self):
        return {"width": self.screen_width, "height": self.screen_height}

    def _normalize_coords(self, norm_x, norm_y):
        """Converte coordenadas normalizadas (0.0 a 1.0) para coordenadas reais de tela."""
        real_x = max(0, min(self.screen_width - 1, int(norm_x * self.screen_width)))
        real_y = max(0, min(self.screen_height - 1, int(norm_y * self.screen_height)))
        return real_x, real_y

    def mouse_move(self, norm_x, norm_y):
        real_x, real_y = self._normalize_coords(norm_x, norm_y)
        if self.platform == "darwin":
            # kCGEventMouseMoved = 5, kCGHIDEventTap = 0
            pt = CGPoint(float(real_x), float(real_y))
            evt = self.app.CGEventCreateMouseEvent(None, 5, pt, 0)
            if evt:
                self.app.CGEventPost(0, evt)
                # Liberar memória no CoreFoundation se necessário
        elif self.platform.startswith("win"):
            self.user32.SetCursorPos(real_x, real_y)

    def mouse_down(self, norm_x, norm_y, button="left"):
        real_x, real_y = self._normalize_coords(norm_x, norm_y)
        if self.platform == "darwin":
            pt = CGPoint(float(real_x), float(real_y))
            # 1: LeftMouseDown, 3: RightMouseDown, 25: OtherMouseDown
            evt_type = 1 if button == "left" else (3 if button == "right" else 25)
            btn_type = 0 if button == "left" else (1 if button == "right" else 2)
            evt = self.app.CGEventCreateMouseEvent(None, evt_type, pt, btn_type)
            if evt:
                self.app.CGEventPost(0, evt)
        elif self.platform.startswith("win"):
            self.user32.SetCursorPos(real_x, real_y)
            # MOUSEEVENTF_LEFTDOWN = 0x0002, MOUSEEVENTF_RIGHTDOWN = 0x0008, MOUSEEVENTF_MIDDLEDOWN = 0x0020
            flags = 0x0002 if button == "left" else (0x0008 if button == "right" else 0x0020)
            self.user32.mouse_event(flags, 0, 0, 0, 0)

    def mouse_up(self, norm_x, norm_y, button="left"):
        real_x, real_y = self._normalize_coords(norm_x, norm_y)
        if self.platform == "darwin":
            pt = CGPoint(float(real_x), float(real_y))
            # 2: LeftMouseUp, 4: RightMouseUp, 26: OtherMouseUp
            evt_type = 2 if button == "left" else (4 if button == "right" else 26)
            btn_type = 0 if button == "left" else (1 if button == "right" else 2)
            evt = self.app.CGEventCreateMouseEvent(None, evt_type, pt, btn_type)
            if evt:
                self.app.CGEventPost(0, evt)
        elif self.platform.startswith("win"):
            self.user32.SetCursorPos(real_x, real_y)
            # MOUSEEVENTF_LEFTUP = 0x0004, MOUSEEVENTF_RIGHTUP = 0x0010, MOUSEEVENTF_MIDDLEUP = 0x0040
            flags = 0x0004 if button == "left" else (0x0010 if button == "right" else 0x0040)
            self.user32.mouse_event(flags, 0, 0, 0, 0)

    def mouse_click(self, norm_x, norm_y, button="left"):
        self.mouse_move(norm_x, norm_y)
        self.mouse_down(norm_x, norm_y, button)
        time.sleep(0.01)
        self.mouse_up(norm_x, norm_y, button)

    def mouse_scroll(self, dy, dx=0):
        if self.platform == "darwin":
            # kCGScrollEventUnitPixel = 0
            evt = self.app.CGEventCreateScrollWheelEvent2(None, 0, 1, int(dy), int(dx))
            if evt:
                self.app.CGEventPost(0, evt)
        elif self.platform.startswith("win"):
            # MOUSEEVENTF_WHEEL = 0x0800
            self.user32.mouse_event(0x0800, 0, 0, int(dy * 120), 0)

    def type_unicode(self, text):
        """Digita texto diretamente com suporte completo a caracteres especiais e acentos."""
        if not text:
            return
        if self.platform == "darwin":
            for char in text:
                evt_down = self.app.CGEventCreateKeyboardEvent(None, 0, True)
                buf = create_unicode_buffer(char)
                self.app.CGEventKeyboardSetUnicodeString(evt_down, len(char), buf)
                self.app.CGEventPost(0, evt_down)
                
                evt_up = self.app.CGEventCreateKeyboardEvent(None, 0, False)
                self.app.CGEventKeyboardSetUnicodeString(evt_up, len(char), buf)
                self.app.CGEventPost(0, evt_up)
        elif self.platform.startswith("win"):
            for char in text:
                code = ord(char)
                # KEYEVENTF_UNICODE = 0x0004, KEYEVENTF_KEYUP = 0x0002
                self.user32.keybd_event(0, code, 0x0004, 0)
                self.user32.keybd_event(0, code, 0x0004 | 0x0002, 0)

    def key_press(self, key_name, down=True):
        """Trata teclas especiais como Enter, Backspace, Tab, Escape, Setas."""
        key_map_mac = {
            "enter": 36, "return": 36, "tab": 48, "space": 49, "backspace": 51,
            "escape": 53, "command": 55, "shift": 56, "control": 59, "alt": 58,
            "arrowleft": 123, "arrowright": 124, "arrowdown": 125, "arrowup": 126
        }
        key_map_win = {
            "enter": 0x0D, "return": 0x0D, "tab": 0x09, "space": 0x20, "backspace": 0x08,
            "escape": 0x1B, "shift": 0x10, "control": 0x11, "alt": 0x12,
            "arrowleft": 0x25, "arrowup": 0x26, "arrowright": 0x27, "arrowdown": 0x28
        }
        k = key_name.lower()
        if self.platform == "darwin":
            keycode = key_map_mac.get(k)
            if keycode is not None:
                evt = self.app.CGEventCreateKeyboardEvent(None, keycode, down)
                if evt:
                    self.app.CGEventPost(0, evt)
        elif self.platform.startswith("win"):
            vk_code = key_map_win.get(k)
            if vk_code is not None:
                flag = 0 if down else 0x0002
                self.user32.keybd_event(vk_code, 0, flag, 0)
