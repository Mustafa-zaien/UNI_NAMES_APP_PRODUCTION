# -*- coding: utf-8 -*-
from PyQt6 import QtWidgets, QtGui, QtCore
import sys, os
from pathlib import Path
import logging

class _StyleLoader:
    def __init__(self):
        self.scale_factor = self._calculate_scale_factor()
        self.tokens = self._generate_tokens()
    
    def _calculate_scale_factor(self) -> float:
        app = QtWidgets.QApplication.instance()
        screen = app.primaryScreen() if app else None
        if not screen: return 1.0
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
    qss_path = qss_path or Path(__file__).parent/'src'/'uni_names'/'style.qss'
    if not Path(qss_path).exists():
        print(f"⚠️ QSS file not found: {qss_path}")
        return
    
    style_loader = _StyleLoader()
    qss = style_loader.load_and_process_qss(str(qss_path))
    if qss:
        app.setStyleSheet(qss)
        print(f"🎨 Applied responsive stylesheet with scale: {style_loader.scale_factor:.2f}")
    else:
        print("❌ Failed to apply stylesheet")

# Setup paths
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
doctor_cleaner_dir = current_dir / 'doctor_cleaner'

# Add paths to Python path  
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(doctor_cleaner_dir))

# Import with error handling
try:
    from uni_names.clean_names_app_qt import UniNameWidget
    print("✅ UniNameWidget imported successfully")
except ImportError as e:
    print(f"⚠️ Failed to import UniNameWidget: {e}")
    UniNameWidget = None

class MainAppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        
        # ✅ Get scale factor for responsive sizing
        self.scale_factor = _StyleLoader().scale_factor
        
        self.setWindowTitle("Uni Names - Medical Data Processing Suite")
        self._create_app_icon()
        self._setup_ui()
        self._setup_content()
        
        # ✅ Responsive window size
        window_width = int(1400 * self.scale_factor)
        window_height = int(900 * self.scale_factor)
        self.resize(window_width, window_height)
        
        print(f"🖼️ Main window created with size: {window_width}x{window_height}")

    def _create_app_icon(self):
        """Create responsive app icon"""
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

    def _setup_ui(self):
        """Setup main UI layout"""
        central = QtWidgets.QWidget(self)
        self.setCentralWidget(central)
        
        layout = QtWidgets.QHBoxLayout(central)
        margin = max(4, int(8 * self.scale_factor))
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(margin)
        
        # ✅ Responsive sidebar
        self.sidebar = QtWidgets.QListWidget()
        self.sidebar.setObjectName("Sidebar")
        sidebar_width = int(240 * self.scale_factor)
        self.sidebar.setFixedWidth(sidebar_width)
        
        # Add sidebar items
        modules = [
            "🩺 Doctor Names Cleaner", 
            "📊 Reports Generator", 
            "📈 Analytics Dashboard", 
            "⚙️ System Settings", 
            "📋 Debug Console"
        ]
        
        for title in modules:
            item = QtWidgets.QListWidgetItem(title)
            self.sidebar.addItem(item)
        
        self.sidebar.setCurrentRow(0)
        layout.addWidget(self.sidebar)
        
        # Content area
        self.stack = QtWidgets.QStackedWidget()
        self.stack.setObjectName("ContentArea")
        layout.addWidget(self.stack, 1)

    def _setup_content(self):
        """Setup stack content"""
        # Add UniName widget if available
        if UniNameWidget:
            try:
                uni_widget = UniNameWidget()
                self.stack.addWidget(uni_widget)
                print("✅ UniNameWidget added to stack")
            except Exception as e:
                print(f"❌ Failed to create UniNameWidget: {e}")
                self._add_error_widget("Doctor Names Cleaner", str(e))
        else:
            self._add_error_widget("Doctor Names Cleaner", "UniNameWidget not available")
        
        # Add placeholder widgets
        placeholders = [
            ("📊 Reports Generator", "Generate comprehensive medical reports and analytics"),
            ("📈 Analytics Dashboard", "Visualize data trends and performance metrics"), 
            ("⚙️ System Settings", "Configure application preferences and system settings"),
            ("📋 Debug Console", "View system logs and debugging information")
        ]
        
        for title, description in placeholders:
            self._add_placeholder_widget(title, description)
        
        # Connect navigation
        self.sidebar.currentRowChanged.connect(self._on_page_changed)

    def _add_placeholder_widget(self, title: str, description: str):
        """Add placeholder widget"""
        widget = QtWidgets.QWidget()
        widget.setObjectName("PlaceholderWidget")
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        spacing = max(12, int(20 * self.scale_factor))
        layout.setSpacing(spacing)
        
        # Title
        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("PlaceholderTitle")
        title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QtWidgets.QLabel(description)
        desc_label.setObjectName("PlaceholderDescription")
        desc_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Coming soon button
        btn = QtWidgets.QPushButton("Coming Soon")
        btn.setObjectName("ComingSoonBtn")
        btn.setEnabled(False)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        
        self.stack.addWidget(widget)

    def _add_error_widget(self, module_name: str, error_msg: str):
        """Add error widget"""
        widget = QtWidgets.QWidget()
        widget.setObjectName("ErrorWidget")
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        
        # Error message
        error_label = QtWidgets.QLabel(f"❌ Failed to load {module_name}")
        error_label.setObjectName("ErrorTitle")
        error_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(error_label)
        
        # Error details
        details_label = QtWidgets.QLabel(error_msg)
        details_label.setObjectName("ErrorDetails")
        details_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        details_label.setWordWrap(True)
        layout.addWidget(details_label)
        
        self.stack.addWidget(widget)

    def _on_page_changed(self, index: int):
        """Handle page change"""
        self.stack.setCurrentIndex(index)
        
        page_names = [
            "Doctor Names Cleaner",
            "Reports Generator", 
            "Analytics Dashboard",
            "System Settings",
            "Debug Console"
        ]
        
        if 0 <= index < len(page_names):
            self.setWindowTitle(f"Uni Names - {page_names[index]}")

def main():
    """Application entry point"""
    app = QtWidgets.QApplication(sys.argv)
    
    # Application properties
    app.setApplicationName("Uni Names Medical Suite")
    app.setApplicationVersion("2.0.0")
    app.setOrganizationName("Uni Names Team")
    
    # Apply responsive stylesheet
    apply_responsive_stylesheet(app)
    
    # Create and show window
    window = MainAppWindow()
    window.show()
    
    print("🚀 Application started successfully")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
