import tkinter as tk
from tkinter import ttk, colorchooser, filedialog
import psutil
import datetime
import json
import os
import random
import ctypes
import time
import re
import tkinter.simpledialog
import tkinter.messagebox
import subprocess
import sys
import threading
import shutil
import platform
import urllib.parse
import stat

try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False

try:
    import pystray
    from PIL import Image as PILImage
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False
    print("WARNING: 'pystray' or 'Pillow' not found. System tray icon disabled.")

from features.snapshot import SnapshotMixin
from features.launcher import LauncherMixin
from features.housekeeper import HousekeeperMixin
from features.dev_sentinel import DevSentinelMixin
from features.memory_bank import MemoryBankMixin
from features.search import SearchMixin
from features.wellness import WellnessMixin
from features.animation import IdleAnimationMixin

MAGIC_BG_COLOR = '#abcdef' 
TEMP_PATH = os.path.expandvars(r'%LOCALAPPDATA%\Temp')
TIME_MULTIPLIER = 1 

# --- SAFE APPDATA PATHS (Crucial for Program Files installation) ---
APP_DATA_PATH = os.path.expandvars(r'%APPDATA%\Buddy')
if not os.path.exists(APP_DATA_PATH):
    os.makedirs(APP_DATA_PATH)

SETTINGS_FILE = os.path.join(APP_DATA_PATH, 'settings.json')
SHIFTS_FILE = os.path.join(APP_DATA_PATH, 'work_shift_presets.json')
DRAFT_FILE = os.path.join(APP_DATA_PATH, 'draft_book.txt')

# --- WINDOWS PREMIUM UI STRUCTURES ---
class ACCENT_POLICY(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint)
    ]

