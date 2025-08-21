import sys
import os
from pathlib import Path
import pandas as pd
from fuzzywuzzy import fuzz, process
from PyQt6 import QtCore, QtGui, QtWidgets

class ReferenceSearchWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Reference Search - Golden Lookup")
        
        # Settings
        self.settings = QtCore.QSettings()
        
        # Data variables
        self.golden_df = None
        self.default_golden_path = Path(__file__).resolve().parent.parent.parent / "reference" / "golden_doctors.xlsx"
        
        # Setup UI
        self._setup_ui()
        
        # Load default golden reference
        self._load_default_golden()
    
    def _setup_ui(self):
        """Setup main UI layout"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        # Scroll area for responsiveness
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Main content widget
        content_widget = QtWidgets.QWidget()
        root = QtWidgets.QVBoxLayout(content_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        # Header
        self._create_header(root)
        
        # File selection
        self._create_file_section(root)
        
        # Search section
        self._create_search_section(root)
        
        # Results section
        self._create_results_section(root)

        # Set content to scroll area
        scroll.setWidget(content_widget)
        main_layout.addWidget(scroll)

    def _create_header(self, root):
        """Create header section"""
        header_frame = QtWidgets.QFrame()
        header_frame.setObjectName("TopBar")
        
        header_layout = QtWidgets.QVBoxLayout(header_frame)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(8)

        # Title
        title_label = QtWidgets.QLabel("Golden Reference Search")
        title_label.setObjectName("HeaderTitle")
        header_layout.addWidget(title_label)

        # Subtitle
        subtitle_label = QtWidgets.QLabel("Search and explore doctor names in golden reference database")
        subtitle_label.setObjectName("HeaderSubtitle")
        header_layout.addWidget(subtitle_label)

        root.addWidget(header_frame)

    def _create_file_section(self, root):
        """Create file selection section"""
        file_frame = QtWidgets.QFrame()
        file_frame.setObjectName("Panel")
        
        file_layout = QtWidgets.QVBoxLayout(file_frame)
        file_layout.setContentsMargins(24, 20, 24, 20)
        file_layout.setSpacing(16)

        # Section title
        file_title = QtWidgets.QLabel("Golden Reference File")
        file_title.setObjectName("PanelTitle")
        file_layout.addWidget(file_title)

        # File selection row
        file_row = QtWidgets.QHBoxLayout()
        file_row.setSpacing(12)

        # Current file label
        self.current_file_label = QtWidgets.QLabel("No file loaded")
        self.current_file_label.setObjectName("ChipCaption")
        file_row.addWidget(self.current_file_label, 1)

        # Browse button
        browse_btn = QtWidgets.QPushButton("📁 Browse")
        browse_btn.setObjectName("GhostBtn")
        browse_btn.clicked.connect(self._browse_golden_file)
        file_row.addWidget(browse_btn)

        # Load default button
        default_btn = QtWidgets.QPushButton("🔄 Load Default")
        default_btn.setObjectName("GhostBtn")
        default_btn.clicked.connect(self._load_default_golden)
        file_row.addWidget(default_btn)

        file_layout.addLayout(file_row)

        # File info
        self.file_info_label = QtWidgets.QLabel("")
        self.file_info_label.setObjectName("ChipCaption")
        file_layout.addWidget(self.file_info_label)

        root.addWidget(file_frame)

    def _create_search_section(self, root):
        """Create search section"""
        search_frame = QtWidgets.QFrame()
        search_frame.setObjectName("Panel")
        
        search_layout = QtWidgets.QVBoxLayout(search_frame)
        search_layout.setContentsMargins(24, 20, 24, 20)
        search_layout.setSpacing(16)

        # Section title
        search_title = QtWidgets.QLabel("Search Configuration")
        search_title.setObjectName("PanelTitle")
        search_layout.addWidget(search_title)

        # Search input
        search_input_layout = QtWidgets.QHBoxLayout()
        search_input_layout.setSpacing(12)

        search_label = QtWidgets.QLabel("Search Query:")
        search_input_layout.addWidget(search_label)

        self.search_input = QtWidgets.QLineEdit()
        self.search_input.setPlaceholderText("Enter doctor name to search...")
        self.search_input.textChanged.connect(self._on_search_text_changed)
        self.search_input.returnPressed.connect(self._perform_search)
        search_input_layout.addWidget(self.search_input, 1)

        search_btn = QtWidgets.QPushButton("🔍 Search")
        search_btn.clicked.connect(self._perform_search)
        search_input_layout.addWidget(search_btn)

        search_layout.addLayout(search_input_layout)

        # Search options
        options_layout = QtWidgets.QHBoxLayout()
        options_layout.setSpacing(16)

        # Similarity threshold
        threshold_label = QtWidgets.QLabel("Similarity Threshold:")
        options_layout.addWidget(threshold_label)

        self.similarity_threshold = QtWidgets.QDoubleSpinBox()
        self.similarity_threshold.setRange(0.0, 100.0)
        self.similarity_threshold.setValue(70.0)
        self.similarity_threshold.setSuffix("%")
        self.similarity_threshold.setSingleStep(5.0)
        options_layout.addWidget(self.similarity_threshold)

        # Max results
        max_results_label = QtWidgets.QLabel("Max Results:")
        options_layout.addWidget(max_results_label)

        self.max_results_spin = QtWidgets.QSpinBox()
        self.max_results_spin.setRange(1, 50)
        self.max_results_spin.setValue(10)
        options_layout.addWidget(self.max_results_spin)

        options_layout.addStretch(1)
        search_layout.addLayout(options_layout)

        root.addWidget(search_frame)

    def _create_results_section(self, root):
        """Create results section"""
        results_frame = QtWidgets.QFrame()
        results_frame.setObjectName("Panel")
        
        results_layout = QtWidgets.QVBoxLayout(results_frame)
        results_layout.setContentsMargins(24, 20, 24, 20)
        results_layout.setSpacing(16)

        # Section title with stats
        results_header = QtWidgets.QHBoxLayout()
        
        results_title = QtWidgets.QLabel("Search Results")
        results_title.setObjectName("PanelTitle")
        results_header.addWidget(results_title)

        results_header.addStretch(1)

        self.results_count_label = QtWidgets.QLabel("0 results")
        self.results_count_label.setObjectName("ChipCaption")
        results_header.addWidget(self.results_count_label)

        # Export button
        export_btn = QtWidgets.QPushButton("📊 Export Results")
        export_btn.setObjectName("GhostBtn")
        export_btn.clicked.connect(self._export_results)
        export_btn.setEnabled(False)
        self.export_btn = export_btn
        results_header.addWidget(export_btn)

        results_layout.addLayout(results_header)

        # Results table - تحديد الحجم الثابت
        self.results_table = QtWidgets.QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.results_table.setSortingEnabled(True)
        
        # ✅ تحديد الارتفاع ليأخذ نصف الصفحة تقريباً
        self.results_table.setMinimumHeight(400)
        self.results_table.setMaximumHeight(500)
        
        # Set columns
        columns = ["Similarity %", "BI Name (Original)", "Standard Name", "Original Spec"]
        self.results_table.setColumnCount(len(columns))
        self.results_table.setHorizontalHeaderLabels(columns)
        
        # Configure table
        header = self.results_table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.results_table.setColumnWidth(0, 120)

        # ✅ إضافة النسبة المحددة للجدول
        results_layout.addWidget(self.results_table, 3)  # يأخذ 3 أجزاء من المساحة

        root.addWidget(results_frame)

    def _browse_golden_file(self):
        """Browse for golden reference file"""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select Golden Reference File",
            str(Path.home()),
            "Excel/CSV Files (*.xlsx *.xls *.csv);;All Files (*.*)"
        )
        
        if file_path:
            self._load_golden_file(Path(file_path))

    def _load_default_golden(self):
        """Load default golden reference file"""
        if self.default_golden_path.exists():
            self._load_golden_file(self.default_golden_path)
        else:
            QtWidgets.QMessageBox.warning(
                self,
                "Default File Not Found",
                f"Default golden reference file not found at:\n{self.default_golden_path}\n\nPlease browse for a file."
            )

    def _load_golden_file(self, file_path: Path):
        """Load golden reference file"""
        try:
            # Load based on extension
            if file_path.suffix.lower() == '.csv':
                df = pd.read_csv(file_path)
            else:
                df = pd.read_excel(file_path)

            # Validate required columns
            required_columns = ['BI Name', 'Standard_Name']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Invalid File Format",
                    f"Missing required columns: {', '.join(missing_columns)}\n\nRequired columns: BI Name, Standard_Name"
                )
                return

            # Store data
            self.golden_df = df
            
            # Update UI
            self.current_file_label.setText(f"Loaded: {file_path.name}")
            
            # Show file info
            total_records = len(df)
            unique_standards = df['Standard_Name'].nunique()
            info_text = f"📊 {total_records:,} records • {unique_standards:,} unique standards"
            self.file_info_label.setText(info_text)
            
            # Clear previous results
            self.results_table.setRowCount(0)
            self.results_count_label.setText("0 results")
            self.export_btn.setEnabled(False)
            
            self._show_message("✅ File loaded successfully!", "success")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error Loading File",
                f"Failed to load file:\n{str(e)}"
            )

    def _on_search_text_changed(self, text):
        """Handle search text changes for real-time search"""
        if len(text) >= 2:  # ✅ تقليل الحد الأدنى إلى حرفين
            QtCore.QTimer.singleShot(200, self._perform_search)  # ✅ تقليل التأخير

    def _perform_search(self):
        """Perform fuzzy search in golden reference - Enhanced Partial Matching"""
        if self.golden_df is None:
            QtWidgets.QMessageBox.warning(
                self,
                "No Data",
                "Please load a golden reference file first."
            )
            return

        query = self.search_input.text().strip()
        if not query:
            self.results_table.setRowCount(0)
            self.results_count_label.setText("0 results")
            self.export_btn.setEnabled(False)
            return

        try:
            # Get search parameters
            threshold = self.similarity_threshold.value()
            max_results = self.max_results_spin.value()

            bi_names = self.golden_df['BI Name'].astype(str).tolist()
            
            # ✅ بحث محسن للمطابقة الجزئية
            all_matches = []
            
            # 1. البحث الدقيق (exact substring match)
            for idx, name in enumerate(bi_names):
                if query.lower() in name.lower():
                    score = 100.0  # أعلى درجة للمطابقة الدقيقة
                    all_matches.append((name, score, idx))
            
            # 2. البحث بـ fuzzy matching للكلمات المفردة
            fuzzy_matches = []
            for idx, name in enumerate(bi_names):
                # تقسيم الاسم إلى كلمات
                name_words = name.lower().split()
                query_words = query.lower().split()
                
                max_word_score = 0
                for query_word in query_words:
                    for name_word in name_words:
                        # مطابقة جزئية للكلمات
                        if query_word in name_word:
                            word_score = 95.0
                        else:
                            # استخدام fuzzy matching للكلمات
                            word_score = fuzz.ratio(query_word, name_word)
                        
                        max_word_score = max(max_word_score, word_score)
                
                if max_word_score >= threshold:
                    fuzzy_matches.append((name, max_word_score, idx))
            
            # 3. البحث بـ fuzzy matching العام
            general_matches = process.extract(query, bi_names, limit=max_results*2, scorer=fuzz.partial_ratio)
            general_fuzzy = []
            name_to_index = {name: idx for idx, name in enumerate(bi_names)}
            
            for match, score in general_matches:
                if score >= threshold:
                    idx = name_to_index.get(match, 0)
                    general_fuzzy.append((match, score, idx))
            
            # ✅ دمج النتائج وإزالة التكرارات
            seen_names = set()
            combined_matches = []
            
            # إضافة المطابقات الدقيقة أولاً
            for name, score, idx in all_matches:
                if name not in seen_names:
                    combined_matches.append((name, score, idx))
                    seen_names.add(name)
            
            # إضافة المطابقات الضبابية للكلمات
            for name, score, idx in fuzzy_matches:
                if name not in seen_names:
                    combined_matches.append((name, score, idx))
                    seen_names.add(name)
            
            # إضافة المطابقات العامة
            for name, score, idx in general_fuzzy:
                if name not in seen_names:
                    combined_matches.append((name, score, idx))
                    seen_names.add(name)
            
            # ترتيب حسب النتيجة وأخذ العدد المطلوب
            combined_matches.sort(key=lambda x: x[1], reverse=True)
            filtered_matches = combined_matches[:max_results]

            # Clear table
            self.results_table.setRowCount(0)

            if not filtered_matches:
                self.results_count_label.setText("0 results")
                self.export_btn.setEnabled(False)
                return

            # Populate results
            self.results_table.setRowCount(len(filtered_matches))

            for row, (match, score, original_idx) in enumerate(filtered_matches):
                # Get corresponding row from dataframe
                df_row = self.golden_df.iloc[original_idx]

                # Similarity percentage
                similarity_item = QtWidgets.QTableWidgetItem(f"{score:.1f}%")
                similarity_item.setData(QtCore.Qt.ItemDataRole.UserRole, score)
                self.results_table.setItem(row, 0, similarity_item)

                # BI Name (Original) - تمييز النص المطابق
                bi_name = str(df_row['BI Name'])
                # ✅ تمييز الجزء المطابق بالخط العريض
                if query.lower() in bi_name.lower():
                    # يمكن إضافة تمييز لاحقاً
                    pass
                
                bi_name_item = QtWidgets.QTableWidgetItem(bi_name)
                self.results_table.setItem(row, 1, bi_name_item)

                # Standard Name
                standard_name_item = QtWidgets.QTableWidgetItem(str(df_row['Standard_Name']))
                self.results_table.setItem(row, 2, standard_name_item)

                # Original Spec (if exists)
                Original_Specialty = ""
                if 'Original_Specialty' in df_row:
                    Original_Specialty = str(df_row['Original_Specialty'])
                elif 'Spec' in df_row:
                    Original_Specialty = str(df_row['Spec'])

                spec_item = QtWidgets.QTableWidgetItem(Original_Specialty)
                self.results_table.setItem(row, 3, spec_item)

            # Update results count
            self.results_count_label.setText(f"{len(filtered_matches)} results")
            self.export_btn.setEnabled(True)

            # الجدول مرتب بالفعل حسب النتيجة

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Search Error",
                f"Error during search:\n{str(e)}"
            )

    def _export_results(self):
        """Export search results to Excel"""
        if self.results_table.rowCount() == 0:
            return

        # Get save location
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Export Search Results",
            str(Path.home() / "search_results.xlsx"),
            "Excel Files (*.xlsx);;CSV Files (*.csv)"
        )

        if not file_path:
            return

        try:
            # Collect data from table
            results_data = []
            for row in range(self.results_table.rowCount()):
                row_data = {}
                row_data['Similarity_Percentage'] = self.results_table.item(row, 0).text()
                row_data['BI_Name_Original'] = self.results_table.item(row, 1).text()
                row_data['Standard_Name'] = self.results_table.item(row, 2).text()
                row_data['Original_Specialty'] = self.results_table.item(row, 3).text()
                row_data['Search_Query'] = self.search_input.text()
                results_data.append(row_data)

            # Create DataFrame and save
            results_df = pd.DataFrame(results_data)
            
            if file_path.lower().endswith('.csv'):
                results_df.to_csv(file_path, index=False)
            else:
                results_df.to_excel(file_path, index=False, sheet_name='Search_Results')

            self._show_message(f"✅ Results exported to {Path(file_path).name}", "success")

        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Export Error",
                f"Failed to export results:\n{str(e)}"
            )

    def _show_message(self, message: str, msg_type: str = "info"):
        """Show status message"""
        # يمكن إضافة status bar أو toast notification هنا
        print(f"[{msg_type.upper()}] {message}")
