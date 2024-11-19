from os import path
from json import load, dump
import subprocess, sys


from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QMainWindow, QApplication, QWidget, QVBoxLayout, QDialog, QFrame, QPushButton, QLabel, \
QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, QLineEdit, QGroupBox, QTabWidget, QStyleFactory, QFormLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QFileDialog
from PySide6.QtGui import QIcon

class AdvancedSettings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.threshold_label = QLabel("Threshold [Default: 128]:")
        self.threshold_desc = QLabel("To analyze the pdf, it must be thresholded (converted to pure black and white). The threshold setting controls the point at which pixels become white or black determined based upon grayscale color values of 0-255")
        self.threshold_desc.setWordWrap(True)
        self.threshold_desc.setStyleSheet("color: white; font: 12px Arial, sans-serif;")
        self.threshold_spinbox = QSpinBox(self)
        self.threshold_spinbox.setMinimum(0)
        self.threshold_spinbox.setMaximum(255)
        self.threshold_spinbox.setValue(self.settings["THRESHOLD"])
        self.threshold_spinbox.valueChanged.connect(self.update_threshold)
        
        self.minimum_area_label = QLabel("Minimum Area [Default: 100]:")
        self.minimum_area_desc = QLabel("When marking up the pdf, boxes are created to highlight major changes. The minimum area setting controls the minimum size the boxes can be which will ultimately control what becomes classfied as a significant change.")
        self.minimum_area_desc.setWordWrap(True)
        self.minimum_area_desc.setStyleSheet("color: white; font: 12px Arial, sans-serif;")
        self.minimum_area_spinbox = QSpinBox(self)
        self.minimum_area_spinbox.setMinimum(0)
        self.minimum_area_spinbox.setMaximum(1000)
        self.minimum_area_spinbox.setValue(self.settings["MIN_AREA"])
        self.minimum_area_spinbox.valueChanged.connect(self.update_area)
        
        self.epsilon_label = QLabel("Precision [Default: 0.00]:")
        self.epsilon_desc = QLabel("When marking up the pdf, outlines are created to show any change. The precision setting controls the maximum distance of the created contours around a change. Smaller values will have better precision and follow curves better and higher values will have more space between the contour and the change.")
        self.epsilon_desc.setWordWrap(True)
        self.epsilon_desc.setStyleSheet("color: white; font: 12px Arial, sans-serif;")
        self.epsilon_spinbox = QDoubleSpinBox(self)
        self.epsilon_spinbox.setMinimum(0.000)
        self.epsilon_spinbox.setMaximum(1.000)
        self.epsilon_spinbox.setSingleStep(0.001)
        self.epsilon_spinbox.setValue(self.settings["EPSILON"])
        self.epsilon_spinbox.valueChanged.connect(self.update_epsilon)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(self.epsilon_label)
        layout.addWidget(self.epsilon_desc)
        layout.addWidget(self.epsilon_spinbox)
        layout.addWidget(self.minimum_area_label)
        layout.addWidget(self.minimum_area_desc)
        layout.addWidget(self.minimum_area_spinbox)
        layout.addWidget(self.threshold_label)
        layout.addWidget(self.threshold_desc)
        layout.addWidget(self.threshold_spinbox)
        
        self.setLayout(layout)
        self.setStyleSheet('''
            QLabel {
                color: white;
                font: 14px Arial, sans-serif;
            }
            QSpinBox, QDoubleSpinBox {
                color: white;
                font: 14px Arial, sans-serif;
            }
        ''')

    def update_threshold(self, threshold):
        self.settings["THESHOLD"] = threshold
        save_settings(self.settings)

    def update_area(self, area):
        self.settings["MIN_AREA"] = area
        save_settings(self.settings)
        
    def update_epsilon(self, epsilon):
        self.settings["EPSILON"] = epsilon
        save_settings(self.settings)

