import tkinter as tk
import os
import sys
import random

class IdleAnimationMixin:
    def start_animation_engine(self, callback):
        """Loads all assets INCREMENTALLY so the event loop stays alive."""
        self.anim_cache = {
            'Idle_1': [], 'Idle_2': [], 'Idle_3': [], 'Idle_4': [], 'Idle_5': [],
            'Talking': [], 'Warning': [], 'Sarcasm': []
        }
        self.is_animating = False
        self.current_anim_queue = []
        self.current_anim_index = 0
        self.current_anim_type = 'Idle'
        self.anim_timer_id = None
        self.on_load_complete = callback

        self._load_queue = [
            ('Talking', 'Animations/Talking', 1, 150),
            ('Warning', 'Animations/Warning', 1, 150),
            ('Sarcasm', 'Animations/Sarcasm', 1, 150),
            ('Idle_1', 'Animations/Idle', 1, 150),
            ('Idle_2', 'Animations/Idle', 151, 300),
            ('Idle_3', 'Animations/Idle', 301, 450),
            ('Idle_4', 'Animations/Idle', 451, 600),
            ('Idle_5', 'Animations/Idle', 601, 750)
        ]
        self._load_queue_index = 0

        print("[ANIM] Starting incremental background load...")
        self._load_next_asset_group()

    def _load_next_asset_group(self):
        if self._load_queue_index >= len(self._load_queue):
            print("[ANIM CACHE] All assets loaded!")
            if self.on_load_complete:
                self.on_load_complete()
            return

        name, folder, start, end = self._load_queue[self._load_queue_index]
        print(f"[ANIM] Loading {name} ({start}-{end})...")

        for i in range(start, end + 1):
            # --- FIX: Use resource_path so PyInstaller can find the folders! ---
            filepath = os.path.join(folder, f"{i:04d}.png")
            try:
                # Define resource_path locally for PyInstaller compatibility
                try:
                    base_path = sys._MEIPASS
                except Exception:
                    base_path = os.path.abspath(".")
                full_path = os.path.join(base_path, filepath)
                
                raw = tk.PhotoImage(file=full_path)
                sub = raw.subsample(5, 5) # Back to 5 for 1080p images!
                self.anim_cache[name].append(sub)
            except Exception:
                pass

        self._load_queue_index += 1
        # Yield to the event loop so the app stays responsive
        self.root.after(1, self._load_next_asset_group)

    # --- PLAYBACK LOGIC ---

    def start_static_break(self):
        self.is_animating = False
        self.current_anim_queue = []

        if hasattr(self, 'static_img') and self.static_img:
            self.img = self.static_img
            self.label.config(image=self.img)

        delay = random.randint(15000, 60000)

        if hasattr(self, 'anim_timer_id') and self.anim_timer_id:
            self.root.after_cancel(self.anim_timer_id)

        print(f"[ANIM] On static break. Next idle in {delay/1000:.1f}s.")
        self.anim_timer_id = self.root.after(delay, self.play_random_idle)

    def play_random_idle(self):
        if self.is_afk:
            self.anim_timer_id = self.root.after(10000, self.play_random_idle)
            return
        anim_index = random.randint(1, 5)
        self.play_animation(f'Idle_{anim_index}')

    def play_forced_animation(self, anim_name):
        if hasattr(self, 'anim_timer_id') and self.anim_timer_id:
            self.root.after_cancel(self.anim_timer_id)
        self.play_animation(anim_name)

    def play_animation(self, anim_name):
        if anim_name not in self.anim_cache or len(self.anim_cache[anim_name]) == 0:
            self.start_static_break()
            return
        self.current_anim_queue = self.anim_cache[anim_name]
        self.current_anim_index = 0
        self.current_anim_type = anim_name
        self.is_animating = True
        self.show_next_frame()

    def show_next_frame(self):
        if not self.is_animating:
            return
        self.img = self.current_anim_queue[self.current_anim_index]
        self.label.config(image=self.img)
        self.current_anim_index += 1
        if self.current_anim_index < len(self.current_anim_queue):
            self.anim_timer_id = self.root.after(33, self.show_next_frame)
        else:
            self.start_static_break()

    def halt_animation(self):
        self.is_animating = False
        if hasattr(self, 'anim_timer_id') and self.anim_timer_id:
            self.root.after_cancel(self.anim_timer_id)
        self.start_static_break()