class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_uint),
        ("Data", ctypes.POINTER(ACCENT_POLICY)),
        ("SizeOfData", ctypes.c_size_t)
    ]

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BuddyApp(SnapshotMixin, LauncherMixin, HousekeeperMixin, DevSentinelMixin, MemoryBankMixin, SearchMixin, WellnessMixin, IdleAnimationMixin):
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.start_time = time.time() 

        # --- INIT FLAGS ---
        self.is_gaming = False  
        self.is_talking = False 
        self.is_showing_bubble = False 
        self.msg_queue = [] 
        
        # --- THEME ENGINE ---
        self.themes = {
            'dark': {'bg': '#1e1e1e', 'fg': '#ffffff', 'accent': '#00ffcc', 'surface': '#2d2d2d', 'text_secondary': '#aaaaaa', 'border': '#3d3d3d'},
            'light': {'bg': '#f5f5f5', 'fg': '#1e1e1e', 'accent': '#0078d4', 'surface': '#ffffff', 'text_secondary': '#666666', 'border': '#cccccc'}
        }
        self.current_theme_mode = 'dark'
        self.theme = self.themes[self.current_theme_mode].copy()
        self.glass_mode = True
        self.glass_tint = 0x99000000
        self.game_apps = [] 

        self.current_corner = "bottom_right"
        self.safe_apps = ['spotify.exe', 'vlc.exe', 'itunes.exe', 'wmplayer.exe', 'aimp.exe']
        self.nokill_apps = ['explorer.exe', 'system', 'system idle process', 'svchost.exe', 'services.exe', 'lsass.exe', 'wininit.exe', 'csrss.exe', 'smss.exe', 'dwm.exe', 'conhost.exe', 'python.exe', 'pythonw.exe', 'main.py']
        self.last_cleanup_date = "01/01/2000"
        
        # STATE FLAGS
        self.sarcasm_timer_id = None; self.conversation_timer_id = None; self.session_start_time = time.time() 
        self.shown_wellness_checks = []; self.last_move_request_time_virtual = 0; self.annoyance_level = 0
        self.is_afk = False; self.high_ram_warned = False; self.high_cpu_warned = False; self.low_storage_warned = False
        self.launch_on_startup = False

        # DATA
        self.app_index = []; self.launcher_window = None; self.launcher_listbox = None; self.launcher_entry = None; self.current_matches = []
        self.shift_presets = {}; self.active_shift = None
        self.clipboard_history = []; self.last_clipboard_content = ""; self.memory_window = None; self.memory_listbox = None
        self.snap_canvas = None; self.snap_start_x = None; self.snap_start_y = None; self.snap_rect_id = None
        self.search_window = None; self.search_entry = None; self.preferred_browser_path = ""
        self.daily_stats = {}; self.known_editors = ['code.exe', 'idea64.exe', 'pycharm64.exe', 'sublime_text.exe', 'notepad++.exe', 'atom.exe', 'code-insiders.exe', 'javaw.exe', 'WindowsTerminal.exe', 'wt.exe', 'cmd.exe']

        # BACKUP DATA (Multiple sources list)
        self.backup_sources = [] 
        self.backup_dest = ""; self.backup_freq = "daily"
        self.backup_denied = False; self.backup_ignored_once = False
        self.draft_window = None

        self.dialogues = {
            'janitor_found': ["Whoa, your desktop is getting messy.", "I see some junk on the desktop. Shall I clean it?"],
            'janitor_done': ["Desktop is spick and span!", "All moved to the archive. Much better."],
            'janitor_denied': ["Okay, I'll leave the mess.", "Suit yourself, it's your desktop."],
            'duplicate_found': ["I see some duplicate files in Downloads.", "Found duplicates wasting space. Delete them?"],
            'duplicate_done': ["Duplicates destroyed. Space saved!", "Cleaned up the duplicates. Nice and tidy."],
            'duplicate_denied': ["Okay, keeping all copies.", "I'll leave the duplicates alone."],
            'shift_launched': ["Shift started. Let's get to work.", "Opening your tools now."],
            'gaming_start': ["Have fun! I'll pause my animations for you.", "Fullscreen app detected! Pausing animations. GLHF!"],
            'gaming_end': ["Hey! I'm back!", "Welcome back! Good session?", "I'm back."]
        }
        
        self.load_settings()
        self.setup_system_tray()
        self.show_loading_screen()

    def say(self, category): return random.choice(self.dialogues.get(category, ["..."]))

    # --- SYSTEM TRAY ---
    def setup_system_tray(self):
        if not TRAY_AVAILABLE: return
        try:
            image = PILImage.open(resource_path('buddy_icon.ico'))
            menu = pystray.Menu(
                pystray.MenuItem('Show Buddy', self.restore_from_tray, default=True),
                pystray.MenuItem('Exit', self.close_app)
            )
            self.tray_icon = pystray.Icon("Buddy", image, "Buddy App", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Tray icon failed: {e}")

    def restore_from_tray(self, icon=None, item=None):
        self.root.deiconify()
        self.restore_position()

    # --- MESSAGE QUEUE (With Urgent Interrupts!) ---
    def queue_message(self, message, duration=5000, animation='Talking', button_text=None, button_command=None, is_urgent=False):
        if is_urgent and self.is_showing_bubble:
            # Emergency! Destroy current bubble and clear queue so this shows IMMEDIATELY
            if self.bubble_win and self.bubble_win.winfo_exists():
                self.bubble_win.destroy()
                self.bubble_win = None
                self.bubble_content_frame = None
            self.msg_queue.clear()
            self.is_showing_bubble = False
            
        self.msg_queue.append({'msg': message, 'dur': duration, 'anim': animation, 'btn': button_text, 'cmd': button_command})
        if not self.is_showing_bubble:
            self.process_queue()

    def process_queue(self):
        if not self.msg_queue:
            self.is_showing_bubble = False
            return
        self.is_showing_bubble = True
        item = self.msg_queue.pop(0)
        self.show_speech_bubble(item['msg'], item['dur'], item['btn'], item['cmd'], item['anim'])

    # --- THEMING & VISUALS ---
    def apply_premium_ui(self, window):
        try:
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
            DWMWCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(ctypes.c_int(DWMWCP_ROUND)), ctypes.sizeof(ctypes.c_int))
            accent = ACCENT_POLICY()
            if self.glass_mode:
                accent.AccentState = 4; accent.AccentFlags = 2; accent.GradientColor = self.glass_tint 
            else:
                accent.AccentState = 0
            data = WINDOWCOMPOSITIONATTRIBDATA(); data.Attribute = 19; data.Data = ctypes.pointer(accent); data.SizeOfData = ctypes.sizeof(accent)
            ctypes.windll.user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        except Exception: pass 

    def update_menu_colors(self):
        def update_menu(menu):
            try:
                menu.config(bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'])
                for i in range(menu.index(tk.END) + 1):
                    try:
                        if menu.type(i) == 'cascade':
                            update_menu(menu.nametowidget(menu.entrycget(i, 'menu')))
                    except: pass
            except: pass
        update_menu(self.main_menu)

    def toggle_theme_mode(self):
        self.current_theme_mode = 'light' if self.current_theme_mode == 'dark' else 'dark'
        self.theme = self.themes[self.current_theme_mode].copy(); self.save_settings()
        self.update_menu_colors() 
        self.queue_message(f"Switched to {self.current_theme_mode} mode!", 2000)

    def change_accent_color(self):
        color = colorchooser.askcolor(title="Choose Accent Color", initialcolor=self.theme['accent'])
        if color and color[1]: self.theme['accent'] = color[1]; self.save_settings(); self.update_menu_colors(); self.queue_message("Accent color updated!", 2000)

    def toggle_glass_mode(self):
        self.glass_mode = not self.glass_mode; self.save_settings()
        self.queue_message(f"Glass Mode {'ON' if self.glass_mode else 'OFF'}!", 2000)

    def set_glass_heavy(self): self.glass_tint = 0x99000000; self.save_settings(); self.queue_message("Heavy Glass Tint", 2000)
    def set_glass_medium(self): self.glass_tint = 0x66000000; self.save_settings(); self.queue_message("Medium Glass Tint", 2000)
    def set_glass_light(self): self.glass_tint = 0x33000000; self.save_settings(); self.queue_message("Light Glass Tint", 2000)

    # --- ALWAYS ON TOP MANAGER ---
    def manage_topmost(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if hwnd == self.root.winfo_id():
                self.root.attributes('-topmost', True)
            else:
                rect = ctypes.wintypes.RECT()
                ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                sw = ctypes.windll.user32.GetSystemMetrics(0)
                sh = ctypes.windll.user32.GetSystemMetrics(1)
                is_covering_screen = (rect.right - rect.left >= sw) and (rect.bottom - rect.top >= sh)
                GWL_STYLE = -16; WS_CAPTION = 0x00C00000
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
                is_borderless = not (style & WS_CAPTION)
                if is_covering_screen and is_borderless:
                    self.root.attributes('-topmost', False)
                else:
                    self.root.attributes('-topmost', True)
        except: pass
        self.root.after(2000, self.manage_topmost)

# --- BACKUP FEATURE (Updated with Frequency in settings) ---
    def ask_for_backup(self):
        if self.backup_denied: return
        if not self.backup_sources or not self.backup_dest:
            if self.backup_ignored_once:
                self.queue_message("I am asking you again, do you want me to automatically backup your data?", duration=0, animation='Talking', button_text="Setup Backup", button_command=self.open_backup_settings)
            else:
                self.queue_message("Do you want me to automatically backup certain data on your PC to keep them safe?", duration=0, animation='Talking', button_text="Setup Backup", button_command=self.open_backup_settings)
                self.backup_ignored_once = True
        self.root.after(5400000, self.ask_for_backup)

    def open_backup_settings(self):
        self.hide_bubble(); self.is_showing_bubble = False
        win = tk.Toplevel(self.root); win.title("Backup Settings"); win.geometry("400x500")
        win.configure(bg=self.theme['bg']); win.attributes('-topmost', True); self.apply_premium_ui(win)
        
        # Sources
        tk.Label(win, text="Folders to Backup:", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 12, "bold")).pack(pady=10)
        src_listbox = tk.Listbox(win, bg=self.theme['surface'], fg=self.theme['fg'], font=("Segoe UI", 10), height=5, bd=0, highlightthickness=0)
        src_listbox.pack(fill='x', padx=20, pady=5)
        for s in self.backup_sources: src_listbox.insert(tk.END, s)
        def add_src():
            folder = filedialog.askdirectory(title="Select Folder to BACKUP")
            if folder and folder not in self.backup_sources:
                self.backup_sources.append(folder); src_listbox.insert(tk.END, folder)
        def rem_src():
            sel = src_listbox.curselection()
            if sel: self.backup_sources.pop(sel[0]); src_listbox.delete(sel[0])
        btn_frame = tk.Frame(win, bg=self.theme['bg']); btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="Add Folder", command=add_src, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 9, "bold"), bd=0, padx=10).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Remove Selected", command=rem_src, bg='#ff3333', fg='white', font=("Segoe UI", 9, "bold"), bd=0, padx=10).pack(side='left', padx=5)
        
        # Destination
        tk.Label(win, text="Main Backup Destination:", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        dest_label = tk.Label(win, text=self.backup_dest or "Not Set", bg=self.theme['surface'], fg=self.theme['fg'], font=("Segoe UI", 10), wraplength=350)
        dest_label.pack(padx=20, pady=5)
        def set_dest():
            folder = filedialog.askdirectory(title="Select Where to STORE Backups")
            if folder: self.backup_dest = folder; dest_label.config(text=folder)
        tk.Button(win, text="Set Destination", command=set_dest, bg=self.theme['surface'], fg=self.theme['fg'], font=("Segoe UI", 9, "bold"), bd=0, padx=10).pack(pady=5)
        
        # Frequency (NEW!)
        tk.Label(win, text="Backup Frequency:", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 12, "bold")).pack(pady=(10, 5))
        freq_map = {"4hrs": "Every 4 Hrs", "daily": "Daily", "weekly": "Weekly"}
        freq_combo = ttk.Combobox(win, values=["Every 4 Hrs", "Daily", "Weekly"], state="readonly", font=("Segoe UI", 10))
        freq_combo.set(freq_map.get(self.backup_freq, "Daily")) # Set current setting
        freq_combo.pack(pady=5)
        
        def save_backup():
            # Translate UI back to internal setting
            selected_freq = freq_combo.get()
            if "4 Hrs" in selected_freq: self.backup_freq = "4hrs"
            elif "Weekly" in selected_freq: self.backup_freq = "weekly"
            else: self.backup_freq = "daily"
            
            if not self.backup_sources or not self.backup_dest:
                self.queue_message("Setup incomplete! Need source and destination.", 3000, animation='Warning')
                return
                
            self.save_settings(); win.destroy()
            self.queue_message("Backup settings saved!", 2000, animation='Talking')
            
        tk.Button(win, text="Save Settings", command=save_backup, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 12, "bold"), bd=0, padx=20, pady=5).pack(pady=15)

    # Add this helper function right above execute_backup_now
    def _remove_readonly(self, func, path, excinfo):
        """Force Windows to delete read-only files (fixes OneDrive/locked file backup crashes)"""
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def execute_backup_now(self):
        if not self.backup_sources or not self.backup_dest:
            self.queue_message("No backup configured yet! Set it up in Settings.", 3000, animation='Talking', button_text="Setup", button_command=self.open_backup_settings)
            return
        self.queue_message("Backing up your files now...", 3000, animation='Talking')
        success = True
        for src in self.backup_sources:
            folder_name = os.path.basename(src) + "_Backup"
            dest_path = os.path.join(self.backup_dest, folder_name)
            try:
                # FIX: Added onerror=self._remove_readonly to force delete locked files
                if os.path.exists(dest_path): shutil.rmtree(dest_path, onerror=self._remove_readonly)
                shutil.copytree(src, dest_path)
            except Exception as e:
                print(f"Backup failed for {src}: {e}"); success = False
        if success: self.queue_message("Backup complete! Your stuff is safe.", 3000, animation='Talking')
        else: self.queue_message("Some backups failed! Check if files are open in another app.", 5000, animation='Warning')

    # --- STORAGE CHECKER ---
    def check_storage_status(self):
        drives = ['C:\\', 'D:\\', 'E:\\']
        low_drives = []
        for d in drives:
            if os.path.exists(d):
                try:
                    usage = psutil.disk_usage(d)
                    if usage.free < 10 * 1024 * 1024 * 1024: low_drives.append(f"{d} ({usage.free // (1024**3)}GB left)")
                except: pass
        if low_drives and not self.low_storage_warned:
            self.low_storage_warned = True
            msg = f"⚠️ Storage Critical!\n{', '.join(low_drives)}\nWant me to help clear space?"
            # Urgent message, auto-dismiss after 8 seconds if ignored
            self.queue_message(msg, duration=8000, animation='Warning', button_text="Cleanup Space", button_command=self.offer_emergency_cleanup, is_urgent=True)
        self.root.after(1800000, self.check_storage_status)

    def offer_emergency_cleanup(self):
        self.queue_message("Move your beloved files out of Downloads/Documents/Desktop NOW. Click Done when safe.", duration=0, animation='Warning', button_text="Done, Clean It", button_command=self.perform_emergency_cleanup)

    def perform_emergency_cleanup(self):
        self.queue_message("Cleaning up junk...", 5000, animation='Talking')
        self.organize_downloads()
        self.check_duplicates(force=True)
        subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force"], capture_output=True)
        self.queue_message("Cleanup done! PC is fresher now.", 4000, animation='Talking')
        self.low_storage_warned = False

       # --- SYSTEM INFO TAB (Advanced & Easy to Read) ---
    def show_system_info(self):
        info_win = tk.Toplevel(self.root); info_win.title("System Info"); info_win.geometry("500x600")
        info_win.configure(bg=self.theme['bg']); info_win.attributes('-topmost', True); self.apply_premium_ui(info_win)
        tk.Label(info_win, text="🖥️ ADVANCED SYSTEM INFO", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 14, "bold")).pack(pady=15)
        
        info_text = ""
        
        # --- OS INFO ---
        info_text += "--- OPERATING SYSTEM ---\n"
        info_text += f"OS: {platform.system()} {platform.release()} ({platform.version()})\n"
        info_text += f"Architecture: {platform.machine()}\n\n"
        
        # --- HARDWARE INFO ---
        info_text += "--- HARDWARE ---\n"
        try:
            man = subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_ComputerSystem | Select-Object -ExpandProperty Manufacturer"], capture_output=True, text=True).stdout.strip()
            mod = subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_ComputerSystem | Select-Object -ExpandProperty Model"], capture_output=True, text=True).stdout.strip()
            info_text += f"PC Model: {man} {mod}\n"
        except: pass
        
        # CPU
        info_text += f"CPU: {platform.processor()}\n"
        info_text += f"Logical Cores: {psutil.cpu_count()}\n"
        try:
            max_speed = subprocess.run(["powershell", "-Command", "(Get-CimInstance Win32_Processor).MaxClockSpeed"], capture_output=True, text=True).stdout.strip()
            if max_speed: info_text += f"Max Clock Speed: {max_speed} MHz\n"
        except: pass
        
        # RAM
        ram = psutil.virtual_memory()
        info_text += f"Total RAM: {ram.total // (1024**3)} GB "
        info_text += "(⚠️ Needs Upgrade!)\n" if ram.total < 8 * 1024**3 else "(✅ Good)\n"
        info_text += f"Available RAM: {ram.available // (1024**3)} GB\n\n"
        
        # --- GRAPHICS ---
        info_text += "--- GRAPHICS ---\n"
        try:
            gpu = subprocess.run(["powershell", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"], capture_output=True, text=True).stdout.strip()
            vram = subprocess.run(["powershell", "-Command", "[math]::Round((Get-CimInstance Win32_VideoController).AdapterRAM / 1GB)"], capture_output=True, text=True).stdout.strip()
            info_text += f"GPU: {gpu}\n"
            if vram: info_text += f"VRAM: {vram} GB\n"
            else: info_text += "VRAM: Shared/System\n"
        except: info_text += "GPU: Unknown\n"
        info_text += "\n"
        
        # --- DRIVES ---
        info_text += "--- STORAGE DRIVES ---\n"
        for part in psutil.disk_partitions():
            try:
                usage = psutil.disk_usage(part.mountpoint)
                fstype = part.fstype
                info_text += f"{part.mountpoint} ({fstype}) - Total: {usage.total//(1024**3)}GB | Free: {usage.free//(1024**3)}GB\n"
            except: pass
        info_text += "\n"
        
        # --- BATTERY (Laptops) ---
        if hasattr(psutil, "sensors_battery"):
            bat = psutil.sensors_battery()
            if bat:
                info_text += "--- BATTERY ---\n"
                status = "Charging" if bat.power_plugged else "Discharging"
                info_text += f"Battery: {int(bat.percent)}% ({status})\n\n"
                
        # --- NETWORK ---
        info_text += "--- NETWORK ---\n"
        try:
            ips = [addr.address for addr in psutil.net_if_addrs().get('Ethernet', []) if addr.family == 2]
            wifis = [addr.address for addr in psutil.net_if_addrs().get('Wi-Fi', []) if addr.family == 2]
            if ips: info_text += f"Ethernet IP: {ips[0]}\n"
            if wifis: info_text += f"Wi-Fi IP: {wifis[0]}\n"
        except: pass

        txt = tk.Text(info_win, bg=self.theme['surface'], fg=self.theme['fg'], font=("Consolas", 10), wrap='word', bd=0)
        txt.pack(fill='both', expand=True, padx=20, pady=10)
        txt.insert('1.0', info_text)
        txt.config(state='disabled') # <-- FIXED TYPO HERE

    # --- DRAFT BOOK ---
    def show_draft_book(self):
        if self.draft_window and self.draft_window.winfo_exists(): self.draft_window.lift(); return
        self.draft_window = tk.Toplevel(self.root); self.draft_window.title("Draft Book")
        self.draft_window.geometry("400x400"); self.draft_window.configure(bg=self.theme['bg'])
        self.draft_window.attributes('-topmost', True); self.apply_premium_ui(self.draft_window)
        tk.Label(self.draft_window, text="📓 Quick Draft", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 12, "bold")).pack(pady=5)
        self.draft_text = tk.Text(self.draft_window, bg=self.theme['surface'], fg=self.theme['fg'], font=("Segoe UI", 11), wrap='word', bd=0, insertbackground=self.theme['fg'])
        self.draft_text.pack(fill='both', expand=True, padx=10, pady=5)
        try:
            with open(DRAFT_FILE, "r", encoding="utf-8") as f: self.draft_text.insert('1.0', f.read())
        except: pass
        self.draft_text.bind('<KeyRelease>', self.save_draft)

    def save_draft(self, event=None):
        try:
            with open(DRAFT_FILE, "w", encoding="utf-8") as f: f.write(self.draft_text.get('1.0', tk.END))
        except: pass

    # --- HELP MENU ---
    def show_help(self):
        help_win = tk.Toplevel(self.root); help_win.title("Help"); help_win.geometry("450x500")
        help_win.configure(bg=self.theme['bg']); help_win.attributes('-topmost', True); self.apply_premium_ui(help_win)
        tk.Label(help_win, text="🆘 Buddy Help", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 14, "bold")).pack(pady=10)
        tips = [
            "🚀 App Launcher (Ctrl+Alt+B): Find any app fast.",
            "🧠 Memory Bank (Ctrl+Shift+V): Grab clipboard history or auto-search errors.",
            "📸 Snapshot (Ctrl+Alt+S): Drag to screenshot any area.",
            "📓 Draft Book (Ctrl+Alt+N): Quick notepad for ideas. Saves automatically.",
            "🔎 Web Search (Ctrl+Alt+G): Quick Google search.",
            "💾 Backup Now: Instantly copies your folders to your Main Backup folder.",
            "⚡ RAM/CPU Nuke: If PC lags, I'll offer to kill heavy apps. I won't kill myself!",
            "🎮 Gaming: I stay on top, but if you launch a real fullscreen game, I yield to it.",
            "🔄 Always On Top: I sit over maximized apps, but hide if an exclusive game takes over."
        ]
        for tip in tips:
            tk.Label(help_win, text=tip, bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 10), wraplength=400, anchor='w', justify='left').pack(fill='x', padx=20, pady=3)

    # --- SHIFT PRESETS MANAGER ---
    def load_presets(self):
        if os.path.exists(SHIFTS_FILE):
            try: 
                with open(SHIFTS_FILE, 'r') as f: self.shift_presets = json.load(f); return
            except: pass
        if not self.shift_presets: self.shift_presets = {'Default Shift': []}

    def save_presets(self):
        try: 
            with open(SHIFTS_FILE, 'w') as f: json.dump(self.shift_presets, f)
        except Exception as e: print(f"Error saving presets: {e}")

    def show_shift_launcher(self):
        self.load_presets()
        launch_win = tk.Toplevel(self.root); launch_win.title("Start Work Shift"); launch_win.geometry("450x400")
        launch_win.configure(bg=self.theme['bg']); launch_win.attributes('-topmost', True); launch_win.grab_set()
        self.apply_premium_ui(launch_win) 
        tk.Label(launch_win, text="Select Shift", bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 16, "bold")).pack(pady=20)
        lb = tk.Listbox(launch_win, font=("Segoe UI", 12), bg=self.theme['surface'], fg=self.theme['fg'], bd=0, highlightthickness=0, selectbackground=self.theme['accent'])
        lb.pack(fill='both', expand=True, padx=20, pady=5)
        for name in sorted(self.shift_presets.keys()): lb.insert(tk.END, f"{name} ({len(self.shift_presets[name])} apps)")
        if lb.size() > 0: lb.select_set(0)
        def launch():
            sel = lb.curselection()
            if not sel: return
            preset_name = lb.get(sel[0]).split(" (")[0]; launch_win.destroy()
            self.execute_shift_launch(preset_name, self.shift_presets[preset_name])
        tk.Button(launch_win, text="LAUNCH SHIFT", command=launch, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 12, "bold"), bd=0, padx=20, pady=10).pack(pady=20, padx=20, fill='x')
        lb.bind('<Return>', lambda e: launch()); lb.bind('<Double-Button-1>', lambda e: launch())

    def execute_shift_launch(self, name, apps):
        self.active_shift = name; self.queue_message(f"{self.say('shift_launched')}\nStarting '{name}'...", 4000)
        count = 0
        for app_name in apps:
            for name_idx, path in self.app_index:
                if name_idx == app_name:
                    try: os.startfile(path); count += 1; time.sleep(0.3)
                    except: pass
                    break
        if count == 0: self.queue_message("Couldn't find any of those apps.", 3000)

    def open_preset_manager(self):
        self.load_presets()
        editor = tk.Toplevel(self.root); editor.title("Shift Preset Manager"); editor.geometry("700x500")
        editor.configure(bg=self.theme['bg']); editor.attributes('-topmost', True); self.apply_premium_ui(editor)
        top_frame = tk.Frame(editor, bg=self.theme['bg']); top_frame.pack(fill='x', padx=15, pady=15)
        tk.Label(top_frame, text="Preset:", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 11, "bold")).pack(side='left', padx=5)
        preset_combo = ttk.Combobox(top_frame, values=list(self.shift_presets.keys()), state="readonly", font=("Segoe UI", 11))
        if self.shift_presets: preset_combo.current(0)
        preset_combo.pack(side='left', padx=5); current_apps_list = []
        def load_preset_into_ui(event=None):
            nonlocal current_apps_list; name = preset_combo.get()
            if name in self.shift_presets: current_apps_list = list(self.shift_presets[name]); fill_edit_lists()
        def fill_edit_lists():
            avail_list.delete(0, tk.END); selected_list.delete(0, tk.END)
            for app in current_apps_list: selected_list.insert(tk.END, app)
            search_term = search_entry.get().lower()
            for name, _ in self.app_index:
                if name not in current_apps_list and search_term in name.lower(): avail_list.insert(tk.END, name)
        def create_new():
            name = tk.simpledialog.askstring("New Preset", "Enter name for new preset:")
            if name and name not in self.shift_presets: self.shift_presets[name] = []; preset_combo['values'] = list(self.shift_presets.keys()); preset_combo.set(name); load_preset_into_ui(); self.save_presets()
        def rename_preset():
            old_name = preset_combo.get()
            if old_name not in self.shift_presets: return
            new_name = tk.simpledialog.askstring("Rename", "Rename preset to:", initialvalue=old_name)
            if new_name and new_name != old_name and new_name not in self.shift_presets: self.shift_presets[new_name] = self.shift_presets.pop(old_name); preset_combo['values'] = list(self.shift_presets.keys()); preset_combo.set(new_name); self.save_presets()
        def delete_preset():
            name = preset_combo.get()
            if name in self.shift_presets and tk.messagebox.askyesno("Confirm Delete", f"Delete preset '{name}'?"):
                del self.shift_presets[name]; preset_combo['values'] = list(self.shift_presets.keys())
                if self.shift_presets: preset_combo.current(0); load_preset_into_ui()
                else: selected_list.delete(0, tk.END); avail_list.delete(0, tk.END); current_apps_list.clear()
                self.save_presets()
        def save_current():
            name = preset_combo.get()
            if name: self.shift_presets[name] = current_apps_list; self.save_settings(); self.queue_message(f"Saved preset '{name}'.", 2000); editor.destroy()
        btn_style = {"font": ("Segoe UI", 10), "bd": 0, "padx": 10, "pady": 5}
        tk.Button(top_frame, text="New", command=create_new, bg=self.theme['surface'], fg=self.theme['fg'], **btn_style).pack(side='left', padx=5)
        tk.Button(top_frame, text="Rename", command=rename_preset, bg=self.theme['surface'], fg=self.theme['fg'], **btn_style).pack(side='left', padx=5)
        tk.Button(top_frame, text="Delete", command=delete_preset, bg='#ff3333', fg='white', **btn_style).pack(side='left', padx=5)
        preset_combo.bind("<<ComboboxSelected>>", load_preset_into_ui)
        search_frame = tk.Frame(editor, bg=self.theme['bg']); search_frame.pack(pady=10)
        tk.Label(search_frame, text="Search Apps:", bg=self.theme['bg'], fg=self.theme['text_secondary'], font=("Segoe UI", 10)).pack(side='left', padx=5)
        search_entry = tk.Entry(search_frame, bg=self.theme['surface'], fg=self.theme['fg'], insertbackground=self.theme['fg'], font=("Segoe UI", 10), width=30, bd=0, relief='flat'); search_entry.pack(side='left', ipady=4)
        search_entry.bind('<KeyRelease>', lambda e: fill_edit_lists())
        list_frame = tk.Frame(editor, bg=self.theme['bg']); list_frame.pack(expand=True, fill='both', padx=15, pady=5)
        tk.Label(list_frame, text="Available Apps", bg=self.theme['bg'], fg=self.theme['text_secondary'], font=("Segoe UI", 9)).grid(row=0, column=0)
        avail_list = tk.Listbox(list_frame, bg=self.theme['surface'], fg=self.theme['fg'], font=("Segoe UI", 10), selectmode='single', bd=0, highlightthickness=0, selectbackground=self.theme['accent']); avail_list.grid(row=1, column=0, sticky='nsew', padx=5)
        btn_frame = tk.Frame(list_frame, bg=self.theme['bg']); btn_frame.grid(row=1, column=1, padx=15)
        tk.Button(btn_frame, text="▶", command=lambda: move_item(avail_list, selected_list), bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 12), bd=0, padx=10, pady=5).pack(pady=10)
        tk.Button(btn_frame, text="◀", command=lambda: move_item(selected_list, avail_list), bg='#ff3333', fg='white', font=("Segoe UI", 12), bd=0, padx=10, pady=5).pack(pady=10)
        tk.Label(list_frame, text="Preset Apps", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 9)).grid(row=0, column=2)
        selected_list = tk.Listbox(list_frame, bg=self.theme['surface'], fg=self.theme['accent'], font=("Segoe UI", 10), selectmode='single', bd=0, highlightthickness=0, selectbackground=self.theme['accent']); selected_list.grid(row=1, column=2, sticky='nsew', padx=5)
        list_frame.columnconfigure(0, weight=1); list_frame.columnconfigure(2, weight=1); list_frame.rowconfigure(1, weight=1)
        def move_item(src, dest):
            sel = src.curselection()
            if not sel: return
            item = src.get(sel[0]); src.delete(sel[0]); dest.insert(tk.END, item); nonlocal current_apps_list
            if dest == selected_list:
                if item not in current_apps_list: current_apps_list.append(item)
            else:
                if item in current_apps_list: current_apps_list.remove(item)
        tk.Button(editor, text="Save Preset", command=save_current, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 12, "bold"), bd=0, padx=20, pady=10).pack(pady=20)
        if self.shift_presets: load_preset_into_ui()
        else: create_new()

    # --- LOAD / SAVE ---
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, 'r') as f:
                    data = json.load(f)
                    self.current_corner = data.get('position', 'bottom_right')
                    if 'safe_apps' in data: self.safe_apps = data['safe_apps']
                    if 'nokill_apps' in data: self.nokill_apps = data['nokill_apps']
                    if 'preferred_browser_path' in data: self.preferred_browser_path = data['preferred_browser_path']
                    if 'game_apps' in data: self.game_apps = data['game_apps']
                    self.last_cleanup_date = data.get('last_cleanup', self.last_cleanup_date)
                    self.current_theme_mode = data.get('theme_mode', 'dark')
                    self.theme = self.themes[self.current_theme_mode].copy()
                    self.launch_on_startup = data.get('launch_on_startup', False)
                    if 'accent_color' in data: self.theme['accent'] = data['accent_color']
                    self.glass_mode = data.get('glass_mode', True)
                    self.glass_tint = data.get('glass_tint', 0x99000000)
                    self.backup_sources = data.get('backup_sources', [])
                    self.backup_dest = data.get('backup_dest', '')
                    self.backup_freq = data.get('backup_freq', 'daily')
            except Exception as e: print(f"Error loading settings: {e}")
        self.load_presets()

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump({
                    'position': self.current_corner, 'safe_apps': self.safe_apps,
                    'nokill_apps': self.nokill_apps, 'preferred_browser_path': self.preferred_browser_path,
                    'game_apps': self.game_apps,
                    'last_cleanup': self.last_cleanup_date, 'theme_mode': self.current_theme_mode,
                    'accent_color': self.theme['accent'], 'glass_mode': self.glass_mode, 'glass_tint': self.glass_tint,
                    'launch_on_startup': self.launch_on_startup,
                    'backup_sources': self.backup_sources, 'backup_dest': self.backup_dest, 'backup_freq': self.backup_freq
                }, f)
        except Exception as e: print(f"Error saving settings: {e}")

    # --- LOADING SCREEN ---
    def show_loading_screen(self):
        self.splash = tk.Toplevel(self.root); self.splash.overrideredirect(True); self.splash.attributes('-topmost', True)
        self.apply_premium_ui(self.splash)
        self.splash.configure(bg=MAGIC_BG_COLOR)
        self.splash.attributes('-transparentcolor', MAGIC_BG_COLOR)
        try: self.splash_img = tk.PhotoImage(file=resource_path('Splash/splash_screen.png'))
        except: self.splash_img = None
        if self.splash_img:
            w, h = self.splash_img.width(), self.splash_img.height()
            sw, sh = self.splash.winfo_screenwidth(), self.root.winfo_screenheight()
            self.splash.geometry(f'+{(sw//2)-(w//2)}+{(sh//2)-(h//2)}')
            tk.Label(self.splash, image=self.splash_img, bg=MAGIC_BG_COLOR, borderwidth=0).pack()
            self.splash_text = tk.Label(self.splash, text="INITIALIZING", bg=MAGIC_BG_COLOR, fg=self.theme['accent'], font=("Segoe UI", 12, "bold"))
            self.splash_text.place(relx=0.5, rely=0.9, anchor='center')
        else:
            self.splash.configure(bg=self.theme['bg']); self.splash.geometry('300x300+500+300')
            self.splash_text = tk.Label(self.splash, text="INITIALIZING", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 12, "bold"))
            self.splash_text.pack(expand=True)
        self.root.after(1000, self._destroy_splash_and_start_loading)

    def _destroy_splash_and_start_loading(self):
        if self.splash and self.splash.winfo_exists(): self.splash.destroy()
        self.start_animation_engine(callback=self.on_loading_complete)

    def on_loading_complete(self):
        self.reveal_buddy()

    def reveal_buddy(self):
        self.setup_main_app()

    # --- MAIN SETUP ---
    def setup_main_app(self):
        self.root.deiconify(); self.root.overrideredirect(True); self.root.configure(bg=MAGIC_BG_COLOR)
        self.root.attributes('-transparentcolor', MAGIC_BG_COLOR); self.root.attributes('-topmost', True)
        
        # --- FORCE HIDE FROM MAIN TASKBAR ---
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            WS_EX_APPWINDOW = 0x00040000
            
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style & ~WS_EX_APPWINDOW # Remove the "I am a big app" flag
            style = style | WS_EX_TOOLWINDOW  # Add the "I am a background tool" flag
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except Exception as e:
            print(f"Taskbar hide failed: {e}")
        try:
            self.raw_img = tk.PhotoImage(file=resource_path('face_idle.png')); self.img = self.raw_img.subsample(5, 5)
            self.static_img = self.img 
        except: self.close_app(); return
        self.label = tk.Label(self.root, image=self.img, bg=MAGIC_BG_COLOR, borderwidth=0); self.label.pack()
        self.img_width = self.img.width(); self.img_height = self.img.height()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        pad = 20
        self.corners = {
            "bottom_right": (sw - self.img_width - pad, sh - self.img_height - 80),
            "bottom_left": (pad, sh - self.img_height - 80),
            "top_left": (pad, pad), "top_right": (sw - self.img_width - pad, pad)
        }
        start_x, start_y = self.corners.get(self.current_corner, self.corners["bottom_right"])
        self.x_pos, self.y_pos = start_x, start_y; self.root.geometry(f'+{self.x_pos}+{self.y_pos}')

        # MENU
        menu_font = ("Segoe UI", 10)
        self.main_menu = tk.Menu(self.root, tearoff=0, bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'], font=menu_font)
        self.main_menu.add_command(label="⚡ Start Work Shift", command=self.show_shift_launcher)
        self.main_menu.add_command(label="⚙️ Manage Shift Presets", command=self.open_preset_manager)
        self.main_menu.add_separator()
        self.main_menu.add_command(label="💾 Backup Now", command=self.execute_backup_now)
        self.main_menu.add_command(label="📊 System Info", command=self.show_system_info)
        self.main_menu.add_command(label="📓 Draft Book (Ctrl+Alt+N)", command=self.show_draft_book)
        self.main_menu.add_separator()
        self.main_menu.add_command(label="📂 Organize Downloads", command=lambda: self.organize_downloads() or self.queue_message("Downloads Organized!", 3000))
        self.main_menu.add_separator()
        self.main_menu.add_command(label="🧪 Test Duplicate Check", command=lambda: self.check_duplicates(force=True))
        self.main_menu.add_command(label="🧪 Test Desktop Cleanup", command=lambda: self.check_desktop_clutter(force=True))
        self.main_menu.add_separator()
        self.main_menu.add_command(label="🔍 What's Playing?", command=self.check_active_safe_apps)
        self.main_menu.add_command(label="🚀 App Launcher (Ctrl+Alt+B)", command=self.show_launcher)
        self.main_menu.add_command(label="🧠 Memory Bank (Ctrl+Shift+V)", command=self.show_memory_bank)
        self.main_menu.add_command(label="📸 Snapshot (Ctrl+Alt+S)", command=self.start_snapping)
        self.main_menu.add_command(label="🔎 Web Search (Ctrl+Alt+G)", command=self.open_search_window)
        self.main_menu.add_command(label="⚡ RAM Usage", command=self.show_ram_popup)
        
        self.pos_menu = tk.Menu(self.root, tearoff=0, bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'], font=menu_font)
        for c in ["Bottom Right", "Bottom Left", "Top Right", "Top Left"]: self.pos_menu.add_command(label=c, command=lambda cn=c: self.change_position(cn.lower().replace(" ", "_")))
        self.main_menu.add_cascade(label="🔄 Change Position", menu=self.pos_menu)
        
        self.set_menu = tk.Menu(self.root, tearoff=0, bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'], font=menu_font)
        self.set_menu.add_command(label="Add Music Safe App", command=self.open_add_safe_app_window)
        self.set_menu.add_command(label="Add Protected (No-Kill) App", command=self.open_add_protected_app_window)
        self.set_menu.add_command(label="Set Preferred Browser", command=self.set_browser_path)
        self.set_menu.add_command(label="🎮 Add Game App (Auto-Hide)", command=self.open_add_game_window)
        self.set_menu.add_separator()
        self.set_menu.add_command(label="💾 Backup Settings", command=self.open_backup_settings)
        self.set_menu.add_separator()
        startup_label = "🚀 Startup: ON" if self.launch_on_startup else "🚀 Startup: OFF"
        self.set_menu.add_command(label=startup_label, command=self.toggle_startup)
        self.set_menu.add_command(label="📌 Add to Start Menu", command=self.install_to_start_menu)
        self.main_menu.add_cascade(label="⚙️ Settings", menu=self.set_menu)

        self.visuals_menu = tk.Menu(self.root, tearoff=0, bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'], font=menu_font)
        self.visuals_menu.add_command(label="Toggle Light/Dark Mode", command=self.toggle_theme_mode)
        self.visuals_menu.add_command(label="Change Accent Color", command=self.change_accent_color)
        self.visuals_menu.add_separator()
        self.visuals_menu.add_command(label="Toggle Glass Mode", command=self.toggle_glass_mode)
        self.glass_intensity_menu = tk.Menu(self.root, tearoff=0, bg=self.theme['bg'], fg=self.theme['fg'], activebackground=self.theme['accent'], activeforeground=self.theme['bg'], font=menu_font)
        self.glass_intensity_menu.add_command(label="Light Tint", command=self.set_glass_light)
        self.glass_intensity_menu.add_command(label="Medium Tint", command=self.set_glass_medium)
        self.glass_intensity_menu.add_command(label="Heavy Tint", command=self.set_glass_heavy)
        self.visuals_menu.add_cascade(label="Glass Intensity", menu=self.glass_intensity_menu)
        self.main_menu.add_cascade(label="🎨 Visuals", menu=self.visuals_menu)
        self.main_menu.add_separator()
        self.main_menu.add_command(label="🆘 Help", command=self.show_help)
        self.main_menu.add_separator()
        self.main_menu.add_command(label="❌ Exit Buddy", command=self.close_app)
        self.label.bind("<Button-1>", self.show_main_menu)
        self.label.bind("<Button-3>", self.restore_from_tray) 

        self.ram_popup = None; self.ram_labels = []; self.bubble_win = None; self.bubble_content_frame = None 

        self.root.after(100, self.build_app_index); self.root.after(1000, self.check_morning_cleanup) 
        self.root.after(1500, self.show_greeting_bubble); self.root.after(5000, self.check_system_health)
        self.root.after(15000, self.check_afk_status); self.root.after(5000, self.manage_wellness_checks)
        self.setup_hotkey()
        if self.launch_on_startup: self.create_startup_shortcut()
        self.root.after(3600000, self.auto_organize_loop); self.root.after(1000, self.check_clipboard)
        self.root.after(5000, self.track_coding_session); self.root.after(3600000, self.check_desktop_clutter) 
        self.root.after(7200000, self.check_duplicates)
        self.root.after(10000, self.check_gaming_status)
        self.root.after(2000, self.manage_topmost)
        self.root.after(5400000, self.ask_for_backup) 
        self.root.after(1800000, self.check_storage_status) 
        self.root.after(2400000, self.suggest_shift) 
        
        self.start_static_break()

    def suggest_shift(self):
        if not self.active_shift and not self.is_gaming:
            # FIX: Changed duration from 0 to 8000 (8 seconds) so he doesn't wait forever!
            self.queue_message("Hey, want to start a Work Shift?", duration=8000, animation='Talking', button_text="Start Shift", button_command=self.show_shift_launcher)
        self.root.after(random.randint(1800000, 3600000), self.suggest_shift)

    def open_add_game_window(self):
        win = tk.Toplevel(self.root); win.title("Add Game App"); win.geometry("350x150"); win.configure(bg=self.theme['bg']); win.attributes('-topmost', True)
        self.apply_premium_ui(win) 
        tk.Label(win, text="Add game .exe (I will yield to it when fullscreen):", bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 10)).pack(pady=15)
        entry = tk.Entry(win, bg=self.theme['surface'], fg=self.theme['fg'], insertbackground=self.theme['fg'], font=("Segoe UI", 10), bd=0, relief='flat'); entry.pack(pady=5, ipady=4)
        def save():
            a = entry.get().strip()
            if a:
                if not a.lower().endswith('.exe'): a += '.exe'
                if a.lower() not in self.game_apps: self.game_apps.append(a.lower()); self.save_settings(); self.queue_message(f"Added {a}. I'll pause if it goes fullscreen!", 3000)
            win.destroy()
        tk.Button(win, text="Save", command=save, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=5).pack(pady=10)

    def setup_hotkey(self):
        if KEYBOARD_AVAILABLE:
            try: keyboard.add_hotkey('ctrl+alt+b', self.show_launcher)
            except: pass
            try: keyboard.add_hotkey('ctrl+shift+v', self.show_memory_bank)
            except: pass
            try: keyboard.add_hotkey('ctrl+alt+s', self.start_snapping)
            except: pass
            try: keyboard.add_hotkey('ctrl+alt+g', self.open_search_window)
            except: pass
            try: keyboard.add_hotkey('ctrl+alt+n', self.show_draft_book)
            except: pass

    # --- UI & MOVEMENT ---
    def show_main_menu(self, event): 
        self.main_menu.post(event.x_root, event.y_root)
        
    def change_position(self, corner):
        self.current_corner = corner; self.save_settings()
        tx, ty = self.corners[corner]
        self.hide_bubble() 
        self.x_pos, self.y_pos = tx, ty 
        self.move_smoothly(tx, ty)

    def restore_position(self):
        tx, ty = self.corners.get(self.current_corner, self.corners["bottom_right"])
        self.root.geometry(f'+{tx}+{ty}'); self.x_pos = tx; self.y_pos = ty

    def move_smoothly(self, tx, ty):
        cx, cy = self.root.winfo_x(), self.root.winfo_y()
        if abs(tx-cx) < 5 and abs(ty-cy) < 5: 
            self.root.geometry(f'+{tx}+{ty}')
            self.x_pos, self.y_pos = tx, ty
            return
        sx = int((tx-cx)*0.2) or (1 if tx>cx else -1)
        sy = int((ty-cy)*0.2) or (1 if ty>cy else -1)
        self.x_pos = cx + sx
        self.y_pos = cy + sy
        self.root.geometry(f'+{self.x_pos}+{self.y_pos}')
        if self.bubble_win and self.bubble_win.winfo_exists():
            popup_x = self.get_popup_x(280) 
            self.bubble_win.geometry(f'+{popup_x}+{self.y_pos + 20}')
        self.root.after(15, lambda: self.move_smoothly(tx, ty))
        
    def get_popup_x(self, pw):
        return self.x_pos - pw - 10 if self.x_pos > (self.root.winfo_screenwidth() / 2) else self.x_pos + self.img_width + 10

    def show_speech_bubble(self, message, duration=5000, button_text=None, button_command=None, animation='Talking'):
        if self.bubble_win and self.bubble_win.winfo_exists(): self.bubble_win.destroy()
        self.bubble_win = tk.Toplevel(self.root); self.bubble_win.overrideredirect(True); self.bubble_win.attributes('-topmost', True)
        self.bubble_win.configure(bg=self.theme['bg'], highlightbackground=self.theme['accent'], highlightthickness=1)
        self.apply_premium_ui(self.bubble_win) 
        self.bubble_win.geometry(f'+{self.get_popup_x(280)}+{self.y_pos + 20}')
        if hasattr(self, 'anim_cache') and animation in self.anim_cache and len(self.anim_cache[animation]) > 0:
            self.play_forced_animation(animation)
        self.bubble_content_frame = tk.Frame(self.bubble_win, bg=self.theme['bg']); self.bubble_content_frame.pack(padx=20, pady=15)
        tk.Label(self.bubble_content_frame, text=message, bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 11), justify='left', wraplength=260).pack()
        if button_text and button_command:
            btn = tk.Button(self.bubble_content_frame, text=button_text, command=button_command, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 10, "bold"), relief='flat', bd=0, padx=15, pady=5)
            btn.pack(pady=(10,0))
        if duration > 0: self.bubble_win.after(duration, self.hide_bubble)

    def hide_bubble(self):
        if self.bubble_win and self.bubble_win.winfo_exists(): self.bubble_win.destroy(); self.bubble_win = None; self.bubble_content_frame = None
        self.process_queue() 

    # --- STARTUP & INSTALL LOGIC ---
    def toggle_startup(self):
        self.launch_on_startup = not self.launch_on_startup
        self.save_settings()
        try:
            if self.launch_on_startup:
                self.set_menu.entryconfig("🚀 Startup: OFF", label="🚀 Startup: ON")
                self.create_startup_shortcut()
                self.queue_message("Startup enabled! I'll be here when you log in.", 3000)
            else:
                self.set_menu.entryconfig("🚀 Startup: ON", label="🚀 Startup: OFF")
                self.remove_startup_shortcut()
                self.queue_message("Startup disabled. I'll wait for you to open me.", 3000)
        except Exception: pass

    def create_startup_shortcut(self):
        startup_folder = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, 'Buddy.lnk')
        if getattr(sys, 'frozen', False):
            target_path = sys.executable; arguments = ""; working_dir = os.path.dirname(sys.executable)
        else:
            target_path = sys.executable; arguments = f'"{os.path.abspath(sys.argv[0])}"'; working_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        ps_command = f"""
        $ws = New-Object -ComObject WScript.Shell
        $s = $ws.CreateShortcut('{shortcut_path}')
        $s.TargetPath = '{target_path}'
        $s.Arguments = '{arguments}'
        $s.WorkingDirectory = '{working_dir}'
        $s.Save()
        """
        try:
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True, check=True)
        except Exception as e: print(f"[STARTUP ERROR] Failed: {e}")

    def remove_startup_shortcut(self):
        startup_folder = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup')
        shortcut_path = os.path.join(startup_folder, 'Buddy.lnk')
        if os.path.exists(shortcut_path):
            try: os.remove(shortcut_path)
            except Exception as e: print(f"[STARTUP ERROR] Failed to remove shortcut: {e}")

    def install_to_start_menu(self):
        start_menu_folder = os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs')
        shortcut_path = os.path.join(start_menu_folder, 'Buddy.lnk')
        if os.path.exists(shortcut_path):
            self.queue_message("I'm already in your Start Menu!", 3000); return
        if getattr(sys, 'frozen', False):
            target_path = sys.executable; arguments = ""; working_dir = os.path.dirname(sys.executable)
        else:
            target_path = sys.executable; arguments = f'"{os.path.abspath(sys.argv[0])}"'; working_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        icon_path = os.path.join(working_dir, 'buddy_icon.ico')
        if not os.path.exists(icon_path): icon_path = target_path
        ps_command = f"""
        $ws = New-Object -ComObject WScript.Shell
        $s = $ws.CreateShortcut('{shortcut_path}')
        $s.TargetPath = '{target_path}'
        $s.Arguments = '{arguments}'
        $s.WorkingDirectory = '{working_dir}'
        $s.IconLocation = '{icon_path}'
        $s.Save()
        """
        try:
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True, check=True)
            self.queue_message("Pinned to Start Menu! Hit the Windows key and search 'Buddy'.", 5000)
        except Exception as e:
            print(f"[INSTALL ERROR] Failed: {e}")
            
    def close_app(self):
        if hasattr(self, 'tray_icon') and TRAY_AVAILABLE:
            self.tray_icon.stop()
        self.root.destroy() 