import webview, sys, os, requests, zipfile, subprocess, ctypes, time, json, re, threading, winreg
from ctypes import wintypes
from io import BytesIO

APP_NAME = "WaveOptimizer" 
VER = "V1.0 Stable (Acceleration Build)"

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CFG_FILE = os.path.join(BASE_DIR, "settings.json")

ROOT = r"C:\Program Files\WaveOptimizer"
FILES = os.path.join(ROOT, "files")
EX_HOSTS = os.path.join(FILES, "exclude-hosts.txt")
EX_IPS = os.path.join(FILES, "exclude-ips.txt")
ICON_NAME = "icon.ico"
URL_ZIP = "https://www.dropbox.com/scl/fi/fng2403wd9cr37mgrnm8a/standik.zip?rlkey=xog1r74io2h5fsmyci0y5ddsf&st=ec2wdxm1&dl=1"

STRATS = {
    "Standard Optimization": "standart.bat",
    "Alt Routing (Mode 1)": "standa.bat",
    "Alt Routing (Mode 2)": "standa2.bat",
    "Alt Routing (Mode 3)": "standa3.bat",
    "Packet Fragmentation": "standart234.bat",
    "Secure Handshake Opt": "standik.bat",
}

try:
    import pystray
    from PIL import Image, ImageDraw
    TRAY = True
except: TRAY = False

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

_GP = ctypes.windll.kernel32.GetShortPathNameW
_GP.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
_GP.restype = wintypes.DWORD

def short_path(p):
    if not os.path.exists(p): return p
    buf = ctypes.create_unicode_buffer(260)
    _GP(p, buf, 260)
    return buf.value

