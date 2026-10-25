# 🗂️ LazyDesk — Local AI File Organizer

> A beginner-friendly, privacy-first desktop file organizer powered by **Python**, **Streamlit**, and **local Ollama (`gemma3:1b`)**.

LazyDesk scans messy folders (such as `Downloads` or `Desktop`) and automatically sorts files into dedicated categories. It keeps all data strictly local on your machine—**no file contents are read or uploaded to the cloud**.

---
## ✅ Project Status

- [x] Core file categorization and extension fallback
- [x] Demo mode for safe exploration
- [x] File movement and undo tests
- [x] Path traversal and overwrite protection tests
- [x] Automated test suite: 8 tests passing

## ✨ Main Features

1. **Modern Dark Navy UI**: Clean typography, dark navy aesthetic (`#0b1120`), and subtle emerald green accents.
2. **Local AI Classification**: Uses Ollama's local `gemma3:1b` model (`http://localhost:11434/api/generate`) to intelligently categorize files by filename.
3. **8 Supported Categories**:
   - `Documents` (PDFs, Word docs, text files, presentations)
   - `Study Notes` (Lecture notes, cheat sheets, exam revisions, coursework)
   - `Images` (PNG, JPG, SVG, WebP, GIF, etc.)
   - `Code` (Python, JavaScript, HTML, CSS, JSON, scripts, etc.)
   - `Spreadsheets` (Excel, CSV, TSV, financial tables)
   - `Videos` (MP4, MKV, AVI, screen recordings, clips)
   - `Archives` (ZIP, RAR, 7z, TAR, GZ)
   - `Other` (Unrecognized or miscellaneous files)
4. **Reliable Rule-Based Fallback**: Automatically falls back to extension and keyword matching if Ollama is offline, slow, or returns an unmapped category.
5. **Interactive Preview**: Shows proposed destinations and classification sources before changing anything. **Scanning never moves files automatically**.
6. **Explicit User Approval**: Files are moved only after you click **"Confirm & Organize Files"**.
7. **Zero-Data-Loss & Traversal Security**:
   - **Never overwrites**: If a file with the same name exists at the destination, a safe numbered suffix (`file (1).ext`) is created.
   - **Path Traversal Protection**: Ensures all files stay strictly inside the selected folder.
8. **Undo Last Batch**: Reverse the most recent file moves with a single click.
9. **Activity Log**: Real-time log tracking scans, moves, errors, and undo operations.
10. **Demo Mode**: Built-in safe sandbox with realistic sample files to explore the app without touching real disk files.
11. **Clear Diagnostics**: Helpful error banners for offline Ollama, missing models, invalid paths, and permissions.

---

## 🛠️ Tech Stack

- **Python 3.10+**
- **Streamlit** (Web UI dashboard)
- **Ollama** with **gemma3:1b** (Local lightweight LLM)
- **Standard Library** (`os`, `shutil`, `urllib`, `json`, `datetime`)

---

## 📋 Prerequisites

1. **Python 3.10 or higher** installed on Windows.
2. **Ollama** installed from [ollama.com](https://ollama.com).

---

## 🚀 Windows Installation & Run Instructions

Follow these exact steps in **PowerShell** or **Command Prompt**:

### Step 1: Open Terminal in the Project Directory
```powershell
cd path\to\Lazydesk
```

### Step 2: Create and Activate a Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### Step 3: Install Required Dependencies
```powershell
pip install -r requirements.txt
```

### Step 4: Install & Start Ollama with `gemma3:1b`
1. Download and install Ollama from [ollama.com/download/windows](https://ollama.com/download/windows).
2. Pull and test the `gemma3:1b` model:
   ```powershell
   ollama run gemma3:1b
   ```
   *(You can type `/bye` to exit the chat prompt once it downloads).*
3. Make sure the Ollama server is running in the background (Ollama runs automatically in the system tray, or run `ollama serve`).

### Step 5: Launch the Application
```powershell
streamlit run app.py
```
Your browser will open automatically at:
```
http://localhost:8501
```

---

## 🧪 Quick Walkthrough

### 1. Test in Demo Mode (Zero Risk)
1. In the left sidebar, toggle **"Enable Demo Mode"**.
2. Click **"🔍 Scan & Suggest Categories"**.
3. Inspect the proposed moves table and the AI / Rule Fallback badges.
4. Click **"🚀 Confirm & Organize Files"** to simulate the organization.
5. Click **"↩️ Undo Last Batch"** to test reversing the operation.

### 2. Organize a Real Folder
1. Toggle off Demo Mode.
2. Enter your folder path (e.g. `C:\Users\dell\Downloads` or a test folder).
3. Click **"🔍 Scan & Suggest Categories"**.
4. Review the generated plan in the **Proposed Moves Table**.
5. Click **"🚀 Confirm & Organize Files"**.
6. Check your folder: subdirectories for each category have been neatly created, with your files sorted inside!

---

## 🛡️ Privacy & Safety Design

- **Local Only**: No cloud API keys, external servers, or network calls outside `localhost`.
- **Filename-Only Prompting**: The app sends only the filename string to Ollama (e.g., `"quarterly_budget_2026.xlsx"`). File contents are never opened or read.
- **Immediate Files Only**: Scanning is non-recursive; it only checks files in the immediate folder, leaving existing subfolders untouched.
- **Collision Avoidance**: If `Documents/report.pdf` already exists, a new incoming file will be saved as `Documents/report (1).pdf` without destroying previous data.

---

## 🧪 Running Unit Tests

To run the automated test suite:

```powershell
python -m pytest -v
```

All tests run locally in milliseconds and verify:
- Category matching and extension fallbacks
- Non-recursive directory scanning
- Safe path resolution and directory traversal blocks
- Automatic suffix numbering for overwrite prevention
- Move and undo cycles

---

## ❓ Troubleshooting

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Ollama Offline" banner** | Ollama is not running on port 11434. | Open terminal and run `ollama serve`. In the meantime, rule fallback will sort your files. |
| **"Model Not Found" banner** | `gemma3:1b` is not installed yet. | Run `ollama run gemma3:1b` in terminal to download the weights. |
| **"Directory not found"** | The typed path has a typo or doesn't exist. | Double check your folder path in Windows File Explorer and paste it into the input. |
| **"Permission denied"** | Folder has restricted system permissions. | Choose a user folder (like `Downloads` or `Documents`) or run the terminal as Administrator. |

---

## 📄 License

MIT License — free to use, modify, and learn from!
