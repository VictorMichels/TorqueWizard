import PyInstaller.__main__
import os
import nicegui

# Get the path to NiceGUI on your system
nicegui_dir = os.path.dirname(nicegui.__file__)

# Define separator for Linux vs Windows
path_sep = ':' if os.name == 'posix' else ';'

cmd = [
    'nice.py',
    '--name=TorqueWizard',
    '--onedir',
    '--windowed',
    '--clean',
    '--noconfirm',
    
    # 1. Force Include NiceGUI Assets (JS/CSS)
    # This fixes the "404 Not Found" errors for the UI
    f'--add-data={nicegui_dir}{path_sep}nicegui',
    
    # 2. Force Include Your Assets
    f'--add-data=assets{path_sep}assets',

    # 3. Hidden Imports (The libraries that PyInstaller misses)
    '--hidden-import=uvicorn',
    '--hidden-import=uvicorn.logging',
    '--hidden-import=uvicorn.loops',
    '--hidden-import=uvicorn.loops.auto',
    '--hidden-import=uvicorn.protocols',
    '--hidden-import=uvicorn.protocols.http',
    '--hidden-import=uvicorn.protocols.http.auto',
    '--hidden-import=uvicorn.lifespan',
    '--hidden-import=uvicorn.lifespan.on',
    '--hidden-import=starlette',
    '--hidden-import=nicegui',
    '--hidden-import=serial',
    '--hidden-import=plotly',
    '--hidden-import=pandas',
    
    # 4. Exclude heavy stuff you don't need
    '--exclude-module=tkinter',
    '--exclude-module=matplotlib',
    '--exclude-module=numpy.random._examples',
]

print("Building TorqueWizard...")
PyInstaller.__main__.run(cmd)
