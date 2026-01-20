import customtkinter as ctk
from tkinter import filedialog, messagebox, simpledialog
import ctypes
import sys
import subprocess
import os
import json
import winreg

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

DATA_FILE = "launcher_profiles.json"
APP_NAME = "MyModernLauncher"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title("Admin Command Center")
        self.geometry("900x600")

        # Grid Layout (1x2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Data Setup
        self.profiles = {}
        self.current_profile_name = ""
        self.app_frames = [] # To keep track of UI elements in the list
        self.load_data()

        # --- LEFT SIDEBAR ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

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

        # Startup Switch (Bottom of Sidebar)
        self.startup_switch_var = ctk.BooleanVar()
        self.startup_switch = ctk.CTkSwitch(self.sidebar_frame, text="Run at Startup", 
                                            command=self.toggle_startup, variable=self.startup_switch_var, onvalue=True, offvalue=False)
        self.startup_switch.grid(row=5, column=0, padx=20, pady=20, sticky="s")

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
        self.refresh_profile_ui()

    # --- LOGIC SECTIONS ---

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

    def refresh_profile_ui(self):
        # Update Dropdown
        profiles = list(self.profiles.keys())
        self.profile_menu.configure(values=profiles)
        self.profile_menu.set(self.current_profile_name)
        
        # Clear Scroll Frame
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        # Populate Scroll Frame with Modern "Cards"
        apps = self.profiles[self.current_profile_name]
        
        for index, app_path in enumerate(apps):
            # Each app is a row
            row_frame = ctk.CTkFrame(self.scroll_frame)
            row_frame.pack(fill="x", pady=5)
            
            # App Name/Path Label
            lbl = ctk.CTkLabel(row_frame, text=app_path, anchor="w", padx=10)
            lbl.pack(side="left", fill="x", expand=True, pady=10)
            
            # Delete Button (Small 'x')
            btn_del = ctk.CTkButton(row_frame, text="✕", width=40, fg_color="#444", hover_color="#666",
                                    command=lambda x=app_path: self.remove_app(x))
            btn_del.pack(side="right", padx=10)

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

    def delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showwarning("Error", "You must keep at least one profile.")
            return
        if messagebox.askyesno("Confirm", f"Delete {self.current_profile_name}?"):
            del self.profiles[self.current_profile_name]
            self.current_profile_name = list(self.profiles.keys())[0]
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
        apps = self.profiles[self.current_profile_name]
        if not apps:
            messagebox.showinfo("Empty", "No apps to launch!")
            return
        
        count = 0
        for path in apps:
            try:
                subprocess.Popen(path)
                count += 1
            except Exception as e:
                print(f"Error: {e}")
        
        # Optional: Minimize after launch
        self.iconify()

    # --- STARTUP LOGIC ---
    def toggle_startup(self):
        is_on = self.startup_switch_var.get()
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        
        if getattr(sys, 'frozen', False):
            app_path = sys.executable 
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if is_on:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            messagebox.showerror("Registry Error", str(e))

    def check_startup_status(self):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, APP_NAME)
            self.startup_switch.select()
            winreg.CloseKey(key)
        except:
            self.startup_switch.deselect()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        app = App()
        app.mainloop()
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)