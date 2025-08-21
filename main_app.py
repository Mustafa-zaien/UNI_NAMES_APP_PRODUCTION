# -*- coding: utf-8 -*-

from PyQt6 import QtWidgets, QtGui, QtCore
import sys, os, io, builtins
from pathlib import Path
import logging

# ===== Prevent GUI when running CLI mode =====
def should_start_gui() -> bool:
    """Check if GUI should be started based on command line arguments"""
    args_str = " ".join(sys.argv).lower()
    # Don't start GUI if called for CLI operations
    cli_indicators = [
        "doctor_cleaner/cli.py",
        "doctor_cleaner\\cli.py", 
        "cli.py",
        "--input",
        "--output", 
        "process",
        "--no-gui",
        "--cli-mode"
    ]
    
    for indicator in cli_indicators:
        if indicator in args_str:
            print(f"[CLI MODE] Detected CLI operation: {indicator}")
            return False
    
    return True

# ===== Early exit for CLI mode =====
if not should_start_gui():
    print("[CLI MODE] Exiting without starting GUI")
    sys.exit(0)

# ===== Console encoding fix (avoid UnicodeEncodeError in prints) =====
def _force_utf8_streams():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass

def _strip_unsupported(text: str) -> str:
    enc = (getattr(sys.stdout, "encoding", None) or "utf-8")
    try:
        text.encode(enc)
        return text
    except Exception:
        # لو الترميز مش مدعوم (زي cp1256)، هنشيل الرموز غير المدعومة (الإيموجيز)
        return text.encode(enc, errors="ignore").decode(enc, errors="ignore")

def _safe_print(*args, **kwargs):
    try:
        builtins._orig_print(*args, **kwargs)
    except Exception:
        s = " ".join(str(a) for a in args)
        s = _strip_unsupported(s)
        builtins._orig_print(s, **{k: v for k, v in kwargs.items() if k != "file"})

# فعّل التصحيحات قبل أي print
_force_utf8_streams()
builtins._orig_print = builtins.print
builtins.print = _safe_print

# ===== Resource path for PyInstaller =====
def resource_path(rel: str) -> str:
    """Return absolute path for resources (works in dev and PyInstaller exe)"""
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel)

# ===== Import widgets =====
try:
    from src.uni_names.clean_names_app_qt import UniNameWidget
    print("✅ UniNameWidget imported successfully")
except ImportError as e:
    print(f"⚠️ Failed to import UniNameWidget: {e}")
    UniNameWidget = None

try:
    from src.uni_names.reference_search import ReferenceSearchWidget
    print("✅ ReferenceSearchWidget imported successfully")
except ImportError as e:
    print(f"⚠️ Failed to import ReferenceSearchWidget: {e}")
    ReferenceSearchWidget = None

# ===== Import auto-updater =====
try:
    from auto_updater import AutoUpdater
    print("✅ AutoUpdater imported successfully")
except ImportError as e:
    print(f"⚠️ Failed to import AutoUpdater: {e}")
    AutoUpdater = None