class DPISettings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = window
        self.settings = load_settings()
        self.low_draft_label = QLabel("Low DPI - Draft Quality:")
        self.low_draft_spinbox = QSpinBox(self)
        self.low_draft_spinbox.setMinimum(1)
        self.low_draft_spinbox.setMaximum(99)
        self.low_draft_spinbox.setValue(self.settings["DPI_LEVELS"][0])
        self.low_draft_spinbox.valueChanged.connect(self.update_dpi_levels)
        
        self.low_viewing_label = QLabel("Low DPI - Viewing Only:")
        self.low_viewing_spinbox = QSpinBox(self)
        self.low_viewing_spinbox.setMinimum(100)
        self.low_viewing_spinbox.setMaximum(199)
        self.low_viewing_spinbox.setValue(self.settings["DPI_LEVELS"][1])
        self.low_viewing_spinbox.valueChanged.connect(self.update_dpi_levels)
        
        self.medium_label = QLabel("Medium DPI - Printable:")
        self.medium_spinbox = QSpinBox(self)
        self.medium_spinbox.setMinimum(200)
        self.medium_spinbox.setMaximum(599)
        self.medium_spinbox.setValue(self.settings["DPI_LEVELS"][2])
        self.medium_spinbox.valueChanged.connect(self.update_dpi_levels)
        
        self.standard_label = QLabel("Standard DPI:")
        self.standard_spinbox = QSpinBox(self)
        self.standard_spinbox.setMinimum(600)
        self.standard_spinbox.setMaximum(999)
        self.standard_spinbox.setValue(self.settings["DPI_LEVELS"][3])
        self.standard_spinbox.valueChanged.connect(self.update_dpi_levels)
        
        self.high_label = QLabel("High DPI - Professional Quality:")
        self.high_spinbox = QSpinBox(self)
        self.high_spinbox.setMinimum(1000)
        self.high_spinbox.setMaximum(1999)
        self.high_spinbox.setValue(self.settings["DPI_LEVELS"][4])
        self.high_spinbox.valueChanged.connect(self.update_dpi_levels)
        
        self.max_label = QLabel("Max DPI - Large File Size:")
        self.max_spinbox = QSpinBox(self)
        self.max_spinbox.setMinimum(1000)
        self.max_spinbox.setMaximum(6000)
        self.max_spinbox.setValue(self.settings["DPI_LEVELS"][5])
        self.max_spinbox.valueChanged.connect(self.update_dpi_levels)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        layout.addWidget(self.low_draft_label)
        layout.addWidget(self.low_draft_spinbox)
        layout.addWidget(self.low_viewing_label)
        layout.addWidget(self.low_viewing_spinbox)
        layout.addWidget(self.medium_label)
        layout.addWidget(self.medium_spinbox)
        layout.addWidget(self.standard_label)
        layout.addWidget(self.standard_spinbox)
        layout.addWidget(self.high_label)
        layout.addWidget(self.high_spinbox)
        layout.addWidget(self.max_label)
        layout.addWidget(self.max_spinbox)
        
        self.setLayout(layout)
        self.setStyleSheet('''
            QLabel {
                color: white;
                font: 14px Arial, sans-serif;
            }
            QSpinBox {
                color: white;
                font: 14px Arial, sans-serif;
            }
            QComboBox {
                height: 30px;
                border-radius: 5px;
                background-color: #454545;
                selection-background-color: #ff5e0e;
                color: white;
            }
            QComboBox QAbstractItemView {
                padding: 10px;
                background-color: #454545;
                selection-background-color: #ff5e0e;
                color: white;
            }
        ''')
        
    def update_dpi_levels(self, new_dpi):
        if new_dpi < 100:
            self.settings["DPI_LEVELS"][0] = new_dpi
            self.settings["DPI_LABELS"][0] = f"Low DPI: Draft Quality [{new_dpi}]"
        elif new_dpi < 200:
            self.settings["DPI_LEVELS"][1] = new_dpi
            self.settings["DPI_LABELS"][1] = f"Low DPI: Viewing Quality [{new_dpi}]"
        elif new_dpi < 600:
            self.settings["DPI_LEVELS"][2] = new_dpi
            self.settings["DPI_LABELS"][2] = f"Medium DPI: Printable [{new_dpi}]"
        elif new_dpi < 1000:
            self.settings["DPI_LEVELS"][3] = new_dpi
            self.settings["DPI_LABELS"][3] = f"Standard DPI [{new_dpi}]"
        elif new_dpi < 2000:
            self.settings["DPI_LEVELS"][4] = new_dpi
            self.settings["DPI_LABELS"][4] = f"High DPI: Professional Quality [{new_dpi}]"
        else:
            self.settings["DPI_LEVELS"][5] = new_dpi
            self.settings["DPI_LABELS"][5] = f"Max DPI: High Memory [{new_dpi}]"
        self.parent_window.dpi_combo.clear()
        self.parent_window.dpi_combo.addItems(self.settings["DPI_LABELS"])
        self.parent_window.dpi_combo.setCurrentText(self.settings["DPI_LABELS"][3])
        save_settings()

