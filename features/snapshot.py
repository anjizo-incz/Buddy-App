import tkinter as tk
import os
import datetime

try:
    import mss 
    from PIL import Image
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False
    print("WARNING: 'mss' or 'Pillow' library not found. Snapshot disabled.")

class SnapshotMixin:
    def start_snapping(self):
        if not MSS_AVAILABLE:
            self.show_speech_bubble("Snapshot library missing.", 2000)
            return
        self.root.withdraw()
        
        self.snap_canvas = tk.Toplevel(self.root)
        self.snap_canvas.overrideredirect(True)
        
        with mss.MSS() as sct:
            mon = sct.monitors[1] 
            w, h = int(mon['width']), int(mon['height'])
            top, left = int(mon['top']), int(mon['left'])
            
        self.snap_canvas.geometry(f'{w}x{h}+{left}+{top}')
        self.snap_canvas.attributes('-alpha', 0.3) 
        self.snap_canvas.configure(bg='black')
        self.snap_canvas.attributes('-topmost', True)
        
        self.snap_canvas.bind('<ButtonPress-1>', self.on_snap_press)
        self.snap_canvas.bind('<B1-Motion>', self.on_snap_drag)
        self.snap_canvas.bind('<ButtonRelease-1>', self.on_snap_release)
        self.snap_canvas.bind('<Escape>', self.cancel_snapshot)
        self.snap_canvas.bind('<Key>', lambda e: self.cancel_snapshot() if e.keysym == 'Escape' else None)

        self.snap_draw = tk.Canvas(self.snap_canvas, bg='black', highlightthickness=0)
        self.snap_draw.pack(fill='both', expand=True)
        tk.Label(self.snap_canvas, text="Drag to select area. ESC to cancel.", bg='black', fg='white', font=("Consolas", 12)).place(relx=0.5, rely=0.05, anchor='center')
        self.snap_canvas.focus_set()

    def on_snap_press(self, event):
        self.snap_start_x = event.x
        self.snap_start_y = event.y
        self.snap_rect_id = self.snap_draw.create_rectangle(self.snap_start_x, self.snap_start_y, self.snap_start_x, self.snap_start_y, outline='white', width=2)

    def on_snap_drag(self, event):
        self.snap_draw.coords(self.snap_rect_id, self.snap_start_x, self.snap_start_y, event.x, event.y)

    def on_snap_release(self, event):
        if self.snap_rect_id:
            coords = self.snap_draw.coords(self.snap_rect_id)
            x1, y1, x2, y2 = coords
            if x1 > x2: x1, x2 = x2, x1
            if y1 > y2: y1, y2 = y2, y1
            if abs(x2 - x1) > 10 and abs(y2 - y1) > 10:
                self.take_screenshot(x1, y1, x2, y2)
            else:
                self.cancel_snapshot()
        else:
            self.cancel_snapshot()

    def take_screenshot(self, x1, y1, x2, y2):
        if self.snap_canvas:
            self.snap_canvas.destroy()
            self.snap_canvas = None
        self.root.deiconify()
        self.restore_position()
        
        try:
            with mss.MSS() as sct:
                monitor = sct.monitors[1] 
                offset_x, offset_y = int(monitor['left']), int(monitor['top'])
                
                rect = {
                    "top": int(y1) + offset_y, 
                    "left": int(x1) + offset_x, 
                    "width": int(x2 - x1), 
                    "height": int(y2 - y1)
                }
                sct_img = sct.grab(rect)
                img = Image.frombytes("RGB", sct_img.size, sct_img.rgb)
                
                downloads = os.path.expanduser('~/Downloads/downloaded-images')
                if not os.path.exists(downloads): os.makedirs(downloads)
                
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = os.path.join(downloads, f"Snap_{timestamp}.png")
                img.save(filepath)
                
                self.show_speech_bubble("Snapshot saved to Images.", 2000)
                
        except Exception as e:
            print(f"Snapshot failed: {e}")
            self.root.deiconify()

    def cancel_snapshot(self):
        if self.snap_canvas:
            self.snap_canvas.destroy()
            self.snap_canvas = None
        self.root.deiconify()
        self.restore_position()