"""
LazyDesk — Local AI File Organizer
===================================
A beginner-friendly, local desktop organizer powered by Streamlit and Ollama (gemma3:1b).
Sorts your messy folders into clean, organized categories without uploading any data to the cloud.
"""

import datetime
import json
import os
import shutil
import urllib.error
import urllib.request
import streamlit as st

# ==============================================================================
# Configuration & Constants
# ==============================================================================

SUPPORTED_CATEGORIES = [
    "Documents",
    "Study Notes",
    "Images",
    "Code",
    "Spreadsheets",
    "Videos",
    "Archives",
    "Other",
]

DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "gemma3:1b"

# Extension mapping for rule-based fallback
EXTENSION_MAP = {
    # Documents
    ".pdf": "Documents",
    ".docx": "Documents",
    ".doc": "Documents",
    ".txt": "Documents",
    ".rtf": "Documents",
    ".odt": "Documents",
    ".epub": "Documents",
    ".md": "Documents",
    ".pptx": "Documents",
    ".ppt": "Documents",
    # Spreadsheets
    ".xlsx": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".tsv": "Spreadsheets",
    ".ods": "Spreadsheets",
    ".xlsm": "Spreadsheets",
    # Images
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".gif": "Images",
    ".svg": "Images",
    ".webp": "Images",
    ".bmp": "Images",
    ".ico": "Images",
    ".tiff": "Images",
    ".tif": "Images",
    # Code
    ".py": "Code",
    ".js": "Code",
    ".jsx": "Code",
    ".ts": "Code",
    ".tsx": "Code",
    ".html": "Code",
    ".css": "Code",
    ".json": "Code",
    ".yaml": "Code",
    ".yml": "Code",
    ".xml": "Code",
    ".java": "Code",
    ".cpp": "Code",
    ".c": "Code",
    ".cs": "Code",
    ".go": "Code",
    ".rs": "Code",
    ".php": "Code",
    ".rb": "Code",
    ".sh": "Code",
    ".bat": "Code",
    ".cmd": "Code",
    ".ps1": "Code",
    ".sql": "Code",
    # Videos
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".avi": "Videos",
    ".mov": "Videos",
    ".wmv": "Videos",
    ".flv": "Videos",
    ".webm": "Videos",
    ".m4v": "Videos",
    # Archives
    ".zip": "Archives",
    ".rar": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".7z": "Archives",
    ".bz2": "Archives",
    ".xz": "Archives",
    ".tgz": "Archives",
    ".iso": "Archives",
}

# Keywords indicating study notes
STUDY_KEYWORDS = [
    "lecture",
    "lecture_",
    "note",
    "notes",
    "study",
    "cheat_sheet",
    "cheatsheet",
    "exam",
    "homework",
    "assignment",
    "syllabus",
    "coursework",
    "revision",
    "summary",
    "quiz",
    "midterm",
    "final_exam",
]

# Sample files for Demo Mode
DEMO_FILES = [
    {"name": "CS101_Lecture_04_Recursion.pdf", "size_kb": 1420},
    {"name": "quarterly_budget_2026.xlsx", "size_kb": 86},
    {"name": "app_backend_server.py", "size_kb": 18},
    {"name": "website_hero_dark.png", "size_kb": 2340},
    {"name": "project_archive_backup.zip", "size_kb": 15400},
    {"name": "system_demo_walkthrough.mp4", "size_kb": 48200},
    {"name": "annual_employment_contract.docx", "size_kb": 125},
    {"name": "biology_exam_cheat_sheet.txt", "size_kb": 42},
    {"name": "customer_churn_analysis.csv", "size_kb": 310},
    {"name": "docker-compose.yml", "size_kb": 6},
    {"name": "family_vacation_sunset.jpeg", "size_kb": 3810},
    {"name": "debug_diagnostics.log", "size_kb": 54},
    {"name": "presentation_slides_draft.pptx", "size_kb": 6700},
]

# ==============================================================================
# Helper Functions: Core Logic & Ollama AI
# ==============================================================================

