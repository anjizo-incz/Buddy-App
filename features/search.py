import os
import subprocess
import webbrowser
import winreg
import tkinter as tk
import tkinter.filedialog
import urllib.parse

class SearchMixin:
    def open_search_window(self):
        if hasattr(self, 'search_window') and self.search_window and self.search_window.winfo_exists():
            self.search_window.lift(); self.search_entry.focus_set(); return

        self.search_window = tk.Toplevel(self.root); self.search_window.overrideredirect(True)
        self.search_window.attributes('-topmost', True)
        self.search_window.configure(bg=self.theme['bg'], highlightbackground=self.theme['accent'], highlightthickness=2)
        self.apply_premium_ui(self.search_window) 
        
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight(); w, h = 600, 80
        self.search_window.geometry(f'{w}x{h}+{(sw//2)-(w//2)}+{(sh//2)-(h//2)}')
        
        tk.Label(self.search_window, text="🔎", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 16)).pack(side='left', padx=15)
        self.search_entry = tk.Entry(self.search_window, font=("Segoe UI", 14), bg=self.theme['bg'], fg=self.theme['fg'], insertbackground=self.theme['fg'], bd=0, width=40)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=10, pady=20); self.search_entry.focus_set()
        self.search_entry.bind('<Return>', self.execute_search); self.search_entry.bind('<Escape>', lambda e: self.search_window.destroy())
        self.search_window.lift()
        
    def set_browser_path(self):
        file_path = tk.filedialog.askopenfilename(title="Select Your Preferred Browser", initialdir='C:\\Program Files', filetypes=[("Applications", "*.exe")])
        if file_path:
            self.preferred_browser_path = file_path; self.save_settings(); name = os.path.basename(file_path)
            self.queue_message(f"Set {name} as preferred browser.", 3000)

    def get_default_browser_path(self):
        try:
            key_path = r'http\shell\open\command'; command = winreg.QueryValue(winreg.HKEY_CLASSES_ROOT, key_path)
            parts = command.split('"')
            for part in parts:
                if '.exe' in part: return part
        except WindowsError: pass
        return None

    def execute_search(self, event=None, query_override=None):
        query = ""
        if query_override:
            query = query_override
            if hasattr(self, 'search_window') and self.search_window and self.search_window.winfo_exists(): self.search_window.destroy()
        else:
            if hasattr(self, 'search_window') and self.search_window and self.search_window.winfo_exists():
                query = self.search_entry.get().strip()
                self.search_window.destroy()
            
        if query:
            try:
                query_formatted = urllib.parse.quote_plus(query) # FIXED HERE
                url = f"https://www.google.com/search?q={query_formatted}"
                opened = False
                if self.preferred_browser_path and os.path.exists(self.preferred_browser_path):
                    try: subprocess.Popen([self.preferred_browser_path, url], shell=True); opened = True
                    except Exception as e: print(f"Failed to launch preferred browser: {e}")
                if not opened:
                    detected_browser = self.get_default_browser_path()
                    if detected_browser:
                        try: subprocess.Popen([detected_browser, url], shell=True); opened = True
                        except Exception as e: print(f"Failed to launch detected browser: {e}")
                if not opened:
                    try: webbrowser.open(url); opened = True
                    except: pass
                if not opened:
                    self.queue_message("Browser failed. Are you offline?", 3000, animation='Warning')
            except Exception as e:
                self.queue_message("Search failed. Check connection.", 3000, animation='Warning')