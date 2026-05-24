import os
import re
import shutil
import time
import datetime
import tkinter as tk

class HousekeeperMixin:
    def get_clean_name(self, filename):
        name, ext = os.path.splitext(filename)
        name = re.sub(r'\s*-\s*Copy$', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*\(\d+\)$', '', name)
        return name, ext

    def check_desktop_clutter(self, force=False):
        print("[DEBUG] Checking Desktop Clutter...")
        base = os.path.expanduser('~')
        desktop_path = os.path.join(base, 'Desktop')
        
        if not os.path.exists(desktop_path):
            onedrive_path = os.path.join(base, 'OneDrive', 'Desktop')
            if os.path.exists(onedrive_path):
                desktop_path = onedrive_path
                print(f"[DEBUG] Desktop redirected to OneDrive: {desktop_path}")
            else:
                print(f"[DEBUG] Desktop path not found.")
                if not force: self.root.after(14400000, self.check_desktop_clutter)
                return
        else:
            print(f"[DEBUG] Found standard Desktop: {desktop_path}")

        try:
            files = [f for f in os.listdir(desktop_path) if os.path.isfile(os.path.join(desktop_path, f))]
            clutter = [f for f in files if not f.endswith('.lnk')]
            
            now = time.time()
            threshold = 0 if force else 86400 
            old_clutter = [f for f in clutter if now - os.path.getmtime(os.path.join(desktop_path, f)) > threshold]
            
            print(f"[DEBUG] Found {len(old_clutter)} files. Force: {force}")

            if force:
                if len(old_clutter) > 0:
                    msg = f"TEST MODE:\n{self.say('janitor_found')}\nFound {len(old_clutter)} files. Move to Archive?"
                    def yes_action(): self.perform_desktop_cleanup(old_clutter, desktop_path, force)
                    def no_action(): self.show_speech_bubble("Test cancelled.", 2000)
                    self.show_yes_no_bubble(msg, yes_action, no_action)
                else:
                    self.show_speech_bubble("Test passed: Desktop is clean.", 3000)
            else:
                if len(old_clutter) > 5: 
                    msg = f"{self.say('janitor_found')}\nFound {len(old_clutter)} old files. Move to Archive?"
                    def yes_action(): self.perform_desktop_cleanup(old_clutter, desktop_path, force)
                    def no_action(): 
                        self.show_speech_bubble(self.say('janitor_denied'), 3000)
                        self.root.after(14400000, self.check_desktop_clutter)
                    self.show_yes_no_bubble(msg, yes_action, no_action)
                else:
                    self.root.after(14400000, self.check_desktop_clutter) 

        except Exception as e:
            print(f"[ERROR] Desktop check error: {e}")
            if not force: self.root.after(14400000, self.check_desktop_clutter)

    def perform_desktop_cleanup(self, files, desktop_path, force=False):
        try:
            archive_name = f"Desktop_Archive_{datetime.datetime.now().strftime('%Y%m%d')}"
            docs_path = os.path.expanduser('~/Documents')
            archive_path = os.path.join(docs_path, archive_name)
            
            if not os.path.exists(archive_path): os.makedirs(archive_path)
            
            moved_count = 0
            for f in files:
                try:
                    shutil.move(os.path.join(desktop_path, f), os.path.join(archive_path, f))
                    moved_count += 1
                except Exception: pass
            
            if moved_count > 0:
                # FIX: Tell the user EXACTLY where the files went!
                self.queue_message(f"{self.say('janitor_done')}\nMoved {moved_count} files to:\n{archive_path}", 6000, animation='Talking')
            else:
                self.queue_message("Couldn't move files. Maybe they are open?", 3000, animation='Warning')
        except Exception as e:
            print(f"[ERROR] Cleanup failed: {e}")
            self.queue_message("Cleanup failed. Check permissions.", 3000, animation='Warning')
        
        if not force: self.root.after(14400000, self.check_desktop_clutter)

    def check_duplicates(self, force=False):
        print("[DEBUG] Checking Duplicates...")
        downloads = os.path.expanduser('~/Downloads')
        if not os.path.exists(downloads): 
            print("[DEBUG] Downloads path not found.")
            if not force: self.root.after(86400000, self.check_duplicates)
            return

        try:
            files = {}
            for f in os.listdir(downloads):
                path = os.path.join(downloads, f)
                if os.path.isfile(path):
                    clean_name, ext = self.get_clean_name(f)
                    size = os.path.getsize(path)
                    mtime = os.path.getmtime(path)
                    
                    if clean_name not in files: files[clean_name] = []
                    files[clean_name].append({'path': path, 'size': size, 'mtime': mtime, 'full': f, 'ext': ext})

            duplicates_to_delete = []
            
            for clean_name, data in files.items():
                if len(data) > 1:
                    size_groups = {}
                    for item in data:
                        s = item['size']
                        if s not in size_groups: size_groups[s] = []
                        size_groups[s].append(item)
                    
                    for size, group in size_groups.items():
                        if len(group) > 1:
                            group.sort(key=lambda x: x['mtime'], reverse=True)
                            for item in group[1:]:
                                duplicates_to_delete.append(item['full'])

            print(f"[DEBUG] Found {len(duplicates_to_delete)} duplicates. Force: {force}")

            if force:
                if len(duplicates_to_delete) > 0:
                    msg = f"TEST MODE:\n{self.say('duplicate_found')}\nFound {len(duplicates_to_delete)} copies. Delete old ones?"
                    def yes_action(): self.perform_duplicate_cleanup(duplicates_to_delete, downloads, force)
                    def no_action(): self.show_speech_bubble("Test cancelled.", 2000)
                    self.show_yes_no_bubble(msg, yes_action, no_action)
                else:
                    self.show_speech_bubble("Test passed: No duplicates found in Downloads.", 3000)
            else:
                if len(duplicates_to_delete) > 0:
                    msg = f"{self.say('duplicate_found')}\nFound {len(duplicates_to_delete)} copies. Delete old ones?"
                    def yes_action(): self.perform_duplicate_cleanup(duplicates_to_delete, downloads, force)
                    def no_action(): 
                        self.show_speech_bubble(self.say('duplicate_denied'), 3000)
                        self.root.after(86400000, self.check_duplicates)
                    self.show_yes_no_bubble(msg, yes_action, no_action)
                else:
                    self.root.after(86400000, self.check_duplicates)

        except Exception as e:
            print(f"[ERROR] Duplicate check error: {e}")
            if not force: self.root.after(86400000, self.check_duplicates)

    def perform_duplicate_cleanup(self, files, downloads_path, force=False):
        count = 0
        for f in files:
            try:
                os.remove(os.path.join(downloads_path, f))
                count += 1
            except Exception: pass
        
        if count > 0:
            self.show_speech_bubble(f"{self.say('duplicate_done')}\nDeleted {count} old copies.", 4000)
        else:
            self.show_speech_bubble("Couldn't delete files. Maybe in use?", 3000)
        
        if not force: self.root.after(86400000, self.check_duplicates)

    def organize_downloads(self):
        downloads = os.path.expanduser('~/Downloads')
        if not os.path.exists(downloads): return

        categories = {
            'downloaded-docs': ['.txt', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.csv'],
            'downloaded-images': ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.bmp', '.webp'],
            'downloaded-videos': ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm'],
            'downloaded-archives': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'downloaded-audio': ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.aac', '.wma'],
        }
        
        moved_count = 0
        for folder in categories:
            path = os.path.join(downloads, folder)
            if not os.path.exists(path): os.makedirs(path)
        
        others_path = os.path.join(downloads, 'downloaded-others')
        if not os.path.exists(others_path): os.makedirs(others_path)

        try:
            files = os.listdir(downloads)
        except PermissionError: return

        for filename in files:
            file_path = os.path.join(downloads, filename)
            if os.path.isdir(file_path) or filename.startswith('downloaded-'): continue
            _, ext = os.path.splitext(filename)
            ext = ext.lower()
            moved = False
            target_folder = others_path 
            for folder, extensions in categories.items():
                if ext in extensions:
                    target_folder = os.path.join(downloads, folder)
                    break
            target_path = os.path.join(target_folder, filename)
            try:
                shutil.move(file_path, target_path)
                moved_count += 1
            except (PermissionError, shutil.Error): pass
        
        if moved_count > 0:
            print(f"Organized {moved_count} files in Downloads.")

    def auto_organize_loop(self):
        self.organize_downloads()
        self.root.after(3600000, self.auto_organize_loop)