def get_fallback_category(filename: str) -> str:
    """
    Determines category based on filename keywords or file extension.
    Used when Ollama is offline or produces an unmapped output.
    """
    name_lower = filename.lower()
    base_name, ext = os.path.splitext(name_lower)

    # First check if filename suggests study notes
    for kw in STUDY_KEYWORDS:
        if kw in base_name:
            return "Study Notes"

    # Match by extension
    if ext in EXTENSION_MAP:
        return EXTENSION_MAP[ext]

    return "Other"


def check_ollama_status(api_url: str, model_name: str) -> tuple[str, str]:
    """
    Checks if Ollama is accessible and whether the required model is installed.
    Returns (status_key, message):
      - 'READY': Server online and model available.
      - 'MODEL_MISSING': Server online, but model is not pulled yet.
      - 'OFFLINE': Cannot connect to Ollama server.
    """
    base_url = api_url.rsplit("/api/", 1)[0]
    tags_url = f"{base_url}/api/tags"

    try:
        req = urllib.request.Request(tags_url, headers={"User-Agent": "LazyDesk"})
        with urllib.request.urlopen(req, timeout=1.8) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                # Check model presence (matching full or tag prefix)
                model_found = any(
                    m == model_name or m.startswith(f"{model_name}:") or m.startswith(model_name)
                    for m in models
                )
                if model_found:
                    return "READY", f"Ollama connected. Model '{model_name}' is ready."
                return (
                    "MODEL_MISSING",
                    f"Ollama is running, but model '{model_name}' is not installed. Run 'ollama run {model_name}' in your terminal.",
                )
            return "OFFLINE", f"Ollama returned unexpected HTTP {response.status}."
    except Exception:
        return (
            "OFFLINE",
            f"Ollama is unreachable at {base_url}. Ensure Ollama is running ('ollama serve').",
        )


