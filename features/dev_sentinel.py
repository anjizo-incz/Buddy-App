import psutil
import ctypes
import tkinter as tk

class DevSentinelMixin:
    def get_active_window_title(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            return buf.value
        except:
            return ""

    def get_active_process_name(self):
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            pid = ctypes.c_uint()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            process = psutil.Process(pid.value)
            return process.name().lower()
        except:
            return ""

    def track_coding_session(self):
        # REMOVED AFK CHECK: Coding while reading docs/AFK is still coding!
        try:
            proc = self.get_active_process_name()
            
            # Map common editors to a clean name so tab switches don't reset the timer
            known_editors_map = {
                'code.exe': 'VS Code', 'code-insiders.exe': 'VS Code Insiders',
                'idea64.exe': 'IntelliJ IDEA', 'pycharm64.exe': 'PyCharm',
                'sublime_text.exe': 'Sublime Text', 'notepad++.exe': 'Notepad++',
                'atom.exe': 'Atom', 'javaw.exe': 'Java App'
            }
            
            is_editor = any(editor in proc for editor in self.known_editors)
            
            if is_editor:
                # Use the clean name instead of parsing the chaotic window title!
                project = known_editors_map.get(proc, proc.replace('.exe', '').title())
                
                if project not in self.daily_stats:
                    self.daily_stats[project] = 0
                self.daily_stats[project] += 5 # Adds 5 seconds
        except Exception as e:
            pass 

        self.root.after(5000, self.track_coding_session)

    def show_daily_report(self):
        if not self.daily_stats:
            self.show_speech_bubble("No coding activity detected today yet.", 4000)
            return

        sorted_projects = sorted(self.daily_stats.items(), key=lambda x: x[1], reverse=True)
        
        msg = "📊 Daily Code Report:\n\n"
        for proj, seconds in sorted_projects:
            hrs = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            secs = int(seconds % 60)
            
            if hrs > 0:
                msg += f"• {proj}: {hrs}h {mins}m {secs}s\n"
            elif mins > 0:
                msg += f"• {proj}: {mins}m {secs}s\n"
            else:
                msg += f"• {proj}: {secs}s\n"
        
        self.show_speech_bubble(msg, duration=10000, animation='Talking')

    def detect_error(self, text):
        error_keywords = [
            'error', 'exception', 'traceback', 'failed', 'fatal', 
            'HTTP 4', 'HTTP 5', 'NaN', 'undefined', 'null pointer'
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in error_keywords) and len(text) > 15