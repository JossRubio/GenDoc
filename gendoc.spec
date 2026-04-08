# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for GenDoc
# Build with:  pyinstaller gendoc.spec --noconfirm

block_cipher = None

a = Analysis(
    ["launcher.py"],
    pathex=["."],
    binaries=[],
    datas=[
        # Bundle UI assets — Flask will find them via create_app(base_dir=sys._MEIPASS)
        ("templates", "templates"),
        ("static",    "static"),
    ],
    hiddenimports=[
        # Flask ecosystem
        "flask",
        "werkzeug",
        "werkzeug.serving",
        "werkzeug.debug",
        "jinja2",
        "jinja2.ext",
        "click",
        # Production WSGI server
        "waitress",
        "waitress.runner",
        # AI providers
        "anthropic",
        "openai",
        "google.genai",
        "google.genai.types",
        "google.auth",
        "google.auth.transport",
        # Document generation
        "docx",
        "docx.oxml",
        "docx.shared",
        "docx.enum.text",
        "pptx",
        "pypdf",
        "docx2pdf",
        "mistletoe",
        # Utilities
        "dotenv",
        "python_dotenv",
        "requests",
        "urllib3",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "scipy",
        "pandas",
        "PIL",
        "cv2",
        "test",
        "unittest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="GenDoc",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # No console window — app lives in the browser
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="build/gendoc.ico",
    onefile=True,           # Single .exe — easy to distribute
)
