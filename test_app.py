"""
Comprehensive Unit Tests for LazyDesk (app.py)
Tests classification, security guards, file scanning, and movement simulation.
"""
import os
import shutil
import sys
import tempfile
import types
import unittest

# Create a lightweight mock for streamlit so app.py functions can be imported and tested
mock_st = types.ModuleType("streamlit")
mock_st.set_page_config = lambda **kwargs: None
mock_st.markdown = lambda *args, **kwargs: None
mock_st.caption = lambda *args, **kwargs: None
mock_st.info = lambda *args, **kwargs: None
mock_st.warning = lambda *args, **kwargs: None
mock_st.error = lambda *args, **kwargs: None
mock_st.success = lambda *args, **kwargs: None
mock_st.progress = lambda *args, **kwargs: types.SimpleNamespace(progress=lambda *a, **k: None, empty=lambda: None)
mock_st.sidebar = types.SimpleNamespace(__enter__=lambda: None, __exit__=lambda *a: None)
mock_st.columns = lambda n, **kwargs: [types.SimpleNamespace(__enter__=lambda: None, __exit__=lambda *a: None) for _ in range(n if isinstance(n, int) else len(n))]
mock_st.expander = lambda *args, **kwargs: types.SimpleNamespace(__enter__=lambda: None, __exit__=lambda *a: None)
mock_st.text_input = lambda *args, **kwargs: ""
mock_st.button = lambda *args, **kwargs: False
mock_st.toggle = lambda *args, **kwargs: False
mock_st.dataframe = lambda *args, **kwargs: None
mock_st.rerun = lambda: None
mock_st.session_state = {}

sys.modules["streamlit"] = mock_st

# Import app module
import app


class TestLazyDeskApp(unittest.TestCase):
    def test_supported_categories(self):
        expected_categories = [
            "Documents",
            "Study Notes",
            "Images",
            "Code",
            "Spreadsheets",
            "Videos",
            "Archives",
            "Other",
        ]
        self.assertEqual(app.SUPPORTED_CATEGORIES, expected_categories)

    def test_study_notes_classification(self):
        # Study notes by filename keywords
        self.assertEqual(app.get_fallback_category("math_lecture_03.pdf"), "Study Notes")
        self.assertEqual(app.get_fallback_category("biology_exam_notes.txt"), "Study Notes")
        self.assertEqual(app.get_fallback_category("python_cheat_sheet.docx"), "Study Notes")
        self.assertEqual(app.get_fallback_category("history_homework_week2.pdf"), "Study Notes")

    def test_extension_fallback_classification(self):
        # Code
        self.assertEqual(app.get_fallback_category("script.py"), "Code")
        self.assertEqual(app.get_fallback_category("index.html"), "Code")
        self.assertEqual(app.get_fallback_category("styles.css"), "Code")
        self.assertEqual(app.get_fallback_category("data.json"), "Code")
        # Spreadsheets
        self.assertEqual(app.get_fallback_category("finance.xlsx"), "Spreadsheets")
        self.assertEqual(app.get_fallback_category("metrics.csv"), "Spreadsheets")
        # Images
        self.assertEqual(app.get_fallback_category("logo.png"), "Images")
        self.assertEqual(app.get_fallback_category("photo.jpg"), "Images")
        self.assertEqual(app.get_fallback_category("graphic.svg"), "Images")
        # Documents
        self.assertEqual(app.get_fallback_category("resume.pdf"), "Documents")
        self.assertEqual(app.get_fallback_category("agreement.docx"), "Documents")
        # Videos
        self.assertEqual(app.get_fallback_category("screencast.mp4"), "Videos")
        self.assertEqual(app.get_fallback_category("clip.mkv"), "Videos")
        # Archives
        self.assertEqual(app.get_fallback_category("backup.zip"), "Archives")
        self.assertEqual(app.get_fallback_category("bundle.tar.gz"), "Archives")
        # Other
        self.assertEqual(app.get_fallback_category("unknown.bin"), "Other")
        self.assertEqual(app.get_fallback_category("app.exe"), "Other")

    def test_scan_directory_immediate_files_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in base folder
            file1 = os.path.join(tmpdir, "file1.txt")
            file2 = os.path.join(tmpdir, "file2.py")
            with open(file1, "w") as f:
                f.write("test1")
            with open(file2, "w") as f:
                f.write("test2")

            # Create a subfolder with a file inside it
            subdir = os.path.join(tmpdir, "subfolder")
            os.makedirs(subdir)
            file_in_sub = os.path.join(subdir, "ignored.txt")
            with open(file_in_sub, "w") as f:
                f.write("sub")

            scanned = app.scan_directory(tmpdir)
            scanned_names = [item["name"] for item in scanned]

            self.assertIn("file1.txt", scanned_names)
            self.assertIn("file2.py", scanned_names)
            # Must NOT include files in subfolders
            self.assertNotIn("ignored.txt", scanned_names)
            self.assertNotIn("subfolder", scanned_names)

    def test_safe_path_resolution_and_traversal_prevention(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Normal resolution
            target = app.resolve_safe_target_path(tmpdir, "Code", "app.py")
            expected = os.path.abspath(os.path.join(tmpdir, "Code", "app.py"))
            self.assertEqual(target, expected)

            # Prevent traversal via category or filename
            target_traversal = app.resolve_safe_target_path(tmpdir, "../Sneaky", "test.txt")
            # Invalid category falls back to "Other" safely
            self.assertTrue(target_traversal.startswith(os.path.abspath(tmpdir)))

    def test_no_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            code_dir = os.path.join(tmpdir, "Code")
            os.makedirs(code_dir, exist_ok=True)
            existing = os.path.join(code_dir, "script.py")
            with open(existing, "w") as f:
                f.write("# original")

            # New target path must not be the existing file
            target1 = app.resolve_safe_target_path(tmpdir, "Code", "script.py")
            self.assertEqual(target1, os.path.join(code_dir, "script (1).py"))

            # Create script (1).py and verify script (2).py is generated
            with open(target1, "w") as f:
                f.write("# first copy")
            target2 = app.resolve_safe_target_path(tmpdir, "Code", "script.py")
            self.assertEqual(target2, os.path.join(code_dir, "script (2).py"))

    def test_demo_files_structure(self):
        self.assertGreater(len(app.DEMO_FILES), 10)
        for demo in app.DEMO_FILES:
            self.assertIn("name", demo)
            self.assertIn("size_kb", demo)
            cat = app.get_fallback_category(demo["name"])
            self.assertIn(cat, app.SUPPORTED_CATEGORIES)

    def test_physical_move_and_undo_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create sample files
            test_file = os.path.join(tmpdir, "notes_math.pdf")
            with open(test_file, "w") as f:
                f.write("content")

            # Resolve category and destination
            cat = app.get_fallback_category("notes_math.pdf")
            self.assertEqual(cat, "Study Notes")

            dest_folder = os.path.join(tmpdir, cat)
            os.makedirs(dest_folder, exist_ok=True)
            dest_file = app.resolve_safe_target_path(tmpdir, cat, "notes_math.pdf")

            # Move file
            shutil.move(test_file, dest_file)
            self.assertFalse(os.path.exists(test_file))
            self.assertTrue(os.path.exists(dest_file))

            # Undo move
            shutil.move(dest_file, test_file)
            self.assertTrue(os.path.exists(test_file))
            self.assertFalse(os.path.exists(dest_file))



if __name__ == "__main__":
    unittest.main()
