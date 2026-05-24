import os
import random
import tkinter as tk

class LauncherMixin:
    def build_app_index(self):
        self.app_index = []
        paths_to_scan = [os.path.expandvars(r'%APPDATA%\Microsoft\Windows\Start Menu\Programs'), os.path.expandvars(r'%PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs')]
        print("Scanning Start Menu for apps..."); count = 0
        for base_path in paths_to_scan:
            if not os.path.exists(base_path): continue
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.lnk'): name = file.replace('.lnk', ''); full_path = os.path.join(root, file); self.app_index.append((name, full_path)); count += 1
        self.app_index.sort(key=lambda x: x[0].lower()); print(f"Indexed {count} applications.")

    def show_launcher(self):
        if self.launcher_window and self.launcher_window.winfo_exists(): self.launcher_window.destroy()
        self.launcher_window = tk.Toplevel(self.root); self.launcher_window.overrideredirect(True)
        self.launcher_window.attributes('-topmost', True)
        self.launcher_window.configure(bg=self.theme['bg'], highlightbackground=self.theme['accent'], highlightthickness=2)
        self.apply_premium_ui(self.launcher_window) 
        
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight(); w, h = 500, 400
        self.launcher_window.geometry(f'{w}x{h}+{(sw//2)-(w//2)}+{(sh//2)-(h//2)}')
        
        self.launcher_entry = tk.Entry(self.launcher_window, font=("Segoe UI", 16), bg=self.theme['bg'], fg=self.theme['fg'], insertbackground=self.theme['fg'], bd=0, highlightthickness=0)
        self.launcher_entry.pack(fill='x', padx=20, pady=20); self.launcher_entry.focus_set()
        self.launcher_entry.bind('<KeyRelease>', self.filter_launcher); self.launcher_entry.bind('<Return>', self.launch_selected_app)
        self.launcher_entry.bind('<Escape>', lambda e: self.launcher_window.destroy())

        self.launcher_listbox = tk.Listbox(self.launcher_window, font=("Segoe UI", 12), bg=self.theme['bg'], fg=self.theme['accent'], bd=0, highlightthickness=0, selectbackground=self.theme['accent'], selectforeground=self.theme['bg'])
        self.launcher_listbox.pack(fill='both', expand=True, padx=20, pady=(0,20))
        self.launcher_listbox.bind('<Double-Button-1>', lambda e: self.launch_selected_app())

        self.filter_launcher(None); self.launcher_window.lift()

    def filter_launcher(self, event):
        query = self.launcher_entry.get().lower(); self.launcher_listbox.delete(0, tk.END); matches = []
        if not query: matches = random.sample(self.app_index, min(20, len(self.app_index)))
        else:
            starts_with = []; contains = []
            for name, path in self.app_index:
                nl = name.lower()
                if nl == query: matches.insert(0, (name, path))
                elif nl.startswith(query): starts_with.append((name, path))
                elif query in nl: contains.append((name, path))
            matches = matches + starts_with + contains; matches = matches[:10]
        for name, path in matches: self.launcher_listbox.insert(tk.END, name)
        self.current_matches = matches
        if self.launcher_listbox.size() > 0: self.launcher_listbox.select_set(0)

    def launch_selected_app(self, event=None):
        if not hasattr(self, 'current_matches') or not self.current_matches: return
        selection = self.launcher_listbox.curselection(); index = 0 if not selection else selection[0]
        if index < len(self.current_matches):
            name, path = self.current_matches[index]
            try: os.startfile(path)
            except: pass
            if self.launcher_window: self.launcher_window.destroy()
            self.show_speech_bubble(f"Launching {name}...", duration=2000)