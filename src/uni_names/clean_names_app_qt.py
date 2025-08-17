import sys
import os
from pathlib import Path
import re
from PyQt6 import QtCore, QtGui, QtWidgets
import pandas as pd

def std_icon(pixmap: QtWidgets.QStyle.StandardPixmap) -> QtGui.QIcon:
    app = QtWidgets.QApplication.instance()
    if app is None:
        return QtGui.QIcon()
    style = QtWidgets.QApplication.style()
    return style.standardIcon(pixmap) if style is not None else QtGui.QIcon()

class ProcessRunner(QtCore.QObject):
    started = QtCore.pyqtSignal()
    finished = QtCore.pyqtSignal(int)
    stdout = QtCore.pyqtSignal(str)
    stderr = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = QtCore.QProcess(self)
        self.process.setProcessChannelMode(QtCore.QProcess.ProcessChannelMode.SeparateChannels)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.started.connect(self.started)
        self.process.finished.connect(self.finished)

    def _read_stdout(self):
        ba = self.process.readAllStandardOutput()
        if not ba.isEmpty():
            try:
                text = bytes(ba.data()).decode('utf-8', errors='replace')
            except Exception:
                text = str(bytes(ba.data()))
            self.stdout.emit(text)

    def _read_stderr(self):
        ba = self.process.readAllStandardError()
        if not ba.isEmpty():
            try:
                text = bytes(ba.data()).decode('utf-8', errors='replace')
            except Exception:
                text = str(bytes(ba.data()))
            self.stderr.emit(text)

    def run(self, args: list[str], working_dir: str | None = None, env=None):
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            return
        program = args[0]
        arguments = args[1:]
        if working_dir:
            self.process.setWorkingDirectory(working_dir)
        
        if env:
            env_vars = QtCore.QProcessEnvironment()
            for key, value in env.items():
                env_vars.insert(key, value)
            self.process.setProcessEnvironment(env_vars)
            
        self.process.start(program, arguments)

    def stop(self):
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()

class UniNameWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Uni Name - Enhanced Medical Processing")
        
        # ✅ Settings without dark mode flag
        self.settings = QtCore.QSettings()
        
        # ✅ Main layout responsive
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # ✅ Scroll area للـ responsive behavior
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Main content widget
        content_widget = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(content_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # === Header (TopBar) === 
        self._create_header(root)
        
        # === Stats chips row ===
        self._create_stats_section(root)

        # === Form section ===
        self._create_form_section(root)

        # === Action buttons ===
        self._create_action_buttons(root)

        # === Progress section ===
        self._create_progress_section(root)

        # === Log section ===
        self._create_log_section(root)

        # Set content widget to scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

        # === Initialize runners ===
        self._init_runners()

    def _create_header(self, root):
        """إنشاء الـ header"""
        self.header = QtWidgets.QFrame()
        self.header.setObjectName("TopBar")
        
        h = QtWidgets.QHBoxLayout(self.header)
        h.setContentsMargins(24, 20, 24, 20)
        h.setSpacing(20)

        # Title section
        title_section = QtWidgets.QVBoxLayout()
        title_section.setSpacing(6)
        
        # ✅ فقط setObjectName - لا setStyleSheet
        self.title = QtWidgets.QLabel("Doctors Name Processing")
        self.title.setObjectName("HeaderTitle")
        
        self.subtitle = QtWidgets.QLabel("Smart cleaning, clustering and golden-reference learning")
        self.subtitle.setObjectName("HeaderSubtitle")
        
        title_section.addWidget(self.title)
        title_section.addWidget(self.subtitle)
        h.addLayout(title_section, 1)

        # Avatar
        self.avatar = QtWidgets.QToolButton()
        self.avatar.setObjectName("Avatar")
        self.avatar.setText("UNI")
        h.addWidget(self.avatar)

        root.addWidget(self.header)

    def _create_stats_section(self, root):
        """إنشاء قسم الإحصائيات"""
        stats_frame = QtWidgets.QFrame()
        stats_frame.setObjectName("GlassyBar")
        
        stats_layout = QtWidgets.QGridLayout(stats_frame)
        stats_layout.setContentsMargins(20, 16, 20, 16)
        stats_layout.setSpacing(16)

        def make_chip(caption: str, col: int) -> QtWidgets.QFrame:
            chip = QtWidgets.QFrame()
            chip.setObjectName("GlassChip")
            
            lay = QtWidgets.QVBoxLayout(chip)
            lay.setContentsMargins(18, 14, 18, 14)
            lay.setSpacing(8)
            
            # ✅ فقط setObjectName - لا setStyleSheet
            cap = QtWidgets.QLabel(caption)
            cap.setObjectName("ChipCaption")
            cap.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            val = QtWidgets.QLabel("0")
            val.setObjectName("ChipValue")
            val.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            
            chip._value_label = val
            lay.addWidget(cap)
            lay.addWidget(val)
            
            # Add to grid layout
            stats_layout.addWidget(chip, 0, col)
            return chip

        self._chip_total = make_chip("Total Processed", 0)
        self._chip_new = make_chip("New Aliases", 1)
        self._chip_unsure = make_chip("Unsure", 2)
        self._chip_changed = make_chip("Name Changed", 3)

        # ✅ Drop shadow محسن
        for chip in [self._chip_total, self._chip_new, self._chip_unsure, self._chip_changed]:
            effect = QtWidgets.QGraphicsDropShadowEffect()
            effect.setBlurRadius(25)
            effect.setColor(QtGui.QColor(0, 0, 0, 140))
            effect.setOffset(0, 6)
            chip.setGraphicsEffect(effect)

        root.addWidget(stats_frame)

    def _create_form_section(self, root):
        """إنشاء قسم النموذج"""
        form_frame = QtWidgets.QFrame()
        form_frame.setObjectName("Panel")
        
        form_layout = QtWidgets.QVBoxLayout(form_frame)
        form_layout.setContentsMargins(24, 24, 24, 24)
        form_layout.setSpacing(18)
        
        # Base directories
        self.base_dir = Path(__file__).resolve().parent
        self.project_root = Path(__file__).resolve().parent.parent.parent

        # Form fields data
        fields = [
            ("Input Excel (BI List):", "input_edit", "Select BI list Excel file (must contain 'BI Name')", "Browse", self.browse_input),
            ("Output Excel:", "output_edit", "Choose where to save processed output (.xlsx)", "Browse", self.browse_output),
            ("Golden Reference:", "golden_edit", "Golden reference (xlsx/csv) with BI Name + Standard_Name", "Browse", self.browse_golden),
            ("New Aliases Output:", "new_aliases_edit", "Where to export new, unseen aliases for review", "Browse", self.browse_new_aliases),
            ("Reviewed Output (to learn):", "reviewed_edit", "Choose reviewed file (Doctors sheet)", "Browse", self.browse_reviewed)
        ]

        # Create form fields
        for label_text, attr_name, placeholder, btn_text, btn_callback in fields:
            row_widget = self._create_form_row(label_text, placeholder, btn_text, btn_callback)
            setattr(self, attr_name, row_widget.findChild(QtWidgets.QLineEdit))
            form_layout.addWidget(row_widget)

        # Set default values
        self.golden_edit.setText(str(self.project_root / "reference" / "golden_doctors.xlsx"))
        self.new_aliases_edit.setText(str(self.base_dir / "Doctor_List_Final_Names.xlsx"))

        # Threshold section
        threshold_widget = QtWidgets.QWidget()
        threshold_layout = QtWidgets.QHBoxLayout(threshold_widget)
        threshold_layout.setContentsMargins(0, 0, 0, 0)
        threshold_layout.setSpacing(16)

        threshold_label = QtWidgets.QLabel("Unsure threshold (0-1):")
        threshold_layout.addWidget(threshold_label)

        self.threshold_spin = QtWidgets.QDoubleSpinBox()
        self.threshold_spin.setRange(0.0, 1.0)
        self.threshold_spin.setSingleStep(0.01)
        self.threshold_spin.setValue(0.70)
        threshold_layout.addWidget(self.threshold_spin)
        threshold_layout.addStretch(1)

        form_layout.addWidget(threshold_widget)
        root.addWidget(form_frame)

    def _create_form_row(self, label_text: str, placeholder: str, btn_text: str, btn_callback) -> QtWidgets.QWidget:
        """إنشاء صف في النموذج"""
        row_widget = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(16)

        # Label
        label = QtWidgets.QLabel(label_text)
        row_layout.addWidget(label)

        # LineEdit
        line_edit = QtWidgets.QLineEdit()
        line_edit.setPlaceholderText(placeholder)
        row_layout.addWidget(line_edit, 1)

        # Button
        btn = QtWidgets.QToolButton()
        btn.setText(btn_text)
        btn.clicked.connect(btn_callback)
        row_layout.addWidget(btn)

        return row_widget

    def _create_action_buttons(self, root):
        """إنشاء أزرار العمل"""
        actions_frame = QtWidgets.QFrame()
        actions_layout = QtWidgets.QHBoxLayout(actions_frame)
        actions_layout.setContentsMargins(24, 20, 24, 20)
        actions_layout.setSpacing(16)

        self.run_btn = QtWidgets.QPushButton("🚀 Run Processing")
        self.run_btn.clicked.connect(self.run_processing)
        actions_layout.addWidget(self.run_btn)

        self.update_btn = QtWidgets.QPushButton("📚 Update Golden")
        self.update_btn.setObjectName("Pill")
        self.update_btn.clicked.connect(self.run_update_golden)
        actions_layout.addWidget(self.update_btn)

        self.stop_btn = QtWidgets.QPushButton("🛑 Stop")
        self.stop_btn.setObjectName("StopBtn")
        self.stop_btn.clicked.connect(self.stop_running)
        self.stop_btn.setEnabled(False)
        actions_layout.addWidget(self.stop_btn)

        actions_layout.addStretch(1)
        root.addWidget(actions_frame)

    def _create_progress_section(self, root):
        """إنشاء قسم التقدم"""
        progress_frame = QtWidgets.QFrame()
        progress_frame.setObjectName("Panel")
        
        progress_layout = QtWidgets.QVBoxLayout(progress_frame)
        progress_layout.setContentsMargins(24, 20, 24, 20)
        progress_layout.setSpacing(16)

        # Processing progress
        proc_widget = QtWidgets.QWidget()
        proc_layout = QtWidgets.QHBoxLayout(proc_widget)
        proc_layout.setContentsMargins(0, 0, 0, 0)
        proc_layout.setSpacing(16)

        proc_label = QtWidgets.QLabel("Processing:")
        proc_layout.addWidget(proc_label)

        self.progress_processing = QtWidgets.QProgressBar()
        self.progress_processing.setRange(0, 1)
        self.progress_processing.setValue(0)
        proc_layout.addWidget(self.progress_processing, 1)

        progress_layout.addWidget(proc_widget)

        # Update golden progress
        update_widget = QtWidgets.QWidget()
        update_layout = QtWidgets.QHBoxLayout(update_widget)
        update_layout.setContentsMargins(0, 0, 0, 0)
        update_layout.setSpacing(16)

        update_label = QtWidgets.QLabel("Update Golden:")
        update_layout.addWidget(update_label)

        self.progress_update = QtWidgets.QProgressBar()
        self.progress_update.setRange(0, 1)
        self.progress_update.setValue(0)
        update_layout.addWidget(self.progress_update, 1)

        progress_layout.addWidget(update_widget)
        root.addWidget(progress_frame)

    def _create_log_section(self, root):
        """إنشاء قسم السجل"""
        log_frame = QtWidgets.QFrame()
        log_frame.setObjectName("Panel")
        
        log_layout = QtWidgets.QVBoxLayout(log_frame)
        log_layout.setContentsMargins(20, 20, 20, 20)
        log_layout.setSpacing(16)

        # Log header
        log_header = QtWidgets.QHBoxLayout()
        
        # ✅ فقط setObjectName - لا setStyleSheet
        log_title = QtWidgets.QLabel("Processing Log")
        log_title.setObjectName("PanelTitle")
        log_header.addWidget(log_title)
        log_header.addStretch(1)

        clear_btn = QtWidgets.QPushButton("🗑️ Clear")
        clear_btn.setObjectName("GhostBtn")
        clear_btn.clicked.connect(self.clear_log)
        log_header.addWidget(clear_btn)

        log_layout.addLayout(log_header)

        # Log area
        self.log = QtWidgets.QTextEdit()
        self.log.setReadOnly(True)
        
        # ✅ Font setup without hardcoded sizes
        font = QtGui.QFont("JetBrains Mono")
        if not font.exactMatch():
            font = QtGui.QFont("Consolas")
        if not font.exactMatch():
            font = QtGui.QFont("Courier New")
        self.log.setFont(font)
        
        log_layout.addWidget(self.log, 1)
        root.addWidget(log_frame)

    def _init_runners(self):
        """تهيئة عمليات التشغيل"""
        self.proc_runner = ProcessRunner(self)
        self.proc_runner.started.connect(lambda: self._set_busy(self.progress_processing, True))
        self.proc_runner.started.connect(lambda: self._set_running(True, which="proc"))
        self.proc_runner.finished.connect(lambda code: self._on_finished(self.progress_processing, code, "Process Doctors"))
        self.proc_runner.stdout.connect(self.append_stdout)
        self.proc_runner.stderr.connect(self.append_stderr)

        self.gold_runner = ProcessRunner(self)
        self.gold_runner.started.connect(lambda: self._set_busy(self.progress_update, True))
        self.gold_runner.started.connect(lambda: self._set_running(True, which="gold"))
        self.gold_runner.finished.connect(lambda code: self._on_finished(self.progress_update, code, "Update Golden Reference"))
        self.gold_runner.stdout.connect(self.append_stdout)
        self.gold_runner.stderr.connect(self.append_stderr)

    # ===== File picker methods =====
    def browse_input(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose input Excel", str(Path.home()), 
            "Excel files (*.xlsx *.xls);;All files (*.*)"
        )
        if fn:
            self.input_edit.setText(fn)

    def browse_output(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Choose output path", str(Path.home()), 
            "Excel (*.xlsx)"
        )
        if fn:
            if not fn.lower().endswith('.xlsx'):
                fn += '.xlsx'
            self.output_edit.setText(fn)

    def browse_golden(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose golden reference", str(Path.home()), 
            "Excel/CSV (*.xlsx *.xls *.csv);;All files (*.*)"
        )
        if fn:
            self.golden_edit.setText(fn)

    def browse_new_aliases(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Where to save new aliases", str(Path.home()), 
            "Excel (*.xlsx)"
        )
        if fn:
            if not fn.lower().endswith('.xlsx'):
                fn += '.xlsx'
            self.new_aliases_edit.setText(fn)

    def browse_reviewed(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Choose reviewed file", str(Path.home()), 
            "Excel/CSV (*.xlsx *.xls *.csv);;All files (*.*)"
        )
        if fn:
            self.reviewed_edit.setText(fn)

    # ===== Log methods =====
    def clear_log(self):
        self.log.clear()

    def append_stdout(self, text: str):
        self._append_log(text)

    def append_stderr(self, text: str):
        self._append_log(text, error=True)

    def _append_log(self, text: str, error: bool = False):
        if not text:
            return
        
        color = QtGui.QColor('#fca5a5' if error else '#e2e8f0')
        self.log.setTextColor(color)
        self.log.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.log.insertPlainText(text)
        self.log.moveCursor(QtGui.QTextCursor.MoveOperation.End)

    # ===== Processing methods =====
    def _set_busy(self, bar: QtWidgets.QProgressBar, busy: bool):
        bar.setRange(0, 0 if busy else 1)
        if not busy:
            bar.setValue(0)

    def _on_finished(self, bar: QtWidgets.QProgressBar, code: int, label: str):
        self._set_busy(bar, False)
        self._set_running(False)
        if code == 0:
            self.append_stdout(f"✅ {label} completed successfully.\n")
            try:
                self._update_glass_stats()
            except Exception as e:
                self.append_stderr(f"⚠️ [Stats] Failed to update: {e}\n")
        else:
            self.append_stderr(f"❌ {label} failed (exit code {code}).\n")

    def _set_running(self, running: bool, which: str | None = None):
        self.run_btn.setEnabled(not running)
        self.update_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self._running_which = which if running else None

    def run_processing(self):
        in_path = self.input_edit.text().strip()
        out_path = self.output_edit.text().strip()
        golden_path = self.golden_edit.text().strip()
        new_aliases = self.new_aliases_edit.text().strip()
        thr = self.threshold_spin.value()

        if not in_path:
            QtWidgets.QMessageBox.critical(self, "Missing Input", "Please choose an input Excel file.")
            return
        if not out_path:
            QtWidgets.QMessageBox.critical(self, "Missing Output", "Please choose an output Excel path.")
            return

        cli_script = self.project_root / "doctor_cleaner" / "cli.py"
        
        self.append_stdout("=" * 50 + "\n")
        self.append_stdout("🔧 DEBUG INFO:\n")
        self.append_stdout(f"   • CLI script: {cli_script}\n")
        self.append_stdout(f"   • CLI exists: {cli_script.exists()}\n")
        self.append_stdout("=" * 50 + "\n\n")
        
        if not cli_script.exists():
            self.append_stderr(f"❌ CLI script not found at: {cli_script}\n")
            QtWidgets.QMessageBox.critical(self, "File Error", f"CLI script not found: {cli_script}")
            return

        exe = sys.executable
        args = [exe, str(cli_script), "process",
                "--input", in_path,
                "--output", out_path,
                "--threshold", str(thr)]
        if golden_path:
            args += ["--golden", golden_path]
        if new_aliases:
            args += ["--new-aliases-out", new_aliases]

        self.append_stdout(f"🚀 COMMAND: {' '.join(args[:5])}...\n\n")
        self.append_stdout("🟢 Starting processing...\n")
        self.append_stdout("=" * 50 + "\n")
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)
        self.proc_runner.run(args, working_dir=str(self.project_root), env=env)

    def run_update_golden(self):
        golden_path = self.golden_edit.text().strip()
        reviewed_path = self.reviewed_edit.text().strip()
        
        if not reviewed_path:
            QtWidgets.QMessageBox.critical(self, "Missing File", "Please choose a reviewed output file.")
            return
        
        if not golden_path:
            golden_path = str(self.project_root / "reference" / "golden_doctors.xlsx")
            self.golden_edit.setText(golden_path)

        cli_script = self.project_root / "doctor_cleaner" / "cli.py"
        exe = sys.executable
        args = [exe, str(cli_script), "learn",
                "--golden", golden_path,
                "--reviewed", reviewed_path]
                
        self.append_stdout("🚀 UPDATE GOLDEN COMMAND\n")
        self.append_stdout("🟢 Starting golden update...\n")
        self.append_stdout("=" * 50 + "\n")
        
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)
        self.gold_runner.run(args, working_dir=str(self.project_root), env=env)

    def stop_running(self):
        if getattr(self, "_running_which", None) == "proc":
            self.proc_runner.stop()
            self.append_stdout("🛑 Processing stopped.\n")
        elif getattr(self, "_running_which", None) == "gold":
            self.gold_runner.stop()
            self.append_stdout("🛑 Golden update stopped.\n")

    def _update_glass_stats(self):
        """تحديث الإحصائيات"""
        out_path = self.output_edit.text().strip()
        new_aliases_path = self.new_aliases_edit.text().strip()

        total = unsure = changed = new_aliases = 0

        # Read output file
        try:
            if out_path and Path(out_path).exists():
                df = pd.read_excel(out_path, sheet_name=0)
                total = len(df)
                
                # Count unsure
                for col in ["Not_Sure", "Unsure", "Manual_Review"]:
                    if col in df.columns:
                        unsure = int((df[col].astype(str) == "Not Sure").sum())
                        break
                
                # Count changed
                for col in ["Name_Changed", "Changed", "Renamed"]:
                    if col in df.columns:
                        if df[col].dtype == bool:
                            changed = int(df[col].sum())
                        else:
                            changed = int(pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int).sum())
                        break

        except Exception as e:
            self.append_stderr(f"⚠️ Error reading output: {e}\n")

        # Read new aliases
        if new_aliases_path and Path(new_aliases_path).exists():
            try:
                df2 = pd.read_excel(new_aliases_path)
                new_aliases = len(df2)
            except Exception:
                pass

        # Update chips
        self._chip_total._value_label.setText(str(total))
        self._chip_new._value_label.setText(str(new_aliases))
        self._chip_unsure._value_label.setText(str(unsure))
        self._chip_changed._value_label.setText(str(changed))

        self.append_stdout(f"📊 Stats: Total={total}, New={new_aliases}, Unsure={unsure}, Changed={changed}\n")
