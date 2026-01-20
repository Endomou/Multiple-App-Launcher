import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import ctypes
import sys
import subprocess
import os
import json
import winreg  # Used for the Startup feature

# --- CONSTANTS ---
DATA_FILE = "launcher_profiles.json"
APP_NAME = "MyAdminLauncher"

class AdminLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Profile Launcher (Admin)")
        self.root.geometry("600x500")

        # Data Structure: {"ProfileName": ["path1", "path2"], ...}
        self.profiles = {}
        self.current_profile_name = ""

        # Load data from JSON
        self.load_data()

        # --- UI: TOP SECTION (PROFILES) ---
        top_frame = tk.LabelFrame(root, text="Profiles", padx=10, pady=10)
        top_frame.pack(fill="x", padx=10, pady=5)

        # Profile Dropdown
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(top_frame, textvariable=self.profile_var, state="readonly")
        self.profile_combo.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_change)

        # Profile Buttons
        btn_add_prof = tk.Button(top_frame, text="+ New Profile", command=self.create_profile)
        btn_add_prof.pack(side=tk.LEFT, padx=5)
        
        btn_del_prof = tk.Button(top_frame, text="Delete Profile", command=self.delete_profile, fg="red")
        btn_del_prof.pack(side=tk.LEFT, padx=5)

        # --- UI: MIDDLE SECTION (APP LIST) ---
        list_frame = tk.Frame(root)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, font=("Consolas", 10))
        self.listbox.pack(side=tk.LEFT, fill="both", expand=True)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        self.listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        # --- UI: BOTTOM SECTION (CONTROLS) ---
        control_frame = tk.Frame(root, pady=10)
        control_frame.pack(fill="x", padx=10)

        # App Management
        tk.Button(control_frame, text="Add App (.exe)", command=self.add_app).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Remove App", command=self.remove_app).pack(side=tk.LEFT, padx=5)

        # Startup Checkbox
        self.startup_var = tk.BooleanVar()
        self.startup_check = tk.Checkbutton(control_frame, text="Run on Windows Startup", 
                                            variable=self.startup_var, command=self.toggle_startup)
        self.startup_check.pack(side=tk.RIGHT, padx=5)
        
        # Check if currently set to run on startup
        self.check_startup_status()

        # --- LAUNCH BUTTON ---
        launch_btn = tk.Button(root, text="LAUNCH ALL APPS IN PROFILE", font=("Arial", 14, "bold"), 
                               bg="#4CAF50", fg="white", height=2, command=self.launch_profile)
        launch_btn.pack(fill="x", padx=10, pady=10)

        # Initial View Update
        self.refresh_profile_list()

    # --- LOGIC: DATA HANDLING ---
    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.profiles = json.load(f)
            except:
                self.profiles = {"Default": []}
        else:
            self.profiles = {"Default": []}
        
        # Select first profile
        if self.profiles:
            self.current_profile_name = list(self.profiles.keys())[0]

    def save_data(self):
        with open(DATA_FILE, "w") as f:
            json.dump(self.profiles, f, indent=4)

    # --- LOGIC: PROFILES ---
    def refresh_profile_list(self):
        names = list(self.profiles.keys())
        self.profile_combo['values'] = names
        if self.current_profile_name in names:
            self.profile_combo.set(self.current_profile_name)
            self.refresh_app_list()

    def create_profile(self):
        name = simpledialog.askstring("New Profile", "Enter profile name:")
        if name:
            if name in self.profiles:
                messagebox.showwarning("Error", "Profile already exists.")
            else:
                self.profiles[name] = []
                self.current_profile_name = name
                self.save_data()
                self.refresh_profile_list()

    def delete_profile(self):
        if len(self.profiles) <= 1:
            messagebox.showwarning("Error", "You must keep at least one profile.")
            return
        
        confirm = messagebox.askyesno("Confirm", f"Delete profile '{self.current_profile_name}'?")
        if confirm:
            del self.profiles[self.current_profile_name]
            self.current_profile_name = list(self.profiles.keys())[0]
            self.save_data()
            self.refresh_profile_list()

    def on_profile_change(self, event):
        self.current_profile_name = self.profile_var.get()
        self.refresh_app_list()

    # --- LOGIC: APPS ---
    def refresh_app_list(self):
        self.listbox.delete(0, tk.END)
        apps = self.profiles[self.current_profile_name]
        for app in apps:
            self.listbox.insert(tk.END, app)

    def add_app(self):
        file_path = filedialog.askopenfilename(title="Select Executable", filetypes=[("Executables", "*.exe")])
        if file_path:
            current_apps = self.profiles[self.current_profile_name]
            if file_path not in current_apps:
                current_apps.append(file_path)
                self.save_data()
                self.refresh_app_list()

    def remove_app(self):
        sel = self.listbox.curselection()
        if sel:
            app = self.listbox.get(sel)
            self.profiles[self.current_profile_name].remove(app)
            self.save_data()
            self.refresh_app_list()

    def launch_profile(self):
        apps = self.profiles[self.current_profile_name]
        if not apps:
            messagebox.showinfo("Info", "No apps in this profile.")
            return

        for path in apps:
            try:
                subprocess.Popen(path)
            except Exception as e:
                print(f"Error launching {path}: {e}")

    # --- LOGIC: STARTUP (REGISTRY) ---
    def toggle_startup(self):
        # Path to current script (or exe if compiled)
        if getattr(sys, 'frozen', False):
            app_path = sys.executable  # If running as compiled .exe
        else:
            app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"' # If running as .py

        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        try:
            reg = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
            if self.startup_var.get():
                # Add to registry
                winreg.SetValueEx(reg, APP_NAME, 0, winreg.REG_SZ, app_path)
            else:
                # Remove from registry
                try:
                    winreg.DeleteValue(reg, APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(reg)
        except Exception as e:
            messagebox.showerror("Registry Error", str(e))

    def check_startup_status(self):
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            reg = winreg.OpenKey(key, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(reg, APP_NAME)
            self.startup_var.set(True)
            winreg.CloseKey(reg)
        except FileNotFoundError:
            self.startup_var.set(False)

# --- ADMIN ELEVATION ---
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if __name__ == "__main__":
    if is_admin():
        root = tk.Tk()
        app = AdminLauncherApp(root)
        root.mainloop()
    else:
        # Re-run with Admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )