# Creating a Windows Executable Package

## Quick Method (Simplest)

### On your development machine:

1. **Install PyInstaller** (one time only):
   ```
   pip install pyinstaller
   ```

2. **Run the build script**:
   ```
   python make_exe.py
   ```

3. **Package for distribution**:
   - You'll get two files:
     - `PLC_Toolkit.exe` (15-20 MB)
     - `Run_Toolkit.bat` (launcher)
   - Zip these together
   - Send to users

### For end users:

1. Extract the zip file
2. Double-click `Run_Toolkit.bat`
3. That's it! No Python needed

---

## Alternative Methods

### Method A: Full Package Builder
```bash
python build_windows.py
```
Creates a complete package with README and config files.

### Method B: Windows Batch Builder
```batch
BUILD_WINDOWS_EXE.bat
```
Run this on a Windows machine with Python installed.

---

## What Gets Packaged

The executable includes:
- **Python interpreter** (embedded)
- **pycomm3** (PLC communication)
- **openpyxl** (Excel support)
- **SQLite** (database)
- All standard libraries

**Not included** (created on first run):
- `plc_data.db` (database file)
- `plc_scans/` folder
- User data files

---

## Distribution Options

### Option 1: Simple ZIP
```
PLC_Toolkit.zip
├── PLC_Toolkit.exe
└── Run_Toolkit.bat
```

### Option 2: With Documentation
```
PLC_Toolkit_Package.zip
├── PLC_Toolkit.exe
├── Run_Toolkit.bat
├── Quick_Start.txt
└── config.ini (optional)
```

### Option 3: Network Share
Place files on a shared drive:
```
\\server\tools\PLC_Toolkit\
├── PLC_Toolkit.exe
└── Run_Toolkit.bat
```

---

## Troubleshooting

**"Windows protected your PC" warning:**
- Click "More info"
- Click "Run anyway"
- This happens with unsigned executables

**Antivirus flags the exe:**
- Add exception for PLC_Toolkit.exe
- PyInstaller executables sometimes trigger false positives

**Missing DLL errors:**
- Install Visual C++ Redistributable 2019
- Available from Microsoft

**Very slow to start first time:**
- Windows Defender scans new executables
- Subsequent runs will be faster

---

## File Size Optimization

The executable will be 15-20 MB. To reduce size:

1. **Use UPX compression** (adds to build command):
   ```
   --upx-dir=C:\path\to\upx
   ```

2. **Exclude more modules**:
   ```python
   # In make_exe.py, add more excludes:
   "--exclude-module", "test",
   "--exclude-module", "unittest",
   ```

3. **Use folder distribution** instead of onefile:
   ```
   # Remove --onefile flag
   # Creates folder with exe + DLLs
   ```

---

## Testing Package

Before distributing:

1. **Test on clean Windows machine** (no Python)
2. **Test with different PLC models**
3. **Test with restricted user accounts**
4. **Verify all export formats work**

---

## Update Process

When you update the code:

1. Modify `plc_toolkit_consolidated.py`
2. Run `python make_exe.py`
3. Distribute new `PLC_Toolkit.exe`
4. Users replace their old exe file

---

## License and Credits

Include in documentation:
- Created by Scott Adams
- Uses pycomm3 (MIT License)
- Uses openpyxl (MIT License)