class Api:
    def __init__(self):
        self.w = None
        self.t = None

    def set_w(self, w): self.w = w
    def set_t(self, t): self.t = t
    def min(self): self.w.minimize() if self.w else None
    
    def drag(self):
        if self.w:
            ctypes.windll.user32.ReleaseCapture()
            ctypes.windll.user32.SendMessageW(ctypes.windll.user32.GetForegroundWindow(), 0xA1, 2, 0)

    def close_req(self):
        c = self.get_cfg()
        if c.get('tray', False) and TRAY:
            self.w.hide() if self.w else None

            self.t.notify("WaveOptimizer minimized to tray", APP_NAME) if self.t else None
        else: self.quit()

    def quit(self):
        if self.get_cfg().get('kill_on_exit', True): self.kill()
        if self.t: self.t.stop()
        os._exit(0)

    def set_lang(self, lang):
        if not self.t: return
        txt_op = "Открыть" if lang == 'ru' else "Open"
        txt_ex = "Выход" if lang == 'ru' else "Quit"
        
        def on_open(icon, item):
            if self.w:
                self.w.show()
                self.w.restore()
        
        self.t.menu = pystray.Menu(
            pystray.MenuItem(txt_op, on_open, default=True),
            pystray.MenuItem(txt_ex, lambda i, It: self.quit())
        )
        self.t.update_menu()

    def find_exe(self):
        for root, dirs, files in os.walk(ROOT):
            if "winws.exe" in files:
                return os.path.join(root, "winws.exe")
        return None

    def run(self, fname):
        self.kill()
        exe = self.find_exe()
        if not exe:
            if self.w: self.w.evaluate_js("log('CRITICAL: Core engine not found! Re-initializing...', 'err')")
            init_files(force=True)
            exe = self.find_exe()
            if not exe: return
        s_h, s_i = short_path(EX_HOSTS), short_path(EX_IPS)
        
        args = ""
        if os.path.exists(EX_HOSTS) and os.path.getsize(EX_HOSTS) > 0: args += f' --hostlist-exclude="{s_h}"'
        if os.path.exists(EX_IPS) and os.path.getsize(EX_IPS) > 0: args += f' --ipset-exclude="{s_i}"'

        bp = os.path.join(ROOT, fname)
        if not os.path.exists(bp):
             for root, _, files in os.walk(ROOT):
                 if fname in files:
                     bp = os.path.join(root, fname)
                     break
        
        if not os.path.exists(bp): return

        try:
            with open(bp, 'r', encoding='utf-8', errors='ignore') as f: c = f.read()
            
            safe_exe = exe.replace('\\', '\\\\')
            full_cmd = f'"{safe_exe}" {args}'
            
            safe_replacement = full_cmd.replace('\\', '\\\\')
            
            c = re.sub(r'(?i)(?:[\"\']?[\w\s\\\/\.\-\~%]+)?winws\.exe[\"\']?', safe_replacement, c)
            
            tb = os.path.join(ROOT, "run_tmp.bat")
            with open(tb, 'w', encoding='utf-8') as f: f.write(c)
            
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.Popen([tb], cwd=os.path.dirname(exe), shell=True, startupinfo=si)
        except Exception as e:
            if self.w: self.w.evaluate_js(f"log('Err: {str(e).replace(chr(92), '/')}', 'err')")

    def kill(self):
        subprocess.run("taskkill /f /im winws.exe", shell=True, stdout=subprocess.DEVNULL)

    def check(self, u):
        try: return requests.head(u, timeout=2.5).status_code < 400
        except: return False

    def scan(self):
        self.kill()
        for s in ["standart.bat", "standa.bat", "standik.bat"]:
            if self.w: self.w.evaluate_js(f"log('Testing bandwidth mode: {s}...')")
            self.run(s)
            time.sleep(4)
            r = [self.check(x) for x in ["https://www.youtube.com", "https://discord.com", "https://www.roblox.com"]]
            if self.w: self.w.evaluate_js(f"updSt({str(r[0]).lower()},{str(r[1]).lower()},{str(r[2]).lower()})")
            if r[0] and r[1]: return s
            self.kill()
        return None

    def get_cfg(self):
        if os.path.exists(CFG_FILE):
            try:
                with open(CFG_FILE, 'r') as f: return json.load(f)
            except: pass
        return {}

    def save_cfg(self, js):
        d = json.loads(js)
        with open(CFG_FILE, 'w') as f: f.write(js)
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            if d.get('autorun', False):
                winreg.SetValueEx(k, "WaveOptimizer", 0, winreg.REG_SZ, f'"{sys.executable}"')
            else:
                try: winreg.DeleteValue(k, "WaveOptimizer")
                except: pass
            winreg.CloseKey(k)
        except: pass

    def io_file(self, t, c=None):
        p = EX_HOSTS if t == 'hosts' else EX_IPS
        if c is not None:
            with open(p, 'w') as f: f.write(c)
        else:
            return open(p, 'r').read() if os.path.exists(p) else ""

