import os
import time
import psutil
import ctypes
import datetime
import random
import subprocess
import shutil
import tkinter as tk

VK_VOLUME_MUTE = 0xAD
KEYEVENTF_KEYUP = 0x0002
TIME_MULTIPLIER = 1 
TEMP_PATH = os.path.expandvars(r'%LOCALAPPDATA%\Temp')

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]

class WellnessMixin:
    def request_random_move(self):
        available_corners = [c for c in self.corners if c != self.current_corner]; target_corner = random.choice(available_corners)
        display_name = target_corner.replace("_", " ").title(); self.hide_bubble()
        self.queue_message(f"Mind if I move to {display_name}?", duration=0, animation='Talking', button_text="Sure", button_command=lambda: self.confirm_move(target_corner))
        if self.bubble_content_frame:
            no_btn = tk.Button(self.bubble_content_frame, text="No", bg='#ff3333', fg='white', font=("Segoe UI", 10, "bold"), relief='flat', bd=0, padx=15, pady=5, command=self.decline_move)
            no_btn.pack(pady=(5,0))
        if self.conversation_timer_id: self.root.after_cancel(self.conversation_timer_id)
        self.conversation_timer_id = self.root.after(random.randint(6000, 8000), self.ignore_move)

    def confirm_move(self, corner_name):
        if self.conversation_timer_id: self.root.after_cancel(self.conversation_timer_id)
        self.hide_bubble(); self.change_position(corner_name); self.user_interacted()
        self.queue_message(random.choice(["Thanks!", "Nice view from here.", "Much better."]), duration=3000)

    def decline_move(self):
        if self.conversation_timer_id: self.root.after_cancel(self.conversation_timer_id)
        self.hide_bubble(); self.user_interacted()
        self.queue_message(random.choice(["Okay, I'll stay here then.", "No problem.", "Fair enough."]), duration=3000, animation='Sarcasm')

    def ignore_move(self):
        if self.conversation_timer_id: self.root.after_cancel(self.conversation_timer_id)
        self.hide_bubble(); self.annoyance_level += 1
        self.queue_message(random.choice(["Guess you like me here.", "Maybe next time.", "Silence means I stay put."]), duration=3000, animation='Sarcasm')

    def user_interacted(self):
        if self.annoyance_level > 0: self.annoyance_level -= 1
        return False

    def show_yes_no_bubble(self, message, yes_cmd, no_cmd):
        self.hide_bubble()
        self.bubble_win = tk.Toplevel(self.root); self.bubble_win.overrideredirect(True); self.bubble_win.attributes('-topmost', True)
        self.bubble_win.configure(bg=self.theme['bg'], highlightbackground=self.theme['accent'], highlightthickness=1)
        self.apply_premium_ui(self.bubble_win) 
        sw = self.root.winfo_screenwidth(); popup_x = self.x_pos - 280 if self.x_pos > (sw / 2) else self.x_pos + self.img_width + 10
        self.bubble_win.geometry(f'+{popup_x}+{self.y_pos + 20}')
        self.bubble_content_frame = tk.Frame(self.bubble_win, bg=self.theme['bg']); self.bubble_content_frame.pack(padx=20, pady=15)
        tk.Label(self.bubble_content_frame, text=message, bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 11), justify='left', wraplength=260).pack()
        btn_frame = tk.Frame(self.bubble_content_frame, bg=self.theme['bg']); btn_frame.pack(pady=(10,0))
        yes_btn = tk.Button(btn_frame, text="Yes", command=lambda: [yes_cmd(), self.hide_bubble()], bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 10, "bold"), relief='flat', bd=0, padx=15, pady=5)
        yes_btn.pack(side='left', padx=5)
        no_btn = tk.Button(btn_frame, text="No", command=lambda: [no_cmd(), self.hide_bubble()], bg='#ff3333', fg='white', font=("Segoe UI", 10, "bold"), relief='flat', bd=0, padx=15, pady=5)
        no_btn.pack(side='left', padx=5)
        self.bubble_timer = self.bubble_win.after(30000, self.hide_bubble)

    def manage_wellness_checks(self):
        if self.bubble_win:
            self.root.after(5000, self.manage_wellness_checks)
            return
        if not self.is_afk and not self.is_safe_app_running() and not self.bubble_win:
            real_elapsed = time.time() - self.session_start_time
            virtual_elapsed = real_elapsed * TIME_MULTIPLIER
            mins = int(virtual_elapsed // 60)
            adapt_factor = 1 + (self.annoyance_level * 0.5)
            effective_mins = mins / adapt_factor
            if effective_mins - self.last_move_request_time_virtual >= 60:
                self.last_move_request_time_virtual = effective_mins
                self.request_random_move()
            if effective_mins >= 30 and "posture" not in self.shown_wellness_checks: self.show_wellness_tip("posture", ["Heads up: Sit up straight.", "Posture check: Shoulders back."])
            elif effective_mins >= 60 and "water" not in self.shown_wellness_checks: self.show_wellness_tip("water", ["It's been an hour. Maybe some water?", "Hydration break? Just a sip."])
            elif effective_mins >= 90 and "eyes" not in self.shown_wellness_checks: self.show_wellness_tip("eyes", ["Look at something far away for 20 seconds.", "Give your eyes 5 minute break."])
            elif effective_mins >= 120 and "break" not in self.shown_wellness_checks: self.show_wellness_tip("break", ["You've been here 2 hours. 5 min walk?", "Stand up and stretch your legs."])
            elif effective_mins >= 150 and "stretch" not in self.shown_wellness_checks: self.show_wellness_tip("stretch", ["Roll your shoulders back a few times.", "Stretch your arms overhead."])
            elif effective_mins >= 180: 
                self.shown_wellness_checks = []; self.session_start_time = time.time(); self.last_move_request_time_virtual = 0
        self.root.after(5000, self.manage_wellness_checks)

    def show_wellness_tip(self, tip_type, messages): 
        self.shown_wellness_checks.append(tip_type)
        self.queue_message(random.choice(messages), duration=5000, animation='Talking')

    def get_heavy_apps(self, limit=5):
        candidates = []
        my_pid = os.getpid() 
        for proc in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid']):
            try:
                if proc.info['pid'] == my_pid: continue 
                name = proc.info['name'].lower()
                if name in self.nokill_apps: continue
                score = proc.info['cpu_percent'] + proc.info['memory_percent']
                if score > 0.1: candidates.append((proc, score))
            except (psutil.NoSuchProcess, psutil.AccessDenied): pass
        candidates.sort(key=lambda x: x[1], reverse=True); return candidates[:limit]

    def execute_app_killer(self):
        # If user clicks NUKE, cancel the incoming sarcasm timer!
        if self.sarcasm_timer_id: self.root.after_cancel(self.sarcasm_timer_id); self.sarcasm_timer_id = None
        
        targets = self.get_heavy_apps(5); killed_names = []
        for proc, score in targets:
            try: proc.terminate(); killed_names.append(proc.info['name'])
            except: 
                try: proc.kill(); killed_names.append(proc.info['name'])
                except: pass
        self.hide_bubble()
        msg = "Terminated:\n" + "\n".join(killed_names) if killed_names else "Couldn't kill anything safely."
        self.queue_message(msg, duration=5000, animation='Warning'); self.high_ram_warned = False; self.high_cpu_warned = False; self.user_interacted()

    def trigger_sarcasm(self): 
        self.sarcasm_timer_id = None
        self.queue_message("Suit yourself. Your funeral.", duration=4000, animation='Sarcasm'); self.annoyance_level += 1

    def check_active_safe_apps(self):
        found_apps = [proc.info['name'] for proc in psutil.process_iter(['name']) if proc.info['name'].lower() in self.safe_apps]
        msg = "Music apps running: " + ", ".join(found_apps).upper() if found_apps else "No music apps running. I'll mute if you leave."
        self.queue_message(msg, duration=8000, animation='Talking')

    def open_add_safe_app_window(self):
        win = tk.Toplevel(self.root); win.title("Add Safe App"); win.geometry("300x150"); win.configure(bg=self.theme['bg']); win.attributes('-topmost', True)
        self.apply_premium_ui(win) 
        tk.Label(win, text="Add music app (e.g. netflix.exe):", bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 10)).pack(pady=15)
        entry = tk.Entry(win, bg=self.theme['surface'], fg=self.theme['fg'], insertbackground=self.theme['fg'], font=("Segoe UI", 10), bd=0, relief='flat'); entry.pack(pady=5, ipady=4)
        def save():
            a = entry.get().strip()
            if a:
                if not a.lower().endswith('.exe'): a += '.exe'
                if a.lower() not in self.safe_apps: self.safe_apps.append(a.lower()); self.save_settings(); self.queue_message(f"Added {a}", 3000)
            win.destroy()
        tk.Button(win, text="Save", command=save, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=5).pack(pady=10)

    def open_add_protected_app_window(self):
        win = tk.Toplevel(self.root); win.title("Add Protected App"); win.geometry("300x150"); win.configure(bg=self.theme['bg']); win.attributes('-topmost', True)
        self.apply_premium_ui(win) 
        tk.Label(win, text="Protect app from killing:", bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 10)).pack(pady=15)
        entry = tk.Entry(win, bg=self.theme['surface'], fg=self.theme['fg'], insertbackground=self.theme['fg'], font=("Segoe UI", 10), bd=0, relief='flat'); entry.pack(pady=5, ipady=4)
        def save():
            a = entry.get().strip()
            if a:
                if not a.lower().endswith('.exe'): a += '.exe'
                if a.lower() not in self.nokill_apps: self.nokill_apps.append(a.lower()); self.save_settings(); self.queue_message(f"Protected {a}", 3000)
            win.destroy()
        tk.Button(win, text="Protect", command=save, bg=self.theme['accent'], fg=self.theme['bg'], font=("Segoe UI", 10, "bold"), bd=0, padx=15, pady=5).pack(pady=10)

    def perform_cleanup(self):
        self.queue_message("Cleaning up junk...", 5000, animation='Talking'); self.root.update()
        try: subprocess.run(["powershell", "-Command", "Clear-RecycleBin -Force"], capture_output=True)
        except: pass
        try:
            for f in os.listdir(TEMP_PATH):
                p = os.path.join(TEMP_PATH, f)
                try: 
                    if os.path.isfile(p): os.unlink(p)
                    elif os.path.isdir(p): shutil.rmtree(p)
                except: pass
        except: pass
        self.last_cleanup_date = datetime.datetime.now().strftime("%d/%m/%Y"); self.save_settings()
        self.hide_bubble(); self.queue_message("PC is fresher now.", 4000, animation='Talking'); self.user_interacted()

    def check_morning_cleanup(self):
        if self.last_cleanup_date != datetime.datetime.now().strftime("%d/%m/%Y"):
            self.queue_message("Morning! Want me to empty the Recycle Bin?", 10000, animation='Talking', button_text="Clean It Now", button_command=self.perform_cleanup)

    def show_greeting_bubble(self):
        if self.bubble_win: return
        h = datetime.datetime.now().hour
        if 5 <= h < 12: g = "Good morning!"
        elif 12 <= h < 18: g = "Good afternoon!"
        elif 18 <= h < 22: g = "Good evening!"
        else: g = "Burning the midnight oil?"
        t = datetime.datetime.now().strftime("%I:%M %p"); r, c = psutil.virtual_memory().percent, psutil.cpu_percent(interval=None)
        hm = "PC is struggling." if r > 80 or c > 80 else "PC is running smooth."
        self.queue_message(f"{g}\nIt's {t}.\n{hm}", 6000, animation='Talking')

    def check_system_health(self):
        r, c = psutil.virtual_memory().percent, psutil.cpu_percent(interval=None)
        if r > 85:
            if not self.high_ram_warned:
                self.high_ram_warned = True
                if self.sarcasm_timer_id: self.root.after_cancel(self.sarcasm_timer_id)
                # URGENT message, auto-closes in 8 seconds
                self.queue_message(f"⚠️ RAM CRITICAL: {int(r)}%", duration=8000, animation='Warning', button_text="NUKE TOP 5", button_command=self.execute_app_killer, is_urgent=True)
                # If ignored, trigger sarcasm 0.5s after it fades
                self.sarcasm_timer_id = self.root.after(8500, self.trigger_sarcasm)
        elif r < 70: self.high_ram_warned = False
        if c > 85:
            if not self.high_cpu_warned:
                self.high_cpu_warned = True
                if self.sarcasm_timer_id: self.root.after_cancel(self.sarcasm_timer_id)
                # URGENT message, auto-closes in 8 seconds
                self.queue_message(f"⚠️ CPU CRITICAL: {int(c)}%", duration=8000, animation='Warning', button_text="NUKE TOP 5", button_command=self.execute_app_killer, is_urgent=True)
                # If ignored, trigger sarcasm 0.5s after it fades
                self.sarcasm_timer_id = self.root.after(8500, self.trigger_sarcasm)
        elif c < 60: self.high_cpu_warned = False
        self.root.after(30000, self.check_system_health)

    def is_safe_app_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() in self.safe_apps: return True
            except: pass
        return False

    def get_idle_time(self):
        l = LASTINPUTINFO(); l.cbSize = ctypes.sizeof(l); ctypes.windll.user32.GetLastInputInfo(ctypes.byref(l))
        return (ctypes.windll.kernel32.GetTickCount() - l.dwTime) / 1000.0

    # --- GAMING LOGIC ---
    def check_gaming_status(self):
        currently_gaming = self.is_game_running()
        if currently_gaming and not self.is_gaming:
            self.is_gaming = True
            self.hide_bubble()
            self.halt_animation() 
            print("[GAMING] Game detected. Pausing animations.")
        elif not currently_gaming and self.is_gaming:
            self.is_gaming = False
            self.start_static_break() 
            self.queue_message(self.say('gaming_end'), 4000, animation='Talking')
            print("[GAMING] Game closed. Restoring Buddy.")
        self.root.after(10000, self.check_gaming_status) 

    def is_game_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'].lower() in self.game_apps: return True
            except: pass
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            rect = ctypes.wintypes.RECT()
            ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
            sw = ctypes.windll.user32.GetSystemMetrics(0)
            sh = ctypes.windll.user32.GetSystemMetrics(1)
            if (rect.right - rect.left >= sw) and (rect.bottom - rect.top >= sh):
                GWL_STYLE = -16; WS_CAPTION = 0x00C00000
                style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
                if not (style & WS_CAPTION): return True
        except: pass
        return False
    
    def check_afk_status(self):
        if self.is_gaming: 
            self.root.after(15000, self.check_afk_status)
            return
        try:
            idle = self.get_idle_time()
            if idle > 300:
                if not self.is_afk:
                    self.is_afk = True
                    if self.is_safe_app_running(): self.queue_message("AFK mode: Audio protected.", 5000, animation='Talking')
                    else: ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0); ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0); self.queue_message("You left. Muted audio.", 5000, animation='Talking')
            else:
                if self.is_afk:
                    self.is_afk = False; self.session_start_time = time.time(); self.last_move_request_time_virtual = 0
                    if not self.is_safe_app_running(): ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, 0, 0); ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_KEYUP, 0); self.queue_message("Welcome back! Audio on.", 4000, animation='Talking')
                    else: self.queue_message("Welcome back!", 4000, animation='Talking')
        except: pass
        self.root.after(15000, self.check_afk_status)

    def get_top_ram_apps(self, limit=5):
        a = []
        for p in psutil.process_iter(['name', 'memory_percent']):
            try: 
                if p.info['name'] and p.info['memory_percent'] is not None and p.info['memory_percent'] > 0.1: a.append((p.info['name'], p.info['memory_percent']))
            except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError): pass
        a.sort(key=lambda x: x[1], reverse=True); return a[:limit]

    def show_ram_popup(self):
        if self.ram_popup and self.ram_popup.winfo_exists(): return
        self.ram_popup = tk.Toplevel(self.root); self.ram_popup.overrideredirect(True)
        self.ram_popup.attributes('-topmost', True); self.ram_popup.configure(bg=self.theme['bg'])
        self.apply_premium_ui(self.ram_popup) 
        self.ram_popup.geometry(f'+{self.get_popup_x(250)}+{self.y_pos}')
        tk.Label(self.ram_popup, text="⚡ LIVE RAM USAGE ⚡", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 11, "bold")).pack(padx=15, pady=(10, 5))
        self.ram_labels = [tk.Label(self.ram_popup, text="Loading...", bg=self.theme['bg'], fg=self.theme['fg'], font=("Segoe UI", 10), anchor='w') for _ in range(5)]
        for l in self.ram_labels: l.pack(padx=15, fill='x')
        tk.Label(self.ram_popup, text="", bg=self.theme['bg']).pack(pady=5)
        self.update_ram_popup(); self.ram_popup.after(random.randint(5000, 8000), self.hide_ram_popup)

    def hide_ram_popup(self):
        if self.ram_popup and self.ram_popup.winfo_exists(): self.ram_popup.destroy(); self.ram_popup = None; self.ram_labels = []

    def update_ram_popup(self):
        if not self.ram_popup or not self.ram_popup.winfo_exists(): return
        t = self.get_top_ram_apps()
        for i in range(5):
            if i < len(t): self.ram_labels[i].config(text=f"{t[i][0]:<20} | {t[i][1]:.1f}%")
            else: self.ram_labels[i].config(text="")
        self.ram_popup.after(2000, self.update_ram_popup) 