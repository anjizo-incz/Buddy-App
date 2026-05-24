import ctypes
import tkinter as tk
import socket

# Tell Windows to use the actual screen resolution, not a scaled virtual one
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # For Windows 8.1+
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware() # Fallback for older Windows
    except Exception:
        pass

# --- DOUBLE LAUNCH PREVENTION (Socket Lock) ---
def is_already_running():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', 54321)) # Buddy claims this port
        s.listen(1)
        return False
    except socket.error:
        return True

if is_already_running():
    print("[LOCK] Buddy is already running! Exiting this instance.")
    sys.exit(0)

from core.app_core import BuddyApp

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw() # Hide root immediately so it doesn't show in taskbar
    app = BuddyApp(root)
    root.mainloop()