class _StyleLoader:
    def __init__(self):
        self.scale_factor = self._calculate_scale_factor()
        self.tokens = self._generate_tokens()

    def _calculate_scale_factor(self) -> float:
        app = QtWidgets.QApplication.instance()
        screen = app.primaryScreen() if app else None
        if not screen:
            return 1.0
        dpi = screen.logicalDotsPerInch()
        geometry = screen.geometry()
        dpi_scale = dpi / 96.0
        size_scale = ((geometry.width()/1920)+(geometry.height()/1080))/2.0
        combined = dpi_scale*0.7 + size_scale*0.3
        final_scale = max(0.8, min(2.0, combined))
        print(f"📐 Scale Factor: {final_scale:.2f} (DPI: {dpi}, Screen: {geometry.width()}x{geometry.height()})")
        return final_scale

    def _generate_tokens(self):
        s = self.scale_factor
        return {
            'FS_TINY': f"{int(10*s)}px", 'FS_SMALL': f"{int(12*s)}px", 'FS_BASE': f"{int(14*s)}px",
            'FS_MEDIUM': f"{int(16*s)}px", 'FS_LARGE': f"{int(18*s)}px", 'FS_TITLE': f"{int(24*s)}px", 'FS_HEADER': f"{int(28*s)}px",
            'SP_XS': f"{int(4*s)}px", 'SP_SM': f"{int(8*s)}px", 'SP_MD': f"{int(12*s)}px", 'SP_LG': f"{int(16*s)}px", 'SP_XL': f"{int(24*s)}px", 'SP_XXL': f"{int(32*s)}px",
            'PD_XS': f"{int(4*s)}px", 'PD_SM': f"{int(8*s)}px", 'PD_MD': f"{int(12*s)}px", 'PD_LG': f"{int(16*s)}px", 'PD_XL': f"{int(20*s)}px",
            'MG_XS': f"{int(2*s)}px", 'MG_SM': f"{int(4*s)}px", 'MG_MD': f"{int(8*s)}px", 'MG_LG': f"{int(12*s)}px", 'MG_XL': f"{int(16*s)}px",
            'BR_SM': f"{int(6*s)}px", 'BR_MD': f"{int(8*s)}px", 'BR_LG': f"{int(12*s)}px", 'BR_XL': f"{int(16*s)}px",
            'SZ_ICON_SM': f"{int(16*s)}px", 'SZ_ICON_MD': f"{int(24*s)}px", 'SZ_ICON_LG': f"{int(32*s)}px", 'SZ_ICON_XL': f"{int(48*s)}px",
            'SZ_BTN_H': f"{int(36*s)}px", 'SZ_BTN_H_LG': f"{int(44*s)}px", 'SZ_INPUT_H': f"{int(36*s)}px",
            'W_SIDEBAR': f"{int(240*s)}px", 'W_BTN_SM': f"{int(80*s)}px", 'W_BTN_MD': f"{int(120*s)}px", 'W_BTN_LG': f"{int(160*s)}px",
            'SZ_PROGRESS_H': f"{int(6*s)}px", 'SZ_SCROLL_W': f"{int(8*s)}px", 'FS_NUMBER': f"{int(20*s)}px", 'BR_PILL': f"{int(20*s)}px"
        }

    def load_and_process_qss(self, qss_path):
        try:
            with open(qss_path, encoding='utf-8') as f:
                qss = f.read()
            for token, value in self.tokens.items():
                qss = qss.replace(f"{{{{{token}}}}}", value)
            print(f"✅ QSS loaded and processed from: {qss_path}")
            return qss
        except Exception as e:
            print(f"❌ Failed to load QSS: {e}")
            return ""

def apply_responsive_stylesheet(app: QtWidgets.QApplication, qss_path=None):
    # Paths to search (supports dev and PyInstaller)
    candidates = [
        qss_path,
        Path(__file__).parent / 'style.qss',
        Path(__file__).parent / 'light_style.qss',
        Path(__file__).parent / 'src' / 'uni_names' / 'style.qss',
        Path(resource_path('assets/style.qss')),
        Path(resource_path('style.qss')),
        Path(resource_path('src/uni_names/style.qss')),
    ]
    for p in [c for c in candidates if c]:
        try:
            if Path(p).exists():
                loader = _StyleLoader()
                qss = loader.load_and_process_qss(str(p))
                if qss:
                    app.setStyleSheet(qss)
                    print(f"🎨 Applied responsive stylesheet from: {p}")
                    return
        except Exception:
            continue
    print("⚠️ No QSS file found, using default styles")

class MainAppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.scale_factor = _StyleLoader().scale_factor
        self.setWindowTitle("Uni Names - Medical Data Processing Suite")

        # Initialize auto-updater system
        if AutoUpdater:
            self.updater = AutoUpdater(self, "2.1.0")
            print("✅ Auto-updater initialized")
        else:
            self.updater = None
            print("⚠️ Auto-updater not available")

        self._create_app_icon()
        self._setup_menu_bar()
        self._setup_ui()
        self._setup_content()

        window_width = int(1400 * self.scale_factor)
        window_height = int(900 * self.scale_factor)
        self.resize(window_width, window_height)
        print(f"🖼️ Main window created with size: {window_width}x{window_height}")

    def _create_app_icon(self):
        icon_size = int(32 * self.scale_factor)
        pixmap = QtGui.QPixmap(icon_size, icon_size)
        pixmap.fill(QtGui.QColor("#7c5cff"))
        painter = QtGui.QPainter(pixmap)
        pen_width = max(1, int(2 * self.scale_factor))
        font_size = max(8, int(16 * self.scale_factor))
        painter.setPen(QtGui.QPen(QtGui.QColor("white"), pen_width))
        painter.setFont(QtGui.QFont("Segoe UI", font_size, QtGui.QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), QtCore.Qt.AlignmentFlag.AlignCenter, "U")
        painter.end()
        self.setWindowIcon(QtGui.QIcon(pixmap))

    def _setup_menu_bar(self):
        menubar = self.menuBar()
        help_menu = menubar.addMenu('Help')
        if self.updater:
            check_update_action = help_menu.addAction('Check for Updates')
            check_update_action.setShortcut(QtGui.QKeySequence('Ctrl+U'))
            check_update_action.triggered.connect(lambda: self.updater.check_for_updates(True))
            help_menu.addSeparator()
        about_action = help_menu.addAction('About')
        about_action.triggered.connect(self.show_about)

    def show_about(self):
        QtWidgets.QMessageBox.about(self, "About Application",
            "UniNames Medical Suite v2.1.0\n\n"
            "🩺 Medical Names Processing Application\n\n"
            "Features:\n"
            "• Doctor names cleaning and standardization\n"
            "• Golden reference database search\n"
            "• Comprehensive report generation\n"
            "• Analytics dashboard and statistics\n"
            "• Auto-update system\n\n"
            "© 2025 Development Team")

    def _setup_ui(self):
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        layout = QtWidgets.QHBoxLayout(central)
        margin = max(4, int(8 * self.scale_factor))
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(margin)

        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFixedWidth(int(240 * self.scale_factor))

        modules = [
            "🩺 Doctor Names Cleaner",
            "🔍 Reference Search",
            "📊 Reports Generator",
            "📈 Analytics Dashboard",
            "⚙️ System Settings",
            "📋 Debug Console"
        ]
        for title in modules:
            self.sidebar.addItem(QtWidgets.QListWidgetItem(title))
        self.sidebar.setCurrentRow(0)
        layout.addWidget(self.sidebar)

        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("ContentArea")
        layout.addWidget(self.stack, 1)

    def _setup_content(self):
        if UniNameWidget:
            try:
                self.stack.addWidget(UniNameWidget())
                print("✅ UniNameWidget added to stack")
            except Exception as e:
                print(f"❌ Failed to create UniNameWidget: {e}")
                self._add_error_widget("Doctor Names Cleaner", str(e))
        else:
            self._add_error_widget("Doctor Names Cleaner", "UniNameWidget not available")

        if ReferenceSearchWidget:
            try:
                self.stack.addWidget(ReferenceSearchWidget())
                print("✅ ReferenceSearchWidget added to stack")
            except Exception as e:
                print(f"❌ Failed to create ReferenceSearchWidget: {e}")
                self._add_error_widget("Reference Search", str(e))
        else:
            self._add_error_widget("Reference Search", "ReferenceSearchWidget not available")

        placeholders = [
            ("📊 Reports Generator", "Generate comprehensive medical reports and analytics"),
            ("📈 Analytics Dashboard", "Visualize data trends and performance metrics"),
            ("⚙️ System Settings", "Configure application preferences and system settings"),
            ("📋 Debug Console", "View system logs and debugging information")
        ]
        for title, description in placeholders:
            self._add_placeholder_widget(title, description)

        self.sidebar.currentRowChanged.connect(self._on_page_changed)

    def _add_placeholder_widget(self, title: str, description: str):
        widget = QtWidgets.QWidget()
        widget.setObjectName("PlaceholderWidget")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        spacing = max(12, int(20 * self.scale_factor))
        layout.setSpacing(spacing)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("PlaceholderTitle")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("PlaceholderDescription")
        desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        btn = QtWidgets.QPushButton("Coming Soon")
        btn.setObjectName("ComingSoonBtn")
        btn.setEnabled(False)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(widget)

    def _add_error_widget(self, module_name: str, error_msg: str):
        widget = QtWidgets.QWidget()
        widget.setObjectName("ErrorWidget")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        error_label = QtWidgets.QLabel(f"❌ Failed to load {module_name}")
        error_label.setObjectName("ErrorTitle")
        error_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_label)

        details_label = QtWidgets.QLabel(error_msg)
        details_label.setObjectName("ErrorDetails")
        details_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        details_label.setWordWrap(True)
        layout.addWidget(details_label)

        self.stack.addWidget(widget)

    def _on_page_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        page_names = [
            "Doctor Names Cleaner",
            "Reference Search", 
            "Reports Generator",
            "Analytics Dashboard",
            "System Settings",
            "Debug Console"
        ]
        if 0 <= index < len(page_names):
            self.setWindowTitle(f"Uni Names - {page_names[index]}")

    def closeEvent(self, event):
        if self.updater:
            temp_dir = Path.cwd() / "temp_updates"
            if temp_dir.exists():
                try:
                    import shutil
                    shutil.rmtree(temp_dir)
                    print("🧹 Cleaned up temporary update files")
                except Exception as e:
                    print(f"⚠️ Failed to clean temp files: {e}")
        event.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if self.updater:
            QtCore.QTimer.singleShot(3000, lambda: self.updater.check_for_updates(False))

def main():
    """Main application entry point - only for GUI mode"""
    print("[GUI MODE] Starting GUI application...")
    
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Uni Names Medical Suite")
    app.setApplicationVersion("2.1.0")
    app.setOrganizationName("Uni Names Team")
    app.setApplicationDisplayName("UniNames Medical Suite")
    app.setDesktopFileName("UniNames")

    apply_responsive_stylesheet(app)
    window = MainAppWindow()
    window.show()
    print("🚀 Application started successfully with auto-updater support")
    sys.exit(app.exec())

if __name__ == "__main__":
    # Final check before starting GUI
    if should_start_gui():
        main()
    else:
        print("[CLI MODE] Skipping GUI startup")