def classify_with_ollama(
    filename: str, api_url: str = DEFAULT_OLLAMA_URL, model_name: str = DEFAULT_MODEL, timeout_sec: float = 3.5
) -> tuple[str, str]:
    """
    Sends the filename to Ollama to suggest a category.
    Strictly passes only the filename (never file contents) to ensure 100% privacy and speed.
    Falls back to extension-based categorization on failure or invalid output.
    """
    prompt = (
        "You are an automated file organizer. Categorize the file based solely on its filename into "
        "exactly ONE of these categories:\n"
        "Documents, Study Notes, Images, Code, Spreadsheets, Videos, Archives, Other.\n\n"
        f'Filename: "{filename}"\n\n'
        "Instructions:\n"
        "- 'Study Notes': lecture notes, exam prep, study guides, homework, coursework, summaries.\n"
        "- 'Documents': PDF files, text documents, Word files, reports, contracts.\n"
        "- 'Spreadsheets': Excel, CSV, tabular financial or data files.\n"
        "- 'Code': programming scripts, markup, source files, config files.\n"
        "- 'Images': pictures, screenshots, graphics, photos.\n"
        "- 'Videos': recordings, video files, clips.\n"
        "- 'Archives': zip, rar, tar, compressed archives.\n"
        "- 'Other': anything else.\n\n"
        "Return ONLY the exact category name and nothing else."
    )

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,  # Low temperature for deterministic classification
            "num_predict": 10,
        },
    }

    try:
        json_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            api_url,
            data=json_data,
            headers={"Content-Type": "application/json", "User-Agent": "LazyDesk"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            if resp.status == 200:
                result = json.loads(resp.read().decode("utf-8"))
                raw_response = result.get("response", "").strip().strip('"').strip("'").strip(".").strip()
                
                # Verify if returned output matches one of the 8 categories
                for category in SUPPORTED_CATEGORIES:
                    if category.lower() == raw_response.lower() or raw_response.lower().startswith(category.lower()):
                        return category, f"AI ({model_name})"

    except Exception:
        # Fallback cleanly on network errors, timeouts, or uninstalled models
        pass

    # Fallback to extension/keyword rules
    fallback_cat = get_fallback_category(filename)
    return fallback_cat, "Rule Fallback"


def resolve_safe_target_path(base_dir: str, category: str, filename: str) -> str:
    """
    Safely resolves the target destination path inside base_dir/category.
    Ensures:
      1. Destination stays strictly inside base_dir (prevents directory traversal).
      2. Never overwrites existing files (automatically generates 'name (1).ext' if collision).
    """
    clean_filename = os.path.basename(filename)
    if category not in SUPPORTED_CATEGORIES:
        category = "Other"

    base_abs = os.path.abspath(base_dir)
    target_dir = os.path.abspath(os.path.join(base_abs, category))

    # Path traversal protection
    if os.path.commonpath([base_abs, target_dir]) != base_abs:
        raise ValueError(f"Security error: Target directory outside base folder: {target_dir}")

    target_file = os.path.abspath(os.path.join(target_dir, clean_filename))
    if os.path.commonpath([base_abs, target_file]) != base_abs:
        raise ValueError(f"Security error: Target file outside base folder: {target_file}")

    # Overwrite protection: If file already exists, find safe unique suffix
    if os.path.exists(target_file):
        stem, ext = os.path.splitext(clean_filename)
        counter = 1
        while True:
            candidate = os.path.join(target_dir, f"{stem} ({counter}){ext}")
            if not os.path.exists(candidate):
                target_file = candidate
                break
            counter += 1

    return target_file


def format_size(size_bytes: int) -> str:
    """Converts bytes to human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"


def scan_directory(folder_path: str) -> list[dict]:
    """
    Scans immediate files in the given folder (non-recursive).
    Returns list of file metadata dictionaries.
    """
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")
    if not os.path.isdir(folder_path):
        raise NotADirectoryError(f"Provided path is a file, not a directory: {folder_path}")

    files_found = []
    # Immediate files only (never scan subfolders)
    with os.scandir(folder_path) as entries:
        for entry in entries:
            try:
                if entry.is_file(follow_symlinks=False):
                    stat = entry.stat()
                    files_found.append({
                        "name": entry.name,
                        "current_path": entry.path,
                        "size_bytes": stat.st_size,
                        "size_formatted": format_size(stat.st_size),
                    })
            except (PermissionError, OSError):
                # Skip locked or inaccessible files safely
                continue

    return sorted(files_found, key=lambda x: x["name"].lower())


# ==============================================================================
# Streamlit Interface
# ==============================================================================

def main():
    st.set_page_config(
        page_title="LazyDesk — Local AI File Organizer",
        page_icon="🗂️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Custom Styling: Modern dark navy theme with subtle emerald green accents
    st.markdown(
        """
        <style>
        /* Dark navy background & typography */
        .stApp {
            background-color: #0b1120;
            color: #f1f5f9;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }
        
        /* Sidebar styling */
        [data-testid="stSidebar"] {
            background-color: #070d19;
            border-right: 1px solid #1e293b;
        }

        /* Headings */
        h1, h2, h3, h4 {
            color: #f8fafc !important;
            font-weight: 700;
            letter-spacing: -0.02em;
        }
        
        /* Brand Accent */
        .accent-green {
            color: #10b981;
        }

        /* Cards / Containers */
        .lz-card {
            background-color: #111b2e;
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 18px 22px;
            margin-bottom: 18px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }

        .lz-metric-card {
            background-color: #111b2e;
            border: 1px solid #1e293b;
            border-radius: 10px;
            padding: 14px 18px;
            text-align: center;
        }
        .lz-metric-val {
            font-size: 1.8rem;
            font-weight: 700;
            color: #10b981;
        }
        .lz-metric-label {
            font-size: 0.85rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        /* Badges */
        .lz-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-ai {
            background-color: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .badge-rule {
            background-color: rgba(148, 163, 184, 0.15);
            color: #cbd5e1;
            border: 1px solid rgba(148, 163, 184, 0.3);
        }
        .badge-demo {
            background-color: rgba(245, 158, 11, 0.15);
            color: #fbbf24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        /* Button Styling */
        div.stButton > button {
            background-color: #0f766e;
            color: #ffffff;
            border: 1px solid #14b8a6;
            border-radius: 8px;
            font-weight: 600;
            padding: 8px 18px;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background-color: #10b981;
            border-color: #34d399;
            color: #052e16;
            transform: translateY(-1px);
        }

        /* Primary approve button */
        .primary-btn > div.stButton > button {
            background-color: #10b981 !important;
            color: #022c22 !important;
            font-weight: 700 !important;
            border: 1px solid #34d399 !important;
        }
        .primary-btn > div.stButton > button:hover {
            background-color: #34d399 !important;
            box-shadow: 0 0 12px rgba(16, 185, 129, 0.4);
        }

        /* Input fields */
        .stTextInput > div > div > input {
            background-color: #070d19;
            color: #f1f5f9;
            border: 1px solid #1e293b;
            border-radius: 8px;
        }
        .stTextInput > div > div > input:focus {
            border-color: #10b981;
            box-shadow: 0 0 0 1px #10b981;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize Session State
    if "scanned_items" not in st.session_state:
        st.session_state.scanned_items = []
    if "scan_folder" not in st.session_state:
        st.session_state.scan_folder = ""
    if "is_demo" not in st.session_state:
        st.session_state.is_demo = False
    if "activity_log" not in st.session_state:
        st.session_state.activity_log = []
    if "last_batch" not in st.session_state:
        st.session_state.last_batch = []
    if "show_plan" not in st.session_state:
        st.session_state.show_plan = False

    # --------------------------------------------------------------------------
    # Sidebar
    # --------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### 🗂️ **LazyDesk**")
        st.caption("Local AI Desktop File Organizer")
        st.markdown("---")

        # Demo Mode Switch
        st.markdown("#### 🧪 Mode Selection")
        demo_toggle = st.toggle(
            "Enable Demo Mode",
            value=st.session_state.is_demo,
            help="Explore the interface and AI classification with sample files safely without altering real files.",
        )
        if demo_toggle != st.session_state.is_demo:
            st.session_state.is_demo = demo_toggle
            st.session_state.scanned_items = []
            st.session_state.show_plan = False
            st.rerun()

        if st.session_state.is_demo:
            st.markdown(
                '<span class="lz-badge badge-demo">⚠️ DEMO MODE ACTIVE (Simulated Safe Sandbox)</span>',
                unsafe_allow_html=True,
            )
            st.caption("No files will be modified on disk during demo mode.")

        st.markdown("---")
        st.markdown("#### 🤖 Local Ollama Settings")

        api_url = st.text_input("Ollama API URL", value=DEFAULT_OLLAMA_URL)
        model_name = st.text_input("Model Name", value=DEFAULT_MODEL)

        # Check Ollama Connectivity
        status_key, status_msg = check_ollama_status(api_url, model_name)

        if status_key == "READY":
            st.success("🟢 Ollama Connected & Ready", icon="✅")
            st.caption(f"Model `{model_name}` detected.")
        elif status_key == "MODEL_MISSING":
            st.warning("🟡 Model Not Found", icon="⚠️")
            st.info(f"Ollama is running, but model `{model_name}` is missing.\n\nRun:\n```bash\nollama run {model_name}\n```")
            st.caption("Rule-based extension fallback will be used.")
        else:
            st.error("🔴 Ollama Offline", icon="❌")
            st.caption("Ollama service not detected on localhost:11434.")
            with st.expander("How to start Ollama"):
                st.markdown(
                    """
                    1. Install Ollama from [ollama.com](https://ollama.com).
                    2. Start the service:
                       ```bash
                       ollama serve
                       ```
                    3. Download the model:
                       ```bash
                       ollama run gemma3:1b
                       ```
                    *(LazyDesk will use extension fallback while Ollama is offline).*
                    """
                )

        st.markdown("---")
        st.markdown("#### 📁 Supported Categories")
        with st.expander("View 8 Supported Categories", expanded=False):
            for cat in SUPPORTED_CATEGORIES:
                st.markdown(f"- **{cat}**")
        
        st.markdown("---")
        st.caption("🔒 **100% Private & Local**: Only filenames are inspected. No file contents are read or uploaded.")

    # --------------------------------------------------------------------------
    # Main Dashboard
    # --------------------------------------------------------------------------
    st.markdown(
        """
        <div style="margin-bottom: 24px;">
            <h1 style="display: inline-block; margin-bottom: 4px;">LazyDesk <span class="accent-green">File Organizer</span></h1>
            <p style="color: #94a3b8; font-size: 1.05rem; margin-top: 0;">
                Categorize and clean up messy folders using local AI (Gemma 3 1B) with extension fallback and safe undo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Step 1: Folder Input & Scan Action
    st.markdown("### 1. Select Folder to Organize")

    col_input, col_action = st.columns([3, 1], gap="medium")

    with col_input:
        if st.session_state.is_demo:
            folder_input = st.text_input(
                "Target Folder Path",
                value="[DEMO VIRTUAL SANDBOX] C:/Users/DemoUser/Downloads",
                disabled=True,
                help="Demo mode uses a virtual set of sample files.",
            )
        else:
            folder_input = st.text_input(
                "Target Folder Path",
                value=st.session_state.scan_folder or os.getcwd(),
                placeholder="e.g. C:\\Users\\YourName\\Downloads",
                help="Enter the absolute path to the directory containing files you want to organize.",
            )

    with col_action:
        st.write("")  # Vertical spacing alignment
        st.write("")
        scan_clicked = st.button("🔍 Scan & Suggest Categories", use_container_width=True)

    # Processing Scan Request
    if scan_clicked:
        st.session_state.scanned_items = []
        st.session_state.show_plan = False

        if st.session_state.is_demo:
            base_dir = "C:/Users/DemoUser/Downloads"
            st.session_state.scan_folder = base_dir
            
            progress_bar = st.progress(0, text="Classifying sample files with Ollama...")
            total_demo = len(DEMO_FILES)
            
            scanned_list = []
            for idx, item in enumerate(DEMO_FILES):
                filename = item["name"]
                progress_bar.progress((idx + 1) / total_demo, text=f"Analyzing: {filename}")
                
                category, method = classify_with_ollama(filename, api_url, model_name)
                target_path = f"{base_dir}/{category}/{filename}"
                
                scanned_list.append({
                    "name": filename,
                    "current_path": f"{base_dir}/{filename}",
                    "size_formatted": f"{item['size_kb']} KB",
                    "category": category,
                    "target_path": target_path,
                    "method": method,
                })
                
            progress_bar.empty()
            st.session_state.scanned_items = scanned_list
            st.session_state.show_plan = True

            st.session_state.activity_log.append({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "action": "Scan (Demo)",
                "details": f"Scanned {len(scanned_list)} sample demo files.",
                "status": "Success",
            })

        else:
            clean_path = folder_input.strip().strip('"').strip("'")
            
            if not clean_path:
                st.error("Please provide a valid folder path.", icon="⚠️")
            elif not os.path.exists(clean_path):
                st.error(f"Directory not found: '{clean_path}'. Please check the path and try again.", icon="❌")
            elif not os.path.isdir(clean_path):
                st.error(f"The path '{clean_path}' is a file, not a directory.", icon="❌")
            else:
                try:
                    base_dir = os.path.abspath(clean_path)
                    st.session_state.scan_folder = base_dir
                    raw_files = scan_directory(base_dir)

                    if not raw_files:
                        st.warning(f"No immediate files found in '{base_dir}'. (LazyDesk does not scan subdirectories).", icon="ℹ️")
                    else:
                        progress_bar = st.progress(0, text="Classifying files with Ollama / Fallback...")
                        total_files = len(raw_files)
                        scanned_list = []

                        for idx, file_info in enumerate(raw_files):
                            filename = file_info["name"]
                            progress_bar.progress((idx + 1) / total_files, text=f"Scanning ({idx+1}/{total_files}): {filename}")
                            
                            category, method = classify_with_ollama(filename, api_url, model_name)
                            
                            try:
                                target_path = resolve_safe_target_path(base_dir, category, filename)
                            except Exception as e:
                                target_path = f"[Security blocked: {e}]"

                            scanned_list.append({
                                "name": filename,
                                "current_path": file_info["current_path"],
                                "size_formatted": file_info["size_formatted"],
                                "category": category,
                                "target_path": target_path,
                                "method": method,
                            })

                        progress_bar.empty()
                        st.session_state.scanned_items = scanned_list
                        st.session_state.show_plan = True

                        st.session_state.activity_log.append({
                            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "action": "Scan",
                            "details": f"Scanned {len(scanned_list)} files in {base_dir}",
                            "status": "Success",
                        })

                except PermissionError:
                    st.error(f"Permission denied when reading folder '{clean_path}'. Please check folder permissions.", icon="🔒")
                except Exception as e:
                    st.error(f"An error occurred while scanning: {e}", icon="💥")

    # Step 2: Proposed Movements Preview & Approval
    if st.session_state.show_plan and st.session_state.scanned_items:
        st.markdown("---")
        st.markdown("### 2. Preview Proposed Organization")
        st.info(
            "🛡️ **Safety Preview**: No files have been moved yet. Review the proposed destinations below. "
            "Files will only move when you explicitly click **'Confirm & Organize Files'**.",
            icon="ℹ️",
        )

        items = st.session_state.scanned_items
        total_count = len(items)
        ai_count = sum(1 for item in items if "AI" in item["method"])
        rule_count = total_count - ai_count

        # Metrics summary
        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            st.markdown(
                f'<div class="lz-metric-card"><div class="lz-metric-val">{total_count}</div><div class="lz-metric-label">Files Discovered</div></div>',
                unsafe_allow_html=True,
            )
        with m_col2:
            st.markdown(
                f'<div class="lz-metric-card"><div class="lz-metric-val" style="color:#34d399;">{ai_count}</div><div class="lz-metric-label">AI Categorized</div></div>',
                unsafe_allow_html=True,
            )
        with m_col3:
            st.markdown(
                f'<div class="lz-metric-card"><div class="lz-metric-val" style="color:#94a3b8;">{rule_count}</div><div class="lz-metric-label">Extension Fallback</div></div>',
                unsafe_allow_html=True,
            )
        with m_col4:
            cat_set = len(set(i["category"] for i in items))
            st.markdown(
                f'<div class="lz-metric-card"><div class="lz-metric-val" style="color:#60a5fa;">{cat_set}</div><div class="lz-metric-label">Target Subfolders</div></div>',
                unsafe_allow_html=True,
            )

        st.write("")

        # Interactive Table
        st.markdown("#### Proposed Moves Table")
        st.caption("Inspect the suggested destination and classification source for each file:")

        table_display = []
        for item in items:
            table_display.append({
                "File Name": item["name"],
                "Size": item["size_formatted"],
                "Suggested Category": item["category"],
                "Destination Subfolder": f"{item['category']}/",
                "Classification Source": item["method"],
            })

        st.dataframe(
            table_display,
            use_container_width=True,
            hide_index=True,
        )

        # Move Confirmation Button
        st.markdown("### 3. Approve and Execute")
        st.caption("Existing destination files with the same name are never overwritten (safe copy suffixes are appended automatically).")

        act_col1, act_col2 = st.columns([2, 3])

        with act_col1:
            st.markdown('<div class="primary-btn">', unsafe_allow_html=True)
            approve_clicked = st.button("🚀 Confirm & Organize Files", use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        with act_col2:
            cancel_clicked = st.button("❌ Cancel / Clear Preview")

        if cancel_clicked:
            st.session_state.scanned_items = []
            st.session_state.show_plan = False
            st.rerun()

        # Execution Logic
        if approve_clicked:
            moved_records = []
            failed_records = []

            if st.session_state.is_demo:
                for item in items:
                    moved_records.append({
                        "source": item["current_path"],
                        "destination": item["target_path"],
                        "filename": item["name"],
                        "category": item["category"],
                        "is_demo": True,
                    })

                st.session_state.last_batch = moved_records
                st.session_state.activity_log.append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "Organize (Demo)",
                    "details": f"Simulated movement of {len(moved_records)} files into organized subfolders.",
                    "status": "Success",
                })
                st.session_state.show_plan = False
                st.session_state.scanned_items = []
                st.success(f"🎉 Demo Simulated Successfully! {len(moved_records)} files organized in virtual sandbox.", icon="✅")

            else:
                base_dir = st.session_state.scan_folder
                progress_move = st.progress(0, text="Moving files...")

                for idx, item in enumerate(items):
                    progress_move.progress((idx + 1) / len(items), text=f"Moving: {item['name']}")
                    src = item["current_path"]
                    cat = item["category"]

                    try:
                        dest_folder = os.path.join(base_dir, cat)
                        os.makedirs(dest_folder, exist_ok=True)

                        dest = resolve_safe_target_path(base_dir, cat, item["name"])

                        shutil.move(src, dest)
                        moved_records.append({
                            "source": src,
                            "destination": dest,
                            "filename": item["name"],
                            "category": cat,
                            "is_demo": False,
                        })

                    except Exception as err:
                        failed_records.append({"filename": item["name"], "error": str(err)})

                progress_move.empty()
                st.session_state.last_batch = moved_records
                st.session_state.show_plan = False
                st.session_state.scanned_items = []

                status_str = "Success" if not failed_records else f"Partial ({len(failed_records)} errors)"
                st.session_state.activity_log.append({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "action": "Organize",
                    "details": f"Moved {len(moved_records)} files successfully. Failed: {len(failed_records)}.",
                    "status": status_str,
                })

                if failed_records:
                    st.warning(f"Moved {len(moved_records)} files. {len(failed_records)} files encountered errors.", icon="⚠️")
                    for f in failed_records:
                        st.error(f"Failed to move {f['filename']}: {f['error']}")
                else:
                    st.success(f"🎉 Successfully organized {len(moved_records)} files into respective folders!", icon="✅")

    # Step 4: Undo Feature & Activity Log
    st.markdown("---")
    st.markdown("### 4. Activity Log & Undo")

    undo_col, clear_col = st.columns([1, 1])

    with undo_col:
        has_last_batch = bool(st.session_state.last_batch)
        batch_count = len(st.session_state.last_batch)
        undo_label = f"↩️ Undo Last Batch ({batch_count} files)" if has_last_batch else "↩️ Undo Last Batch (None)"
        undo_clicked = st.button(undo_label, disabled=not has_last_batch, use_container_width=True)

    with clear_col:
        clear_log_clicked = st.button("🗑️ Clear Activity Log", use_container_width=True)

    if clear_log_clicked:
        st.session_state.activity_log = []
        st.rerun()

    if undo_clicked and st.session_state.last_batch:
        batch = st.session_state.last_batch
        undone_count = 0
        undo_errors = []

        for item in batch:
            if item.get("is_demo", False):
                undone_count += 1
            else:
                dest = item["destination"]
                src = item["source"]
                try:
                    if os.path.exists(dest):
                        if os.path.exists(src):
                            stem, ext = os.path.splitext(os.path.basename(src))
                            src = os.path.join(os.path.dirname(src), f"{stem}_restored{ext}")
                        shutil.move(dest, src)
                        undone_count += 1
                    else:
                        undo_errors.append(f"File not found at destination: {dest}")
                except Exception as e:
                    undo_errors.append(f"Could not restore {item['filename']}: {e}")

        st.session_state.last_batch = []

        st.session_state.activity_log.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "Undo Batch",
            "details": f"Restored {undone_count} files to original locations. Errors: {len(undo_errors)}.",
            "status": "Success" if not undo_errors else "Partial",
        })

        if undo_errors:
            st.warning(f"Restored {undone_count} files. Encountered {len(undo_errors)} issues.", icon="⚠️")
            for err in undo_errors:
                st.error(err)
        else:
            st.success(f"↩️ Successfully restored {undone_count} files to their original locations!", icon="✅")

    # Display Activity History
    if st.session_state.activity_log:
        st.markdown("#### Recent Operations")
        log_display = []
        for entry in reversed(st.session_state.activity_log):
            log_display.append({
                "Timestamp": entry.get("timestamp", "-"),
                "Action": entry.get("action", "-"),
                "Details": entry.get("details", "-"),
                "Status": entry.get("status", "-"),
            })
        st.dataframe(log_display, use_container_width=True, hide_index=True)
    else:
        st.caption("No activity recorded yet. Scanned operations and file movements will appear here.")


if __name__ == "__main__":
    main()
