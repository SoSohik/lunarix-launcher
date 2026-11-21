import subprocess
import sys
import os
import shutil

base_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(base_dir)

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconsole",
    "--onefile",
    "--name", "Lunarix Launcher",
    "--icon", os.path.join("assets", "icon.ico"),
    "--version-file", "version_info.txt",
    "--noupx",
    "--add-data", f"assets{os.pathsep}assets",
    "--add-data", f"core{os.pathsep}core",
    "--add-data", f"{os.path.join(sys.base_prefix, 'tcl', 'tcl8.6')}{os.pathsep}_tcl_data",
    "--add-data", f"{os.path.join(sys.base_prefix, 'tcl', 'tk8.6')}{os.pathsep}_tk_data",
    "--collect-all", "customtkinter",
    "--collect-all", "cv2",
    "--hidden-import", "PIL._tkinter_finder",
    "--hidden-import", "PIL.ImageTk",
    "--hidden-import", "PIL.ImageDraw",
    "--clean",
    "main.py"
]

print("Running PyInstaller...")
res = subprocess.run(cmd)
if res.returncode == 0:
    dist_exe = os.path.join(base_dir, "dist", "Lunarix Launcher.exe")
    out_exe = os.path.join(base_dir, "Lunarix Launcher.exe")
    if os.path.exists(dist_exe):
        try:
            # Terminate running launcher if open
            subprocess.run(["taskkill", "/F", "/IM", "Lunarix Launcher.exe"], capture_output=True)
            import time
            time.sleep(0.5)
        except Exception:
            pass
        shutil.copy2(dist_exe, out_exe)
        print("SUCCESS: Lunarix Launcher.exe updated successfully!")
    else:
        print("ERROR: dist exe not found")
else:
    print("PyInstaller failed with code:", res.returncode)