api = Api()

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Unbounded:wght@400;600;900&display=swap');
:root{--bg:#050505;--g:rgba(255,255,255,0.03);--gb:rgba(255,255,255,0.08);--t:#fff;--td:#888;--ac:#10b981;--warn:#f59e0b;--err:#ef4444;--rad:24px}
*{box-sizing:border-box;user-select:none;outline:none}
body{background:0 0;color:var(--t);font-family:'Inter',sans-serif;margin:0;height:100vh;overflow:hidden;border-radius:var(--rad)}
.tb{position:absolute;top:0;left:0;width:100%;height:40px;z-index:1000;display:flex;justify-content:flex-end;align-items:center;padding-right:15px}
.dz{position:absolute;top:0;left:0;width:100%;height:100%;z-index:-1}
.wb{width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;cursor:pointer;margin-left:8px;background:rgba(255,255,255,0.05);transition:.2s;z-index:1001}
.wb:hover{background:rgba(255,255,255,0.2)}.wb.cl:hover{background:#ef4444}
.wb svg{width:12px;height:12px;fill:#fff}
.wrap{background:#080808;height:100%;border:1px solid var(--gb);border-radius:var(--rad);padding:30px;display:flex;flex-direction:column;position:relative;overflow:hidden}
.orb{position:absolute;border-radius:50%;filter:blur(90px);opacity:.3;z-index:0;pointer-events:none}
.o1{width:250px;height:250px;background:#10b981;top:-60px;left:-60px}
.o2{width:180px;height:180px;background:#059669;bottom:-40px;right:-40px}
.main{position:relative;z-index:10;height:100%;display:flex;flex-direction:column}
h1{font-family:'Unbounded';font-weight:800;font-size:34px;margin:20px 0 5px;background:linear-gradient(135deg,#fff 30%,#34d399 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.ver{font-size:10px;color:var(--td);font-weight:600;letter-spacing:2px;margin-bottom:15px;text-transform:uppercase}
.beta-warn{font-size:10px;color:var(--warn);background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);padding:6px 10px;border-radius:8px;margin-bottom:15px;display:flex;align-items:center;gap:6px;font-weight:600}
.sel{position:relative;width:100%;cursor:pointer;margin-bottom:15px}
.sh{background:var(--g);border:1px solid var(--gb);border-radius:18px;padding:16px 20px;display:flex;justify-content:space-between;align-items:center;font-family:'Unbounded';font-size:11px;font-weight:600}
.dl{position:absolute;top:110%;width:100%;background:#111;border:1px solid var(--gb);border-radius:18px;overflow:hidden;z-index:100;opacity:0;pointer-events:none;transform:translateY(-10px);transition:.2s;box-shadow:0 15px 40px rgba(0,0,0,0.6)}
.sel.act .dl{opacity:1;pointer-events:all;transform:translateY(0)}
.opt{padding:14px 20px;font-size:12px;color:var(--td);border-bottom:1px solid rgba(255,255,255,0.03);transition:.2s}
.opt:hover{background:var(--g);color:#fff}
.btn{width:100%;height:55px;border-radius:18px;border:none;background:#fff;color:#000;font-family:'Unbounded';font-weight:800;font-size:13px;cursor:pointer;margin-top:auto;transition:.3s}
.btn:hover{transform:scale(1.02)}.btn:active{transform:scale(.96)}.btn.stop{background:#ef4444;color:#fff}
.sb{display:flex;gap:8px;margin-top:15px}
.si{flex:1;height:32px;border-radius:10px;background:rgba(255,255,255,0.03);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:600;color:var(--td);border:1px solid transparent;transition:.3s}
.si.act{border-color:var(--ac);color:#fff;background:rgba(16,185,129,0.15)}
.log{height:100px;margin-top:15px;overflow-y:auto;font-family:monospace;font-size:9px;color:var(--td);mask-image:linear-gradient(to bottom,#000 80%,transparent 100%)}
.ll{margin-bottom:4px;display:flex;gap:8px}.lok{color:#34d399}.ler{color:#f87171}
.tools{display:flex;gap:10px;margin-bottom:10px}
.tb-i{width:32px;height:32px;border-radius:10px;background:rgba(255,255,255,0.05);display:flex;align-items:center;justify-content:center;cursor:pointer;transition:.2s}
.tb-i:hover{background:rgba(255,255,255,0.15)}
.tb-i svg{width:14px;fill:#fff;opacity:.7}
.sw{width:40px;height:22px;background:rgba(255,255,255,0.1);border-radius:20px;position:relative;cursor:pointer;transition:.3s}
.sw::after{content:'';position:absolute;top:3px;left:3px;width:16px;height:16px;background:#fff;border-radius:50%;transition:.3s}
.sw.chk{background:var(--ac)}.sw.chk::after{transform:translateX(18px)}
.modal{position:absolute;top:0;left:0;width:100%;height:100%;background:rgba(5,5,5,0.95);backdrop-filter:blur(20px);z-index:2000;padding:30px;display:flex;flex-direction:column;opacity:0;pointer-events:none;transition:.4s}
.modal.act{opacity:1;pointer-events:all}
.box{border:1px solid var(--gb);background:rgba(255,255,255,0.02);padding:25px;border-radius:20px}
.l-txt{font-size:11px;color:var(--td);line-height:1.6;margin-bottom:25px;height:150px;overflow-y:auto;padding:10px 0;border-top:1px solid var(--gb);border-bottom:1px solid var(--gb)}
.row{display:flex;justify-content:space-between;align-items:center;margin-bottom:25px;padding-bottom:15px;border-bottom:1px solid var(--gb)}
.ta{width:100%;height:120px;background:var(--g);border:1px solid var(--gb);color:#fff;border-radius:10px;padding:10px;font-size:10px;resize:none;margin-bottom:10px}
.flags{display:flex;justify-content:center;gap:30px;margin-top:40px}
.flag{width:80px;height:60px;border-radius:12px;cursor:pointer;transition:.3s;border:2px solid transparent;opacity:0.6;display:flex;flex-direction:column;align-items:center;gap:10px}
.flag:hover{opacity:1;transform:scale(1.1)}
.flag.sel-f{border-color:var(--ac);opacity:1}
.flag svg{width:40px;height:30px;border-radius:4px}
::-webkit-scrollbar{width:0}
</style>
</head>
<body>
<div id="lang-modal" class="modal act" style="z-index:3500;text-align:center;justify-content:center">
    <h2 style="font-family:'Unbounded'">LANGUAGE</h2>
    <div class="flags">
        <div class="flag" onclick="setLang('ru')">
             <svg viewBox="0 0 640 480"><path fill="#fff" d="M0 0h640v160H0z"/><path fill="#0039a6" d="M0 160h640v160H0z"/><path fill="#d52b1e" d="M0 320h640v160H0z"/></svg>
             <span style="font-size:10px;font-weight:600">RUSSIAN</span>
        </div>
        <div class="flag" onclick="setLang('en')">
             <svg viewBox="0 0 640 480"><path fill="#b22234" d="M0 0h640v480H0"/><path fill="#3c3b6e" d="M0 0h260v222H0"/><g fill="#fff"><path d="M0 45h640v40H0M0 137h640v40H0M0 228h640v40H0M0 320h640v40H0M0 411h640v40H0M260 45h380v40H260M260 137h380v40H260"/></g><g fill="#fff"><circle cx="21" cy="21" r="9"/><circle cx="21" cy="65" r="9"/><circle cx="21" cy="110" r="9"/><circle cx="21" cy="154" r="9"/><circle cx="21" cy="198" r="9"/><circle cx="65" cy="21" r="9"/><circle cx="65" cy="65" r="9"/><circle cx="65" cy="110" r="9"/><circle cx="65" cy="154" r="9"/><circle cx="65" cy="198" r="9"/><circle cx="108" cy="21" r="9"/><circle cx="108" cy="65" r="9"/><circle cx="108" cy="110" r="9"/><circle cx="108" cy="154" r="9"/><circle cx="108" cy="198" r="9"/><circle cx="152" cy="21" r="9"/><circle cx="152" cy="65" r="9"/><circle cx="152" cy="110" r="9"/><circle cx="152" cy="154" r="9"/><circle cx="152" cy="198" r="9"/><circle cx="195" cy="21" r="9"/><circle cx="195" cy="65" r="9"/><circle cx="195" cy="110" r="9"/><circle cx="195" cy="154" r="9"/><circle cx="195" cy="198" r="9"/><circle cx="239" cy="21" r="9"/><circle cx="239" cy="65" r="9"/><circle cx="239" cy="110" r="9"/><circle cx="239" cy="154" r="9"/><circle cx="239" cy="198" r="9"/></g></svg>
             <span style="font-size:10px;font-weight:600">ENGLISH</span>
        </div>
    </div>
</div>

<div id="legal-modal" class="modal" style="z-index:3000;text-align:center;justify-content:center">
    <h2 style="font-family:'Unbounded';margin-bottom:10px" data-key="legal_title">LICENSE</h2>
    <div class="box">
        <div class="l-txt" id="legal-content"></div>
        <button class="btn" style="background:var(--ac);color:#fff" onclick="accLeg()" data-key="legal_btn">ACCEPT</button>
    </div>
</div>

<div id="cfg-modal" class="modal">
    <h2 style="font-family:'Unbounded';margin-bottom:30px" data-key="set_title">SETTINGS</h2>
    <div class="row"><span data-key="set_tray">Tray on Close</span><div class="sw" id="tg-tray" onclick="tSw('tg-tray')"></div></div>
    <div class="row"><span data-key="set_auto">Autorun</span><div class="sw" id="tg-auto" onclick="tSw('tg-auto')"></div></div>
    <div class="row"><span data-key="set_kill">Close Engine on Exit</span><div class="sw" id="tg-kill" onclick="tSw('tg-kill')"></div></div>
    <div class="row"><span data-key="set_scan">Auto-Optimize</span><div class="sw" id="tg-check" onclick="tSw('tg-check')"></div></div>
    <button class="btn" onclick="tSet()" style="background:#222;color:#fff" data-key="back">BACK</button>
</div>

<div id="ex-modal" class="modal">
    <h2 style="font-family:'Unbounded';margin-bottom:20px" data-key="ex_title">ROUTING RULES</h2>
    <span style="color:var(--ac);font-size:10px;font-weight:700">IGNORE DOMAINS</span>
    <textarea id="txt-hosts" class="ta"></textarea>
    <span style="color:var(--ac);font-size:10px;font-weight:700">IGNORE IPS / CIDR</span>
    <textarea id="txt-ips" class="ta"></textarea>
    <div style="display:flex;gap:10px;margin-top:auto">
        <button class="btn" style="background:#222;color:#fff" onclick="tEx()" data-key="cancel">CANCEL</button>
        <button class="btn" onclick="sEx()" data-key="save">APPLY RULES</button>
    </div>
</div>

<div class="wrap">
    <div class="orb o1"></div><div class="orb o2"></div>
    <div class="tb"><div class="dz" onmousedown="pywebview.api.drag()"></div>
        <div class="wb" onclick="pywebview.api.min()"><svg viewBox="0 0 24 24"><path d="M5 12h14v2H5z"/></svg></div>
        <div class="wb cl" onclick="pywebview.api.close_req()"><svg viewBox="0 0 24 24"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12 19 6.41z"/></svg></div>
    </div>
    <div class="main">
        <div class="tools">
            <div class="tb-i" onclick="runScan()"><svg viewBox="0 0 24 24"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-2.5-2.5"/></svg></div>
            <div class="tb-i" onclick="tEx()"><svg viewBox="0 0 24 24"><path d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/></svg></div>
            <div class="tb-i" onclick="tSet()"><svg viewBox="0 0 24 24"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.56-1.62-.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.03-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6 3.6z"/></svg></div>
        </div>
        <h1>WaveOptimizer</h1>
        <div class="ver">[[VER]]</div>
        <div class="beta-warn" title="Experimental Build">
            <svg viewBox="0 0 24 24" style="width:14px;fill:var(--warn)"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
            EXPERIMENTAL OPTIMIZATION BUILD
        </div>
        <div class="sel" onclick="this.classList.toggle('act')">
            <div class="sh"><span id="c-strat">Standard Optimization</span><span style="opacity:.5">▼</span></div>
            <div class="dl" id="dd"></div>
        </div>
        <input type="hidden" id="strat-v" value="standart.bat">
        <div class="sb"><div class="si" id="s-yt">YouTube</div><div class="si" id="s-ds">Discord</div><div class="si" id="s-rb">Roblox</div></div>
        <div class="log" id="cons"></div>
        <button class="btn" id="btn-run" onclick="tRun()" data-key="launch">OPTIMIZE NETWORK</button>
    </div>
</div>
<script>
let run=false, cfg={};
const TEXTS = {
    ru: {
        legal_title: "ЛИЦЕНЗИОННОЕ СОГЛАШЕНИЕ",
        legal_btn: "ПРИНЯТЬ УСЛОВИЯ",
        // Текст полностью переписан под "Ускоритель"
        legal_text: "<b>WaveOptimizer — TRAFFIC ACCELERATOR</b><br><br>WaveOptimizer является инструментом с открытым исходным кодом, предназначенным для оптимизации маршрутизации сетевых пакетов и снижения задержек (ping) в нестабильных сетях.<br><br>Программное обеспечение работает путем фрагментации пакетов для улучшения прохождения через загруженные узлы связи. Нажимая кнопку, вы подтверждаете, что используете ПО для улучшения качества собственного сетевого соединения.",
        set_title: "НАСТРОЙКИ", set_tray: "Сворачивать в трей", set_auto: "Запуск с Windows", set_kill: "Выгружать драйвер при выходе", set_scan: "Авто-оптимизация",
        back: "НАЗАД", ex_title: "ИСКЛЮЧЕНИЯ", cancel: "ОТМЕНА", save: "СОХРАНИТЬ",
        launch: "УСКОРИТЬ СЕТЬ", stop: "ОСТАНОВИТЬ"
    },
    en: {
        legal_title: "USER AGREEMENT",
        legal_btn: "ACCEPT & CONTINUE",
        legal_text: "<b>WaveOptimizer — TRAFFIC ACCELERATOR</b><br><br>WaveOptimizer is an open-source network utility designed to optimize packet routing and reduce latency (ping) in unstable network environments.<br><br>This software operates by fragmenting packets to ensure better stability through congested nodes. By proceeding, you acknowledge that this tool is used solely for improving your personal network connection quality.",
        set_title: "SETTINGS", set_tray: "Minimize to Tray", set_auto: "Start with Windows", set_kill: "Kill Engine on Exit", set_scan: "Auto-Optimize on Startup",
        back: "BACK", ex_title: "ROUTING EXCEPTIONS", cancel: "CANCEL", save: "SAVE",
        launch: "OPTIMIZE NETWORK", stop: "STOP ACCELERATION"
    }
};
function setLang(l){
    const t = TEXTS[l];
    document.querySelectorAll('[data-key]').forEach(e => e.innerText = t[e.dataset.key]);
    document.getElementById('legal-content').innerHTML = t['legal_text'];
    pywebview.api.set_lang(l);
    document.getElementById('lang-modal').classList.remove('act');
    document.getElementById('legal-modal').classList.add('act');
}
function init(s, c) {
    const d = document.getElementById('dd');
    for(let n in s){
        let i = document.createElement('div');
        i.className='opt'; i.innerText=n;
        i.onclick=(e)=>{e.stopPropagation();document.getElementById('c-strat').innerText=n;document.getElementById('strat-v').value=s[n];document.querySelector('.sel').classList.remove('act')};
        d.appendChild(i);
    }
    cfg=c;
    if(c.tray) document.getElementById('tg-tray').classList.add('chk');
    if(c.autorun) document.getElementById('tg-auto').classList.add('chk');
    if(c.autoselect) document.getElementById('tg-check').classList.add('chk');
    if(c.kill_on_exit!==false) document.getElementById('tg-kill').classList.add('chk');
}
function accLeg() {
    document.getElementById('legal-modal').classList.remove('act');
    if(cfg.autoselect) setTimeout(runScan, 500);
}
function tSw(id) { document.getElementById(id).classList.toggle('chk'); saveC(); }
function tSet() { document.getElementById('cfg-modal').classList.toggle('act'); }
function tEx() {
    const m = document.getElementById('ex-modal');
    m.classList.toggle('act');
    if(m.classList.contains('act')) {
        pywebview.api.io_file('hosts').then(t=>document.getElementById('txt-hosts').value=t);
        pywebview.api.io_file('ips').then(t=>document.getElementById('txt-ips').value=t);
    }
}
function sEx() {
    pywebview.api.io_file('hosts', document.getElementById('txt-hosts').value);
    pywebview.api.io_file('ips', document.getElementById('txt-ips').value);
    tEx(); log("Routing rules updated", "ok");
}
function tRun() {
    const b = document.getElementById('btn-run');
    const lang = document.getElementById('legal-content').innerHTML.includes('ПО') ? 'ru' : 'en';
    if(!run) {
        run=true;
        pywebview.api.run(document.getElementById('strat-v').value);
        b.innerHTML=TEXTS[lang].stop; b.classList.add('stop');
        log("Optimization active", 'ok');
    } else {
        run=false; pywebview.api.kill();
        b.innerHTML=TEXTS[lang].launch; b.classList.remove('stop');
        log("Optimization stopped");
    }
}
function log(m, s='') {
    const c = document.getElementById('cons');
    c.innerHTML = `<div class="ll"><span style="opacity:.5">●</span><span>${m}</span><span style="margin-left:auto" class="${s=='ok'?'lok':s=='err'?'ler':''}">${s?s.toUpperCase():''}</span></div>` + c.innerHTML;
}
function runScan() {
    if(run) return;
    log("Analyzing network...");
    document.getElementById('btn-run').style.opacity='0.5';
    pywebview.api.scan().then(b => {
        document.getElementById('btn-run').style.opacity='1';
        if(b) { log("Best route found", "ok"); document.getElementById('strat-v').value=b; tRun(); }
        else log("Optimization failed", "err");
    });
}
function updSt(y,d,r) {
    const f=(i,v)=>document.getElementById(i).classList.toggle('act', v);
    f('s-yt',y); f('s-ds',d); f('s-rb',r);
}
function saveC() {
    pywebview.api.save_cfg(JSON.stringify({
        tray: document.getElementById('tg-tray').classList.contains('chk'),
        autorun: document.getElementById('tg-auto').classList.contains('chk'),
        autoselect: document.getElementById('tg-check').classList.contains('chk'),
        kill_on_exit: document.getElementById('tg-kill').classList.contains('chk')
    }));
}
window.onclick = e => { if(!e.target.closest('.sel')) document.querySelector('.sel').classList.remove('act'); }
</script>
</body>
</html>
"""

def init_files(force=False):
    if not os.path.exists(ROOT): os.makedirs(ROOT)
    if not os.path.exists(FILES): os.makedirs(FILES)
    
    has_exe = False
    for r, d, f in os.walk(ROOT):
        if "winws.exe" in f: has_exe = True
    
    if not has_exe or force:
        try:
            r = requests.get(URL_ZIP)
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(ROOT)
        except: pass
    for x in [EX_HOSTS, EX_IPS]: 
        if not os.path.exists(x): open(x,'w').close()

def main():
    init_files()
    w = webview.create_window(APP_NAME, html=HTML.replace("[[VER]]", VER), width=380, height=720, resizable=False, frameless=True, easy_drag=False, hidden=True, background_color='#000000', js_api=api)
    api.set_w(w)
    
    w.events.loaded += lambda: [w.evaluate_js(f"init({json.dumps(STRATS)}, {json.dumps(api.get_cfg())})"), time.sleep(0.1), w.show()]
    w.events.closing += lambda: api.close_req() or False

    if TRAY:
        def tr_op(icon, item): w.show(); w.restore()
        
        icon_path = resource_path(ICON_NAME)
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
        else:
            img = Image.new('RGB', (64, 64), (16, 185, 129))

        menu = pystray.Menu(pystray.MenuItem('Open', tr_op, default=True), pystray.MenuItem('Quit', api.quit))
        api.set_t(pystray.Icon("WaveOptimizer", img, "WaveOptimizer", menu))
        threading.Thread(target=api.t.run, daemon=True).start()

    webview.start(gui='edgechromium', debug=False)

if __name__ == "__main__":
    if not ctypes.windll.shell32.IsUserAnAdmin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
    else:
        main()
