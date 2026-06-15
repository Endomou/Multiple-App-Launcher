import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog, Menu
import ctypes
from ctypes import wintypes
import sys
import subprocess
import os
import json
import winreg
import threading
from PIL import Image
import pystray
from pystray import MenuItem as item
import win32gui
import win32ui
import win32con
import win32api
import pythoncom
from win32com.shell import shell, shellcon

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

DATA_FILE = "launcher_profiles.json"
SETTINGS_FILE = "launcher_settings.json"
APP_NAME = "MyModernLauncher"



class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(500, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tipwindow = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        
        label = ctk.CTkLabel(tw, text=self.text, corner_radius=6, fg_color="#333333", text_color="#fff", padx=10, pady=5)
        label.pack()

    def hidetip(self):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # State
        self.view_mode = "List" # "List" or "Grid"
        self.icon_size_var = ctk.IntVar(value=32)

        # Window Setup
        self.title("Multiple App Launcher - Admin")
        self.geometry("900x600")

        # Grid Layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data Setup
        self.profiles = {}
        self.current_profile_name = ""
        self.load_data()

        # Handle the "X" button click manually
        self.protocol('WM_DELETE_WINDOW', self.on_closing)

        # --- LEFT SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Allow row 5 (Quick Launch) to expand

        # Sidebar Title
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="LAUNCHER PRO", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # Profile Selector
        self.lbl_profile = ctk.CTkLabel(self.sidebar_frame, text="Select Profile:", anchor="w")
        self.lbl_profile.grid(row=1, column=0, padx=20, pady=(10, 0))
        
        self.profile_menu = ctk.CTkOptionMenu(self.sidebar_frame, dynamic_resizing=False, command=self.change_profile)
        self.profile_menu.grid(row=2, column=0, padx=20, pady=(5, 10))

        # Profile Actions
        self.btn_new_profile = ctk.CTkButton(self.sidebar_frame, text="+ New Profile", command=self.create_profile, 
                                             fg_color="transparent", border_width=2, text_color=("gray10", "#DCE4EE"))
        self.btn_new_profile.grid(row=3, column=0, padx=20, pady=10)

        # Quick Launch Section
        self.lbl_quick = ctk.CTkLabel(self.sidebar_frame, text="Quick Launch:", anchor="w", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_quick.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="w")

        self.quick_launch_frame = ctk.CTkScrollableFrame(self.sidebar_frame, fg_color="transparent")
        self.quick_launch_frame.grid(row=5, column=0, padx=10, pady=5, sticky="nsew")

        # --- SETTINGS SWITCHES (Bottom of Sidebar) ---
        
        # 1. Startup Switch
        self.startup_switch_var = ctk.BooleanVar()
        self.startup_switch = ctk.CTkSwitch(self.sidebar_frame, text="Run at Startup", 
                                            command=self.toggle_startup, variable=self.startup_switch_var, onvalue=True, offvalue=False)
        self.startup_switch.grid(row=7, column=0, padx=20, pady=(10, 0), sticky="s")

        # 2. Minimize to Tray Switch
        self.tray_switch_var = ctk.BooleanVar(value=True) # Default to True
        self.tray_switch = ctk.CTkSwitch(self.sidebar_frame, text="Close to Tray", 
                                         command=self.save_settings,
                                         variable=self.tray_switch_var, onvalue=True, offvalue=False)
        self.tray_switch.grid(row=8, column=0, padx=20, pady=(10, 0), sticky="s")

        # 3. Start As option
        self.lbl_start_as = ctk.CTkLabel(self.sidebar_frame, text="Start as:", anchor="w")
        self.lbl_start_as.grid(row=9, column=0, padx=20, pady=(10, 0), sticky="s")

        self.startup_state_var = ctk.StringVar(value="Normal")
        self.startup_state_menu = ctk.CTkOptionMenu(
            self.sidebar_frame,
            values=["Normal", "Minimized", "Maximized", "Tray"],
            variable=self.startup_state_var,
            command=lambda _v: self.save_settings(),
        )
        self.startup_state_menu.grid(row=10, column=0, padx=20, pady=(5, 10), sticky="s")

        # 4. Icon Size Setting
        self.lbl_icon_size_setting = ctk.CTkLabel(self.sidebar_frame, text="Icon Size:", anchor="w")
        self.lbl_icon_size_setting.grid(row=11, column=0, padx=20, pady=(10, 0), sticky="s")

        self.icon_size_control_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.icon_size_control_frame.grid(row=12, column=0, padx=20, pady=(5, 20), sticky="s")

        self.icon_size_slider = ctk.CTkSlider(
            self.icon_size_control_frame, from_=16, to=128, number_of_steps=112,
            variable=self.icon_size_var, command=self.on_icon_size_changed,
            width=120,
        )
        self.icon_size_slider.pack(side="left", padx=(0, 6))

        self.icon_size_num_label = ctk.CTkLabel(
            self.icon_size_control_frame, text=str(self.icon_size_var.get()),
            width=36, cursor="hand2",
        )
        self.icon_size_num_label.pack(side="left")
        self.icon_size_num_label.bind("<Button-1>", self.edit_icon_size)


        # --- MAIN CONTENT AREA ---
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        
        self.lbl_dashboard = ctk.CTkLabel(self.header_frame, text="Dashboard", font=ctk.CTkFont(size=24, weight="bold"))
        self.lbl_dashboard.pack(side="left")

        self.btn_delete_profile = ctk.CTkButton(self.header_frame, text="Delete Profile", fg_color="#ef5350", hover_color="#c62828", width=100, command=self.delete_profile)
        self.btn_delete_profile.pack(side="right")

        self.btn_rename_profile = ctk.CTkButton(self.header_frame, text="Rename Profile", fg_color="#FFA726", hover_color="#FB8C00", width=100, command=self.rename_profile)
        self.btn_rename_profile.pack(side="right", padx=(0, 10))

        # View Mode Toggle
        self.view_mode_seg = ctk.CTkSegmentedButton(self.header_frame, values=["List", "Grid"], command=self.set_view_mode)
        self.view_mode_seg.set("List")
        self.view_mode_seg.pack(side="right", padx=(0, 20))

        # Scrollable App List
        self.scroll_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Applications List")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # Action Buttons (Bottom)
        self.actions_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.actions_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))

        self.btn_add_app = ctk.CTkButton(self.actions_frame, text="Add Application (.exe)", command=self.add_app, height=40)
        self.btn_add_app.pack(side="left", padx=(0, 10), fill="x", expand=True)

        self.btn_launch = ctk.CTkButton(self.actions_frame, text="LAUNCH ALL", command=self.launch_profile, height=40,
                                        fg_color="#2CC985", hover_color="#0C955A", text_color="white", font=ctk.CTkFont(size=14, weight="bold"))
        self.btn_launch.pack(side="left", padx=(10, 0), fill="x", expand=True)

        # Initialization
        self.check_startup_status()
        self.load_settings()
        self.refresh_profile_ui()
        self.after(100, self.apply_startup_state)

    # --- TRAY ICON LOGIC ---

    def on_closing(self):
        """Overrides the X button behavior"""
        if self.tray_switch_var.get():
            self.withdraw()  # Hide the window
            self.show_tray_icon()
        else:
            self.quit() # Actually close the app

    def show_tray_icon(self):
        """Creates and runs the system tray icon"""
        # Create a simple icon image using PIL (Black square with 'A' or similar)
        # In a real app, you would use: image = Image.open("icon.ico")
        image = Image.new('RGB', (64, 64), color=(44, 201, 133)) # Green square

        # Define Menu Actions (default=True makes 'Show' trigger on left-click)
        menu = (item('Show', self.show_window, default=True), item('Quit', self.quit_app))
        
        # Create Icon
        self.tray_icon = pystray.Icon("name", image, "Launcher Pro", menu)
        
        # Run it (This blocks the main thread until icon.stop is called)
        self.tray_icon.run()

    def show_window(self, icon, item):
        """Callback to restore window"""
        self.tray_icon.stop()  # Stop the tray loop
        self.after(0, self.deiconify)  # Restore window on main thread

    def quit_app(self, icon, item):
        """Callback to fully quit"""
        self.tray_icon.stop()
        self.quit()
        sys.exit()

    # --- SETTINGS LOGIC ---

    def load_settings(self):
        """Load persisted settings (tray preference, startup state)."""
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                self.tray_switch_var.set(settings.get("close_to_tray", True))
                self.startup_state_var.set(settings.get("startup_state", "Normal"))
                icon_size = int(settings.get("icon_size", 32))
                icon_size = max(16, min(128, icon_size))
                self.icon_size_var.set(icon_size)
                self.icon_size_slider.set(icon_size)
                self.icon_size_num_label.configure(text=str(icon_size))
            except Exception as e:
                print(f"Warning: Could not load settings: {e}")

    def save_settings(self, *args):
        """Persist current settings to disk."""
        settings = {
            "close_to_tray": self.tray_switch_var.get(),
            "startup_state": self.startup_state_var.get(),
            "icon_size": self.icon_size_var.get(),
        }
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Warning: Could not save settings: {e}")

    def apply_startup_state(self):
        """Apply the chosen window state when the app first starts."""
        state = self.startup_state_var.get()
        if state == "Minimized":
            self.iconify()
        elif state == "Maximized":
            self.state("zoomed")
        elif state == "Tray":
            self.withdraw()
            threading.Thread(target=self.show_tray_icon, daemon=True).start()
        # "Normal" — default window state, no action needed

    def on_icon_size_changed(self, value):
        """Called when the icon size slider moves."""
        size = int(value)
        self.icon_size_var.set(size)
        self.icon_size_num_label.configure(text=str(size))
        self.save_settings()
        self.refresh_profile_ui()

    def edit_icon_size(self, event=None):
        """Replace the number label with an editable entry field."""
        self.icon_size_num_label.pack_forget()

        entry_var = ctk.StringVar(value=str(self.icon_size_var.get()))
        entry = ctk.CTkEntry(self.icon_size_control_frame, textvariable=entry_var, width=45)
        entry.pack(side="left")
        entry.focus_set()
        entry.select_range(0, "end")

        committed = False

        def commit(event=None):
            nonlocal committed
            if committed:
                return
            committed = True
            try:
                size = int(entry_var.get())
                size = max(16, min(128, size))
            except ValueError:
                size = self.icon_size_var.get()
            entry.destroy()
            self.icon_size_num_label.configure(text=str(size))
            self.icon_size_num_label.pack(side="left")
            self.icon_size_var.set(size)
            self.icon_size_slider.set(size)
            self.save_settings()
            self.refresh_profile_ui()

        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    # --- DATA & UI LOGIC (Existing Code) ---

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.profiles = json.load(f)
            except:
                self.profiles = {"Default": []}
        else:
            self.profiles = {"Default": []}
        
        if self.profiles:
            self.current_profile_name = list(self.profiles.keys())[0]

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.profiles, f, indent=4)

    def set_view_mode(self, mode):
        self.view_mode = mode
        self.refresh_profile_ui()

    def refresh_profile_ui(self):
        profiles = list(self.profiles.keys())
        self.profile_menu.configure(values=profiles)
        self.profile_menu.set(self.current_profile_name)
        
        self.refresh_quick_launch_list()
        
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        apps = self.profiles[self.current_profile_name]
        self.app_rows = []
        self.icon_images = [] # Prevent GC

        icon_size = self.icon_size_var.get()

        if self.view_mode == "List":
            # Reset Grid Config if coming from Grid mode
            self.scroll_frame.grid_columnconfigure(0, weight=1)
            for i in range(1, 10): # clear other column weights
                self.scroll_frame.grid_columnconfigure(i, weight=0)

            for index, app_path in enumerate(apps):
                row_frame = ctk.CTkFrame(self.scroll_frame)
                row_frame.pack(fill="x", pady=5)
                self.app_rows.append(row_frame)
                row_frame.is_selected = False

                # Buttons (Packed FIRST to reserve space)
                btn_del = ctk.CTkButton(row_frame, text="✕", width=40, fg_color="#ef5350", hover_color="#c62828",
                                        command=lambda x=app_path: self.remove_app(x))
                btn_del.pack(side="right", padx=(5, 10))

                btn_edit = ctk.CTkButton(row_frame, text="✎", width=40, fg_color="#444", hover_color="#666",
                                        command=lambda x=index: self.edit_app(x))
                btn_edit.pack(side="right", padx=(5, 0))

                btn_run = ctk.CTkButton(row_frame, text="▶", width=40, fg_color="#2CC985", hover_color="#0C955A",
                                        command=lambda p=app_path: self.launch_single_app(p))
                btn_run.pack(side="right", padx=(5, 0))

                # --- Content Layout ---
                icon_img = self.get_exe_icon(app_path, pixel_size=icon_size)
                if icon_img:
                    self.icon_images.append(icon_img)

                # 1. Icon Label
                lbl_icon = ctk.CTkLabel(row_frame, text="", image=icon_img, width=icon_size + 20)
                lbl_icon.pack(side="left", padx=(10, 5))

                # 2. Information Frame (Name + Path)
                info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="both", expand=True, pady=5)

                app_name = os.path.basename(app_path)
                lbl_name = ctk.CTkLabel(info_frame, text=app_name, anchor="w", font=ctk.CTkFont(size=14, weight="bold"))
                lbl_name.pack(side="top", fill="x")

                lbl_path = ctk.CTkLabel(info_frame, text=app_path, anchor="w", font=ctk.CTkFont(size=12), text_color="gray70")
                lbl_path.pack(side="top", fill="x")

                # Context Menu
                menu = Menu(self, tearoff=0)
                menu.add_command(label="Launch", command=lambda p=app_path: self.launch_single_app(p))
                menu.add_command(label="Edit", command=lambda x=index: self.edit_app(x))
                menu.add_command(label="Delete", command=lambda x=app_path: self.remove_app(x))

                def show_menu(event, m=menu):
                     m.tk_popup(event.x_root, event.y_root)

                # Hover Logic
                default_fg = ("gray86", "gray17")
                hover_fg = ("gray82", "gray21")

                def on_enter(e, f=row_frame):
                    if not getattr(f, 'is_selected', False):
                        f.configure(fg_color=hover_fg)

                def on_leave(e, f=row_frame):
                    try:
                        x, y = self.winfo_pointerxy()
                        widget = self.winfo_containing(x, y)
                        if widget:
                            curr = widget
                            while curr is not None:
                                if curr == f:
                                    return
                                curr = curr.master
                    except:
                        pass
                    
                    if not getattr(f, 'is_selected', False):
                        f.configure(fg_color=default_fg)

                # Bind Events to ALL structural elements so clicking anywhere works
                for w in [row_frame, lbl_icon, info_frame, lbl_name, lbl_path]:
                    w.bind("<Button-1>", lambda event, f=row_frame: self.select_app_row(f))
                    w.bind("<Double-Button-1>", lambda event, p=app_path: self.launch_single_app(p))
                    w.bind("<Button-3>", show_menu)
                    w.bind("<Enter>", on_enter)
                    w.bind("<Leave>", on_leave)

        else: # GRID Mode
             # Grid Configuration (e.g., 5 columns)
            cols = 5
            for i in range(cols):
                self.scroll_frame.grid_columnconfigure(i, weight=1)

            for index, app_path in enumerate(apps):
                row = index // cols
                col = index % cols
                
                icon_img = self.get_exe_icon(app_path, pixel_size=icon_size)
                if icon_img:
                    self.icon_images.append(icon_img)
                
                # App Button/Card
                btn_size = icon_size + 20
                btn = ctk.CTkButton(self.scroll_frame, text="", image=icon_img, width=btn_size, height=btn_size,
                                    fg_color="transparent", border_width=2, border_color="gray30", hover_color="gray25",
                                    command=lambda p=app_path: self.launch_single_app(p))
                btn.grid(row=row, column=col, padx=10, pady=10)
                
                # Tooltip for Title
                ToolTip(btn, text=os.path.basename(app_path))
                
                # Context Menu for Grid Item
                menu = Menu(self, tearoff=0)
                menu.add_command(label="Launch", command=lambda p=app_path: self.launch_single_app(p))
                menu.add_command(label="Edit", command=lambda x=index: self.edit_app(x))
                menu.add_command(label="Delete", command=lambda x=app_path: self.remove_app(x))
                
                def show_menu(event, m=menu):
                    m.tk_popup(event.x_root, event.y_root)
                
                btn.bind("<Button-3>", show_menu)

    def get_exe_icon(self, path, pixel_size=None, size=None):
        """Return a CTkImage for the executable at *path* scaled to *pixel_size*×*pixel_size*.

        The legacy *size* keyword ("small" / "large") is still accepted for
        backwards-compatibility but is ignored when *pixel_size* is given.
        """
        if pixel_size is None:
            # Fall back to legacy size parameter for any remaining callers
            if size == "large":
                pixel_size = 70
            else:
                pixel_size = self.icon_size_var.get()

        if not path or not os.path.exists(path):
            return None
        
        path = os.path.normpath(path)
        out_size = (pixel_size, pixel_size)

        # Method 1: PrivateExtractIconsW (ctypes) — try the best available source size
        try:
            for req in [256, 48, 32]:
                if req >= pixel_size:
                    hIcon = self.fetch_icon_ctypes(path, req)
                    if hIcon:
                        img = self.hicon_to_image(hIcon, req, out_size)
                        if img:
                            return img
        except Exception as e:
            print(f"Ctypes Icon Fetch Error: {e}")

        # Fallback: ExtractIconEx (Standard 32×32 / 16×16)
        try:
            large, small = win32gui.ExtractIconEx(path, 0)
            
            if pixel_size >= 24:
                hIcon = large[0] if large else (small[0] if small else None)
                req_size = 32
            else:
                hIcon = small[0] if small else (large[0] if large else None)
                req_size = 16
            
            if not hIcon:
                return None
            
            return self.hicon_to_image(hIcon, req_size, out_size)
            
        except Exception:
            return None

    def fetch_icon_ctypes(self, path, size):
        try:
            phicon = (wintypes.HICON * 1)()
            # PrivateExtractIconsW(file, index, width, height, phicon, piconid, nIcons, flags)
            res = ctypes.windll.user32.PrivateExtractIconsW(path, 0, size, size, phicon, None, 1, 0)
            if res > 0:
                return phicon[0]
        except:
            pass
        return None

    def hicon_to_image(self, hIcon, icon_size, display_size):
        try:
            # Create dc
            hdc = win32ui.CreateDCFromHandle(win32gui.GetDC(0))
            hbmp = win32ui.CreateBitmap()
            hbmp.CreateCompatibleBitmap(hdc, icon_size, icon_size)
            hdc = hdc.CreateCompatibleDC()
            
            hdc.SelectObject(hbmp)
            
            # Draw
            win32gui.DrawIconEx(hdc.GetSafeHdc(), 0, 0, hIcon, icon_size, icon_size, 0, 0, win32con.DI_NORMAL)
            
            # Convert
            bmpinfo = hbmp.GetInfo()
            bmpstr = hbmp.GetBitmapBits(True)
            
            img = Image.frombuffer(
                'RGBA',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRA', 0, 1
            )
            
            # Clean up
            win32gui.DestroyIcon(hIcon)
            return ctk.CTkImage(light_image=img, dark_image=img, size=display_size)
        except:
             return None

    def select_app_row(self, selected_frame):
        for frame in self.app_rows:
            if frame == selected_frame:
                frame.configure(fg_color=("gray75", "gray25"))
                frame.is_selected = True
            else:
                frame.configure(fg_color=("gray86", "gray17"))
                frame.is_selected = False

    def launch_single_app(self, app_path):
        try:
            subprocess.Popen(app_path)
        except Exception as e:
            print(f"Error launching {app_path}: {e}")


    def change_profile(self, choice):
        self.current_profile_name = choice
        self.refresh_profile_ui()

    def create_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            if name in self.profiles:
                messagebox.showwarning("Error", "Profile exists.")
            else:
                self.profiles[name] = []
                self.current_profile_name = name
                self.save_data()
                self.refresh_profile_ui()

    def rename_profile(self):
        new_name = simpledialog.askstring("Rename Profile", f"Rename '{self.current_profile_name}' to:", initialvalue=self.current_profile_name)
        if new_name and new_name != self.current_profile_name:
            if new_name in self.profiles:
                messagebox.showwarning("Error", "Profile name already exists.")
            else:
                self.profiles[new_name] = self.profiles.pop(self.current_profile_name)
                self.current_profile_name = new_name
                self.save_data()
                self.refresh_profile_ui()

    def delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showwarning("Error", "You must keep at least one profile.")
            return
        if messagebox.askyesno("Confirm", f"Delete {self.current_profile_name}?"):
            del self.profiles[self.current_profile_name]
            self.current_profile_name = list(self.profiles.keys())[0]
            self.save_data()
            self.refresh_profile_ui()

    def edit_app(self, index):
        old_path = self.profiles[self.current_profile_name][index]
        new_path = filedialog.askopenfilename(filetypes=[("Executables", "*.exe")], initialfile=old_path)
        if new_path:
            self.profiles[self.current_profile_name][index] = new_path
            self.save_data()
            self.refresh_profile_ui()

    def add_app(self):
        path = filedialog.askopenfilename(filetypes=[("Executables", "*.exe")])
        if path:
            if path not in self.profiles[self.current_profile_name]:
                self.profiles[self.current_profile_name].append(path)
                self.save_data()
                self.refresh_profile_ui()

    def remove_app(self, path_to_remove):
        self.profiles[self.current_profile_name].remove(path_to_remove)
        self.save_data()
        self.refresh_profile_ui()

    def launch_profile(self):
        self.launch_specific_profile(self.current_profile_name)

    def launch_specific_profile(self, profile_name):
        apps = self.profiles.get(profile_name, [])
        if not apps:
            messagebox.showinfo("Empty", f"No apps in {profile_name}!")
            return
        
        count = 0
        for path in apps:
            try:
                subprocess.Popen(path)
                count += 1
            except Exception as e:
                print(f"Error: {e}")
        self.iconify()

    def refresh_quick_launch_list(self):
        for widget in self.quick_launch_frame.winfo_children():
            widget.destroy()
        
        for profile in self.profiles.keys():
            btn = ctk.CTkButton(self.quick_launch_frame, text=profile, 
                                command=lambda p=profile: self.launch_specific_profile(p),
                                fg_color="transparent", border_width=1, text_color=("gray10", "#DCE4EE"))
            btn.pack(fill="x", pady=2)

    # --- STARTUP LOGIC ---
    def toggle_startup(self):
        is_on = self.startup_switch_var.get()
        task_name = f"{APP_NAME}_Startup"

        if getattr(sys, 'frozen', False):
            exe_path = sys.executable 
            work_dir = os.path.dirname(exe_path)
            args_str = ""
        else:
            # Use pythonw.exe if available to avoid console window on startup
            exe_path = sys.executable
            if exe_path.lower().endswith("python.exe"):
                dir_name = os.path.dirname(exe_path)
                pythonw_path = os.path.join(dir_name, "pythonw.exe")
                if os.path.exists(pythonw_path):
                    exe_path = pythonw_path
            script_path = os.path.abspath(sys.argv[0])
            work_dir = os.path.dirname(script_path)
            safe_script_path = script_path.replace("'", "''")
            args_str = f"-Argument ([char]34 + '{safe_script_path}' + [char]34)"

        safe_exe_path = exe_path.replace("'", "''")
        safe_work_dir = work_dir.replace("'", "''")

        if is_on:
            ps_cmd = (
                f"$ErrorActionPreference = 'Stop'; "
                f"$Action = New-ScheduledTaskAction -Execute '{safe_exe_path}' -WorkingDirectory '{safe_work_dir}' {args_str}; "
                f"$Trigger1 = New-ScheduledTaskTrigger -AtStartup; "
                f"$Trigger2 = New-ScheduledTaskTrigger -AtLogOn; "
                f"$Principal = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\\Users' -RunLevel Highest; "
                f"$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0; "
                f"Register-ScheduledTask -TaskName '{task_name}' -Action $Action -Trigger @($Trigger1, $Trigger2) -Principal $Principal -Settings $Settings -Force"
            )
            try:
                subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd], check=True, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            except Exception as e:
                messagebox.showerror("Task Scheduler Error", f"Failed to enable startup:\n{e}")
                self.startup_switch.deselect()
        else:
            try:
                subprocess.run(["schtasks", "/delete", "/tn", task_name, "/f"], check=True, creationflags=subprocess.CREATE_NO_WINDOW, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
            except Exception:
                pass

    def check_startup_status(self):
        task_name = f"{APP_NAME}_Startup"
        try:
            ps_cmd = f"$t = Get-ScheduledTask -TaskName '{task_name}' -ErrorAction SilentlyContinue; if ($t) {{ Write-Output $t.Actions[0].Execute; Write-Output ('ARGS:' + $t.Actions[0].Arguments) }}"
            result = subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            output = result.stdout.strip()
            if result.returncode == 0 and output:
                lines = [line.strip() for line in output.splitlines()]
                task_exe_path = lines[0].strip('"\'') if len(lines) > 0 else ""
                task_args = lines[1][5:] if len(lines) > 1 and lines[1].startswith("ARGS:") else ""
                
                if getattr(sys, 'frozen', False):
                    expected_exe = sys.executable
                    expected_args = ""
                else:
                    expected_exe = sys.executable
                    if expected_exe.lower().endswith("python.exe"):
                        dir_name = os.path.dirname(expected_exe)
                        pythonw_path = os.path.join(dir_name, "pythonw.exe")
                        if os.path.exists(pythonw_path):
                            expected_exe = pythonw_path
                    script_path = os.path.abspath(sys.argv[0])
                    expected_args = f'"{script_path}"'
                
                path_match = (task_exe_path.lower() == expected_exe.lower())
                args_match = (task_args.lower() == expected_args.lower())
                
                if path_match and args_match:
                    self.startup_switch.select()
                else:
                    self.startup_switch_var.set(True)
                    self.toggle_startup()
                    self.startup_switch.select()
            else:
                self.startup_switch.deselect()
        except:
            self.startup_switch.deselect()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    mutex_name = "MultipleAppLauncher_AdminLauncher_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: # ERROR_ALREADY_EXISTS
        ctypes.windll.user32.MessageBoxW(0, "Multiple App Launcher is already open.", "Already Running", 0x30)
        sys.exit(0)

    if is_admin():
        app = App()
        app.mainloop()
    else:
        ctypes.windll.kernel32.CloseHandle(mutex)
        if getattr(sys, 'frozen', False):
            # If frozen, sys.executable is the compiled .exe
            # Do not pass the script name as a parameter
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        else:
            # If not frozen, sys.executable is python.exe
            # We need to pass the script path and any other arguments
            params = " ".join([f'"{arg}"' for arg in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit()