class OutputSettings(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = load_settings()
        self.output_path_label = QLabel("Output Path:")
        self.output_path_combobox = QComboBox(self)
        self.output_path_combobox.addItems(["Source Path", "Default Path", "Specified Path"])
        if self.settings["OUTPUT_PATH"] == "\\": 
            self.output_path_combobox.setCurrentText("Default Path")
        elif self.settings["OUTPUT_PATH"] is None:
            self.output_path_combobox.setCurrentText("Source Path")
        else:
            self.output_path_combobox.setCurrentText("Specified Path")
        self.output_path_combobox.currentTextChanged.connect(self.set_output_path)

        self.specified_label = QLabel("Specified Path:")
        self.specified_entry = QLineEdit(self)
        self.specified_entry.setText(self.settings["OUTPUT_PATH"] if self.output_path_combobox.currentText() == "Specified Path" else "")
        self.specified_entry.textChanged.connect(self.set_output_path)
        
        self.checkbox_image1 = QCheckBox("New Copy")
        if self.settings["INCLUDE_IMAGES"]["New Copy"] is True:
            self.checkbox_image1.setChecked(True)
        self.checkbox_image2 = QCheckBox("Old Copy")
        if self.settings["INCLUDE_IMAGES"]["Old Copy"] is True:
            self.checkbox_image2.setChecked(True)
        self.checkbox_image3 = QCheckBox("Markup")
        if self.settings["INCLUDE_IMAGES"]["Markup"] is True:
            self.checkbox_image3.setChecked(True)
        self.checkbox_image4 = QCheckBox("Difference")
        if self.settings["INCLUDE_IMAGES"]["Difference"] is True:
            self.checkbox_image4.setChecked(True)
        self.checkbox_image5 = QCheckBox("Overlay")
        if self.settings["INCLUDE_IMAGES"]["Overlay"] is True:
            self.checkbox_image5.setChecked(True)
        self.checkbox_image1.stateChanged.connect(self.set_output_images)
        self.checkbox_image2.stateChanged.connect(self.set_output_images)
        self.checkbox_image3.stateChanged.connect(self.set_output_images)
        self.checkbox_image4.stateChanged.connect(self.set_output_images)
        self.checkbox_image5.stateChanged.connect(self.set_output_images)

        self.scaling_checkbox = QCheckBox("Scale Pages")
        self.scaling_checkbox.setChecked(self.settings["SCALE_OUTPUT"])
        self.scaling_checkbox.stateChanged.connect(self.set_scaling)
        self.bw_checkbox = QCheckBox("Black/White")
        self.bw_checkbox.setChecked(self.settings["OUTPUT_BW"])
        self.bw_checkbox.stateChanged.connect(self.set_bw)
        self.gs_checkbox = QCheckBox("Grayscale")
        self.gs_checkbox.setChecked(self.settings["OUTPUT_GS"])
        self.gs_checkbox.stateChanged.connect(self.set_gs)
        self.reduce_checkbox = QCheckBox("Reduce Size")
        self.reduce_checkbox.setChecked(self.settings["REDUCE_FILESIZE"])
        self.reduce_checkbox.stateChanged.connect(self.set_reduced_filesize)
        
        self.main_page_label = QLabel("Main Page:")
        self.main_page_combobox = QComboBox(self)
        self.main_page_combobox.addItems(["Main File", "Secondary File"])
        self.main_page_combobox.setCurrentText(self.settings["MAIN_PAGE"])
        self.main_page_combobox.currentTextChanged.connect(self.set_main_page)
        
        output_path_group = QGroupBox("Output Settings")
        include_images_group = QGroupBox("Files to include:")
        general_group = QGroupBox("General")
        checkboxes_group = QGroupBox()
        other_group = QGroupBox()
        
        output_path_layout = QFormLayout()
        output_path_layout.addRow(self.output_path_label, self.output_path_combobox)
        output_path_layout.addRow(self.specified_label, self.specified_entry)
        output_path_group.setLayout(output_path_layout)

        include_images_layout = QHBoxLayout()
        include_images_layout.addWidget(self.checkbox_image1)
        include_images_layout.addWidget(self.checkbox_image2)
        include_images_layout.addWidget(self.checkbox_image3)
        include_images_layout.addWidget(self.checkbox_image4)
        include_images_layout.addWidget(self.checkbox_image5)
        include_images_group.setLayout(include_images_layout)
        
        general_layout = QHBoxLayout()
        checkboxes = QVBoxLayout()
        other = QVBoxLayout()
        other.setAlignment(Qt.AlignmentFlag.AlignTop)
        checkboxes.addWidget(self.scaling_checkbox)
        checkboxes.addWidget(self.bw_checkbox)
        checkboxes.addWidget(self.gs_checkbox)
        checkboxes.addWidget(self.reduce_checkbox)
        other.addWidget(self.main_page_label)
        other.addWidget(self.main_page_combobox)
        checkboxes_group.setLayout(checkboxes)
        other_group.setLayout(other)
        general_layout.addWidget(checkboxes_group)
        general_layout.addWidget(other_group)
        general_group.setLayout(general_layout)
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        main_layout.addWidget(output_path_group)
        main_layout.addWidget(include_images_group)
        main_layout.addWidget(general_group)
        
        self.setLayout(main_layout)
        self.setStyleSheet('''
            QLabel {
                color: white;
                font: 14px Arial, sans-serif;
            }
            QSpinBox {
                color: white;
                font: 14px Arial, sans-serif;
            }
            QComboBox {
                height: 30px;
                border-radius: 5px;
                background-color: #454545;
                selection-background-color: #ff5e0e;
                color: white;
            }
            QComboBox QAbstractItemView {
                padding: 10px;
                background-color: #454545;
                selection-background-color: #ff5e0e;
                color: white;
                font: 14px Arial, sans-serif;
            }
            QCheckBox {
                color: white;
                font: 14px Arial, sans-serif;
                
            }
        ''')

    def set_output_path(self, option):
        if option == "Source Path":
            self.settings["OUTPUT_PATH"] = None
        elif option == "Default Path":
            self.settings["OUTPUT_PATH"] = "\\"
        else:
            self.settings["OUTPUT_PATH"] = self.specified_entry.text()
            self.settings["OUTPUT_PATH"].replace("\\", "\\\\")
            self.settings["OUTPUT_PATH"] += "\\"
            
        save_settings(self.settings)
        
    def set_output_images(self, state):
        checkbox = self.sender()
        if state == 2:
                self.settings["INCLUDE_IMAGES"][checkbox.text()] = True
        else:
            self.settings["INCLUDE_IMAGES"][checkbox.text()] = False
        save_settings(self.settings)
                
    def set_scaling(self, state):
        if state == 2:
            self.settings["SCALE_OUTPUT"] = True
        else:
            self.settings["SCALE_OUTPUT"] = False
        save_settings(self.settings)
                    
    def set_bw(self, state):
        if state == 2:
            self.settings["OUTPUT_BW"] = True
        else:
            self.settings["OUTPUT_BW"] = False
        save_settings(self.settings)
                    
    def set_gs(self, state):
        if state == 2:
            self.settings["OUTPUT_GS"] = True
        else:
            self.settings["OUTPUT_GS"] = False
        save_settings(self.settings)
    
    def set_reduced_filesize(self, state):
        if state == 2:
            self.settings["REDUCE_FILESIZE"] = True
        else:
            self.settings["REDUCE_FILESIZE"] = False
        save_settings(self.settings)
                    
    def set_main_page(self, page):
        self.settings["MAIN_PAGE"] = page
        save_settings(self.settings)
         
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(500, 500)

        self.tab_widget = QTabWidget(self)

        output_settings = OutputSettings()
        dpi_settings = DPISettings()
        advanced_settings = AdvancedSettings()

        self.tab_widget.addTab(output_settings, "Output")
        self.tab_widget.addTab(dpi_settings, "DPI")
        self.tab_widget.addTab(advanced_settings, "Advanced")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tab_widget)
        self.setLayout(layout)
        self.setStyleSheet('''
            QDialog {
                color: black;
            }
            
            QLabel {
                color: black;
            }
            
            QSpinBox, QDoubleSpinBox {
                color: black;
            }
        ''')

class CustomTitleBar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(40)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 10, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        spacer_item = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        self.title_label = QLabel("PyPDFCompare")

        self.settings_button = QPushButton("Settings", self)
        self.settings_button.setObjectName('SettingsButton')
        self.settings_button.setFixedSize(65, 25)

        self.settings_button.clicked.connect(self.open_settings)

        self.minimize_button = QPushButton("-", self)
        self.minimize_button.setObjectName('MinimizeButton')
        self.minimize_button.setFixedSize(20, 20)
        self.minimize_button.clicked.connect(self.parent.showMinimized)

        self.close_button = QPushButton("X", self)
        self.close_button.setObjectName('CloseButton')
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.parent.close)

        self.layout.addWidget(self.settings_button)
        self.layout.addItem(spacer_item)
        self.layout.addWidget(self.title_label)
        self.layout.addItem(spacer_item)
        self.layout.addWidget(self.minimize_button)
        self.layout.addWidget(self.close_button)

        self.draggable = True
        self.dragging_threshold = 5
        self.drag_start_position = None

    def mousePressEvent(self, event):
        if self.draggable:
            if event.button() == Qt.LeftButton:
                self.drag_start_position = event.globalPosition().toPoint() - self.parent.pos()
        event.accept()

    def mouseMoveEvent(self, event):
        if self.draggable and self.drag_start_position is not None:
            if event.buttons() == Qt.LeftButton:
                if (
                    event.globalPosition().toPoint() - self.drag_start_position
                ).manhattanLength() > self.dragging_threshold:
                    self.parent.move(event.globalPosition().toPoint() - self.drag_start_position)
                    self.drag_start_position = event.globalPosition().toPoint() - self.parent.pos()
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_position = None
        event.accept()

    def open_settings(self):
        settings_dialog = SettingsDialog(self.parent)
        settings_dialog.exec()

