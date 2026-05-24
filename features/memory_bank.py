import datetime
import tkinter as tk

class MemoryBankMixin:
    def check_clipboard(self):
        try:
            current_clip = self.root.clipboard_get()
            if current_clip and current_clip != self.last_clipboard_content:
                is_err = self.detect_error(current_clip); timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                self.clipboard_history.append({'text': current_clip, 'is_error': is_err, 'timestamp': timestamp})
                if len(self.clipboard_history) > 20: self.clipboard_history.pop(0)
                self.last_clipboard_content = current_clip
        except: pass
        self.root.after(1000, self.check_clipboard)

    def show_memory_bank(self):
        if self.memory_window and self.memory_window.winfo_exists(): self.memory_window.destroy()
        self.memory_window = tk.Toplevel(self.root); self.memory_window.overrideredirect(True)
        self.memory_window.attributes('-topmost', True); self.memory_window.configure(bg=self.theme['bg'], highlightbackground=self.theme['accent'], highlightthickness=2)
        self.apply_premium_ui(self.memory_window) 
        
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight(); w, h = 600, 450
        self.memory_window.geometry(f'{w}x{h}+{(sw//2)-(w//2)}+{(sh//2)-(h//2)}')
        
        tk.Label(self.memory_window, text="MEMORY BANK", bg=self.theme['bg'], fg=self.theme['accent'], font=("Segoe UI", 14, "bold")).pack(pady=15)
        tk.Label(self.memory_window, text="Last 20 Clips", bg=self.theme['bg'], fg=self.theme['text_secondary'], font=("Segoe UI", 9)).pack()
        
        self.memory_listbox = tk.Listbox(self.memory_window, font=("Segoe UI", 11), bg=self.theme['bg'], fg=self.theme['fg'], bd=0, highlightthickness=0, selectbackground=self.theme['accent'], selectforeground=self.theme['bg'])
        self.memory_listbox.pack(fill='both', expand=True, padx=20, pady=10)
        self.memory_listbox.bind('<Double-Button-1>', self.copy_from_memory); self.memory_listbox.bind('<Return>', self.copy_from_memory)
        self.memory_listbox.bind('<Escape>', lambda e: self.memory_window.destroy())

        for item in reversed(self.clipboard_history):
            prefix = "🔍 " if item['is_error'] else "📋 "; display_text = item['text'].replace('\n', ' ') 
            display_text = (display_text[:50] + '...') if len(display_text) > 50 else display_text
            self.memory_listbox.insert(tk.END, f"{prefix}{display_text}")
            
        if self.memory_listbox.size() > 0: self.memory_listbox.select_set(0); self.memory_window.focus_set()
        else: self.memory_listbox.insert(tk.END, "Memory is empty...")
        self.memory_window.lift()

    def copy_from_memory(self, event=None):
        sel = self.memory_listbox.curselection()
        if not sel: return
        real_index = (self.memory_listbox.size() - 1) - sel[0]
        if 0 <= real_index < len(self.clipboard_history):
            data = self.clipboard_history[real_index]
            if data['is_error']:
                self.execute_search(query_override=data['text']); self.memory_window.destroy(); self.show_speech_bubble("Searching for error...", 2000)
            else:
                self.root.clipboard_clear(); self.root.clipboard_append(data['text']); self.memory_window.destroy()
                self.show_speech_bubble("Copied to clipboard!", 2000)