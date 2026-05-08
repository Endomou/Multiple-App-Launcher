Multiple-App Launcher
A Python-based application dashboard that allows you to launch multiple applications simultaneously with Administrator privileges while bypassing repetitive UAC prompts.

🚀 Features
Bypass UAC Prompts: Launch the dashboard once as Admin, and all subsequent apps launch silently with full privileges.

Profile Management: Create distinct profiles (e.g., "Gaming", "Work", "Dev") to group different sets of applications.

Modern UI: Built with customtkinter for a sleek, dark-mode Windows 11 style interface.

System Tray Support: "Close to Tray" functionality keeps the launcher running in the background without cluttering your taskbar.

Startup Integration: Option to automatically launch the dashboard when Windows starts.

Auto-Save: Automatically persists your profiles and app lists to a local JSON file.

🛠️ Prerequisites
Windows 10 or Windows 11

Python 3.8 or higher

PIP (Python Package Manager)

📦 Installation & Setup
Download the EXE file


🖥️ Usage Guide
1. First Run
When you run the app, you will see a single UAC prompt. Click Yes. This grants the launcher the "Token" it needs to launch other apps silently.

2. Creating a Profile
Click + New Profile in the sidebar.

Enter a name (e.g., Gaming).

The dashboard will switch to this new empty profile.

3. Adding Apps
Click Add Application (.exe) at the bottom.

Browse and select the executable files you want in this profile.

They will appear as "Cards" in the main list.

4. Launching
Click the green LAUNCH ALL button.

All apps in the current list will open immediately as Administrator.

5. Settings
Run at Startup: Toggles a registry key to start the app when you log in.

Close to Tray: If enabled, clicking the X button minimizes the app to the system tray (near the clock) instead of closing it.

Start as: Controls the initial window state when the app launches. Options are:
- **Normal** (default): Opens as a regular window.
- **Minimized**: Starts minimized to the taskbar.
- **Maximized**: Starts maximized to fill the screen.
- **Tray**: Starts hidden directly in the system tray — no window appears until you click the tray icon.

⚠️ Troubleshooting
Antivirus Warnings: Windows Defender may flag the compiled .exe because it requests Admin rights and is unsigned. This is a known "False Positive" for PyInstaller apps. You can add an exclusion to resolve this.

Startup Prompt: When running on startup, Windows will still show one UAC prompt for the launcher itself. This is a mandatory security feature of Windows for any Admin-level startup app.