class DragDropLabel(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._parent = parent
        self.setAcceptDrops(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.clicked.connect(self.browse_files)
        self.setSizePolicy(sizePolicy)
        self.setStyleSheet("""
        QPushButton {
                color: black;
                background-color: #f7f7f7;
                border-radius: 10px;
                border: 2px solid #ff5e0e;
            }
        """)
        self.setText("Drop files here or click to browse")
        
    def browse_files(self) -> None:
        files = list(QFileDialog.getOpenFileNames(self, "Open Files", "", "PDF Files (*.pdf)")[0])
        if files and len(files) == 2:
            self.setText(f"Main File: {files[0]}\nSecondary File: {files[1]}")
            self._parent.files = files
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        files.reverse()
        if files and len(files) == 2:
            self.setText(f"Main File: {files[0]}\nSecondary File: {files[1]}")
            self._parent.files = files
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Maxfield Auto Markup")
        self.setGeometry(100, 100, 500, 300)
        self.setWindowIcon(QIcon("app_icon.png"))
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.setObjectName("TitleBar")
        self.setMenuWidget(self.title_bar)
        
        self.settings = load_settings()
        self.files = None

        layout = QVBoxLayout()

        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.drop_label = DragDropLabel(self)
        
        self.compare_button = QPushButton("Compare", self)
        self.compare_button.clicked.connect(self.compare)

        self.dpi_label = QLabel("DPI:", self)
        self.dpi_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.dpi_combo = QComboBox(self)
        self.dpi_combo.addItems(self.settings["DPI_LABELS"])
        self.dpi_combo.setCurrentText(self.settings["DPI"])
        self.dpi_combo.currentTextChanged.connect(self.update_dpi)

        self.page_label = QLabel("Page Size:", self)
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignBottom)
        self.page_combo = QComboBox(self)
        self.page_combo.addItems(list(self.settings["PAGE_SIZES"].keys()))
        self.page_combo.setCurrentText(self.settings["PAGE_SIZE"])
        self.page_combo.currentTextChanged.connect(self.update_page_size)

        layout.addWidget(self.drop_label)
        layout.addWidget(self.compare_button)
        layout.addWidget(self.dpi_label)
        layout.addWidget(self.dpi_combo)
        layout.addWidget(self.page_label)
        layout.addWidget(self.page_combo)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.set_stylesheet()

    def set_stylesheet(self):
        self.drop_label.setStyleSheet("""
        QPushButton {
            color: white;
            background-color: #2D2D2D;
            border-radius: 10px;
            border: 2px solid #ff5e0e;
            }""")
        
        self.setStyleSheet("""
            QLabel {
                font: 14px Arial, sans-serif;
                color: white;
            }
            QMainWindow {
                background-color: #2D2D2D;
            }
            #TitleBar {
                background-color: #1f1f1f;
            }
            #SettingsButton {
                background-color: #ff5e0e;
                color: black;
            }
            #MinimizeButton {
                background-color: #2b2b2b;
            }
            #CloseButton {
                background-color: #2b2b2b;
            }
            #MinimizeButton:hover {
                background-color: blue;
            }
            #CloseButton:hover {
                background-color: red;
            }
        """)


    def update_dpi(self, dpi):
        if dpi != "":
            self.settings["DPI"] = dpi
            self.settings["DPI_LEVEL"] = self.settings["DPI_LEVELS"][self.settings["DPI_LABELS"].index(dpi)]
            save_settings(self.settings)

    def update_page_size(self, page_size):
        self.settings["PAGE"] = page_size
        self.settings["PAGE_SIZE"] = self.settings["PAGE_SIZES"][page_size]
        save_settings(self.settings)
        
    def compare(self):
        if self.files and len(self.files) == 2:
            compare_thread = CompareThread(self.files, self)
            compare_thread.start()

class CompareThread(QThread):    
    def __init__(self, files: list[str], parent=None):
        super(CompareThread, self).__init__(parent)
        self.settings = load_settings()
        self.files = files

    def run(self):
        args = self._construct_cli_arguments()

        process = subprocess.Popen(
            [sys.executable, "PyPDFCompare.py"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False
        )
        process.wait()
            
    def _construct_cli_arguments(self) -> list[str]:
        """Constructs the CLI arguments based on the current settings."""
        args = []

        # Add DPI level
        dpi_level = self.settings.get("DPI_LEVEL", 600)
        args.append(f"-dpi:{dpi_level}")

        # Add page size
        page_size = self.settings.get("PAGE_SIZE", "AUTO")
        args.append(f"-ps:{page_size}")

        # Add output path
        output_path = self.settings.get("OUTPUT_PATH", None)
        if output_path:
            args.append(f'-o:"{output_path}"')

        # Add scaling option
        scale_output = self.settings.get("SCALE_OUTPUT", True)
        args.append(f"-s:{str(scale_output).capitalize()}")

        # Add black-and-white and grayscale options
        output_bw = self.settings.get("OUTPUT_BW", False)
        output_gs = self.settings.get("OUTPUT_GS", False)
        args.append(f"-bw:{str(output_bw).capitalize()}")
        args.append(f"-gs:{str(output_gs).capitalize()}")

        # Add file size reduction
        reduce_filesize = self.settings.get("REDUCE_FILESIZE", True)
        args.append(f"-r:{str(reduce_filesize).capitalize()}")

        # Add main page focus
        main_page = self.settings.get("MAIN_PAGE", "Main File")
        main_page_arg = "NEW" if main_page == "Main File" else "OLD"
        args.append(f"-mp:{main_page_arg}")
        
        # Add input files
        if len(self.files) == 2:
            args.extend(self.files)
        else:
            raise ValueError("Exactly two input files are required.")

        return args


def save_settings(settings: dict) -> None:
    settings_path = "settings.json"

    if settings_path:
        with open(settings_path, "w") as f:
            dump(settings, f, indent=4)

def load_settings() -> dict:
    settings = None
    settings_path = "settings.json"

    if settings_path and path.exists(settings_path):
        with open(settings_path, "r") as f:
            settings = load(f)
    if not settings:
        settings = _load_default_settings()
    save_settings(settings)
    return settings

def _load_default_settings() -> dict:
    default_settings = {
            "PAGE_SIZES": {
                "AUTO": [None, None],
                "LETTER": [8.5, 11],
                "ANSI A": [11, 8.5],
                "ANSI B": [17, 11],
                "ANSI C": [22, 17],
                "ANSI D": [34, 22]
            },
            "DPI_LEVELS": [75, 150, 300, 600, 1200, 1800],
            "DPI_LABELS": [
                "Low DPI: Draft Quality [75]",
                "Low DPI: Viewing Only [150]",
                "Medium DPI: Printable [300]",
                "Standard DPI [600]",
                "High DPI [1200]: Professional Quality",
                "Max DPI [1800]: Large File Size"
            ],
            "INCLUDE_IMAGES": {"New Copy": False, "Old Copy": False, "Markup": True, "Difference": True, "Overlay": True},
            "DPI": "Standard DPI [600]",
            "DPI_LEVEL": 600,
            "PAGE_SIZE": "AUTO",
            "THRESHOLD": 128,
            "MIN_AREA": 100,
            "EPSILON": 0.0,
            "OUTPUT_PATH": None,
            "SCALE_OUTPUT": True,
            "OUTPUT_BW": False,
            "OUTPUT_GS": False,
            "REDUCE_FILESIZE": True,
            "MAIN_PAGE": "Main File"
    }
    return default_settings


stylesheet = """
#SettingsButton {
    background-color: #ff5e0e;
    color: black;
}
#MinimizeButton:hover {
    background-color: blue;
}
#CloseButton:hover {
    background-color: red;
}
#SettingsDialog {
    color: black;
}
"""

if __name__ == "__main__":
    app = QApplication([])
    app.setStyle(QStyleFactory.create("Fusion"))
    app.setStyleSheet(stylesheet)
    window = MainWindow()
    window.show()
    app.exec()
