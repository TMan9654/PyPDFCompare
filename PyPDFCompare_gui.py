import fitz
from os import path
from time import sleep
from json import load, dump
from tempfile import TemporaryDirectory
from numpy import array, where, all, int32
from PIL import Image, ImageChops, ImageDraw, ImageOps
from cv2 import findContours, threshold, approxPolyDP, arcLength, contourArea, boundingRect, THRESH_BINARY, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE

from PySide6.QtCore import QThread, Signal, Slot, Qt
from PySide6.QtWidgets import QMainWindow, QProgressBar, QApplication, QWidget, QVBoxLayout, QTextBrowser, QDialog, QFrame, QPushButton, QLabel, \
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
        self.main_page_combobox.addItems(["New Document", "Old Document"])
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
        
class ProgressWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyPDFCompare")
        self.resize(600, 500)
        
        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout()
        
        self.progressBar = QProgressBar()
        self.logArea = QTextBrowser()
        self.logArea.setReadOnly(True)
        
        self.layout.addWidget(self.progressBar)
        self.layout.addWidget(self.logArea)
        
        self.centralWidget.setLayout(self.layout)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QTextBrowser {
                background-color: #323232;
                color: #c8c8c8;
                border: 1px solid #ff5e0e;
                border-radius: 5px;
            }
            QProgressBar {
                border: 1px solid #ff5e0e;
                border-radius: 5px;
                text-align: center;
                color: #c8c8c8;
                background-color: #202020;
            }
            QProgressBar::chunk {
                background-color: #0075d5;
                width: 1px;
                border: 1px solid transparent;
                border-radius: 5px;
            }
        """)
        
    @Slot(int)
    def update_progress(self, progress):
        self.progressBar.setValue(progress)
        
    @Slot(str)
    def update_log(self, message):
        self.logArea.append(message)
    
    @Slot(int)
    def operation_complete(self, time):
        sleep(time)
        self.close()

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
            progress_window = ProgressWindow()
            progress_window.show()
            compare_thread = CompareThread(self.files, progress_window, self)
            compare_thread.start()

class CompareThread(QThread):
    progressUpdated = Signal(int)
    compareComplete = Signal(int)
    logMessage = Signal(str)
    
    def __init__(self, files: list[str], progress_window: ProgressWindow, parent=None):
        super(CompareThread, self).__init__(parent)
        compare_settings = load_settings()
        self.DPI_LEVEL = compare_settings.get("DPI_LEVEL")
        self.PAGE_SIZE = tuple(compare_settings.get("PAGE_SIZES").get(compare_settings.get("PAGE_SIZE")))
        self.INCLUDE_IMAGES = compare_settings.get("INCLUDE_IMAGES")
        self.MAIN_PAGE= compare_settings.get("MAIN_PAGE")
        self.THRESHOLD = compare_settings.get("THRESHOLD")
        self.MERGE_THRESHOLD = int(self.DPI_LEVEL / 100 * self.PAGE_SIZE[0] * self.PAGE_SIZE[1]) if self.PAGE_SIZE[0] and self.PAGE_SIZE[1] else None
        self.MIN_AREA = compare_settings.get("MIN_AREA")
        self.EPSILON = compare_settings.get("EPSILON")
        self.OUTPUT_PATH = compare_settings.get("OUTPUT_PATH")
        self.SCALE_OUTPUT = compare_settings.get("SCALE_OUTPUT")
        self.OUTPUT_BW = compare_settings.get("OUTPUT_BW")
        self.OUTPUT_GS = compare_settings.get("OUTPUT_GS")
        self.REDUCE_FILESIZE = compare_settings.get("REDUCE_FILESIZE")
        self.files = files
        self.progress_window = progress_window
        
        self.progressUpdated.connect(self.progress_window.update_progress)
        self.logMessage.connect(self.progress_window.update_log)
        self.compareComplete.connect(self.progress_window.operation_complete)
    
    def run(self):
        try:
            self.handle_files(self.files)
        except fitz.fitz.FileDataError as e:
            self.logMessage.emit(f"Error opening file: {e}")

    def mark_differences(self, image1: Image.Image, image2: Image.Image) -> list[Image.Image]:
        # Overlay Image
        if self.INCLUDE_IMAGES["Overlay"] is True:
            if image1.size != image2.size:
                image2.size = image2.resize(image1.size)
                self.logMessage.emit("Comparison", "Page sizes don't match and the 'Scale Pages' setting is off, attempting to match page sizes... results may be inaccurate.")
            image1array = array(image1)
            image2array = array(image2)
            image2array[~all(image2array == [255, 255, 255], axis=-1)] = [255, 0, 0] # Convert non-white pixels in image2array to red for overlay.
            overlay_image = Image.fromarray(where(all(image1array == [255, 255, 255], axis=-1, keepdims=True), image2array, image1array))
            del image1array, image2array
            
        # Markup Image / Differences Image
        if self.INCLUDE_IMAGES["Markup"] is True or self.INCLUDE_IMAGES["Difference"] is True:
            diff_image = Image.fromarray(where(all(array(ImageOps.colorize(ImageOps.invert(ImageChops.subtract(image2, image1).convert("L")), black="blue", white="white").convert("RGB")) == [255, 255, 255], axis=-1)[:,:,None], array(ImageOps.colorize(ImageOps.invert(ImageChops.subtract(image1, image2).convert("L")), black="red", white="white").convert("RGB")), array(ImageOps.colorize(ImageOps.invert(ImageChops.subtract(image2, image1).convert("L")), black="blue", white="white").convert("RGB"))))
            if self.INCLUDE_IMAGES["Markup"] is True:
                contours, _ = findContours(threshold(array(ImageChops.difference(image2, image1).convert("L")), self.THRESHOLD, 255, THRESH_BINARY)[1], RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
                del _
                marked_image = Image.new("RGBA", image1.size, (255, 0, 0, 255))
                marked_image.paste(image1, (0, 0))
                marked_image_draw = ImageDraw.Draw(marked_image)
                existing_boxes = []

                for contour in contours:
                    approx = approxPolyDP(contour, (self.EPSILON + 0.0000000001) * arcLength(contour, False), False)
                    marked_image_draw.line(tuple(map(tuple, array(approx).reshape((-1, 2)).astype(int32))), fill=(255, 0, 0, 255), width=int(self.DPI_LEVEL/100))

                    if self.MIN_AREA < contourArea(contour):
                        x, y, w, h = boundingRect(contour)
                        new_box = (x, y, x + w, y + h)

                        # Merge with an existing box if close enough, else add as a new box
                        merged = False
                        for i, existing_box in enumerate(existing_boxes):
                            # Define a threshold for how close boxes should be to consider merging
                            if (max(new_box[0], existing_box[0]) - min(new_box[2], existing_box[2]) <= self.MERGE_THRESHOLD and max(new_box[1], existing_box[1]) - min(new_box[3], existing_box[3]) <= self.MERGE_THRESHOLD):
                                # Merge the boxes by taking the min/max of their coordinates
                                merged_box = (min(new_box[0], existing_box[0]), min(new_box[1], existing_box[1]), max(new_box[2], existing_box[2]), max(new_box[3], existing_box[3]))
                                existing_boxes[i] = merged_box  # Update the existing box with the merged one
                                merged = True
                                break
                        
                        if not merged:
                            existing_boxes.append(new_box)

                # After processing all contours, draw the boxes
                for box in existing_boxes:
                    diff_box = Image.new("RGBA", (box[2]-box[0], box[3]-box[1]), (0, 255, 0, 64))
                    ImageDraw.Draw(diff_box).rectangle([(0, 0), (box[2]-box[0] - 1, box[3]-box[1] - 1)], outline=(255, 0, 0, 255), width=int(self.DPI_LEVEL/100))
                    marked_image.paste(diff_box, (box[0], box[1]), mask=diff_box)

                del contours, marked_image_draw
        output = []
        if self.SCALE_OUTPUT is False:
            if self.INCLUDE_IMAGES["New Copy"] is True:
                output.append(image1.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))) if self.MAIN_PAGE == "New Document" else image2.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Old Copy"] is True:
                output.append(image2.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))) if self.MAIN_PAGE == "New Document" else image1.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Markup"] is True:
                output.append(marked_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Difference"] is True:
                output.append(diff_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Overlay"] is True:
                output.append(overlay_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
        else:
            if self.INCLUDE_IMAGES["New Copy"] is True:
                output.append(image1 if self.MAIN_PAGE == "New Document" else image2)
            if self.INCLUDE_IMAGES["Old Copy"] is True:
                output.append(image2 if self.MAIN_PAGE == "New Document" else image1)
            if self.INCLUDE_IMAGES["Markup"] is True:
                output.append(marked_image)
            if self.INCLUDE_IMAGES["Difference"] is True:
                output.append(diff_image)
            if self.INCLUDE_IMAGES["Overlay"] is True:
                output.append(overlay_image)
        return output
    
    def pdf_to_image(self, page_number: int, doc: fitz.Document) -> Image.Image:
        if page_number < doc.page_count:
            pix = doc.load_page(page_number).get_pixmap(dpi=self.DPI_LEVEL)
            image = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        else:
            pix = doc.load_page(0).get_pixmap(dpi=self.DPI_LEVEL)
            image = Image.new("RGB", (pix.width, pix.height), (255, 255, 255))
        del pix
        if self.SCALE_OUTPUT is True:
            image = image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL)))
        return image

    def handle_files(self, files: list[str]) -> str:
        self.logMessage.emit(f"""Processing files:
    {files[0]}
    {files[1]}""")
        toc = []
        current_progress = 0
        with fitz.open(files[0 if self.MAIN_PAGE == "New Document" else 1]) as doc1, fitz.open(files[0 if self.MAIN_PAGE == "OLD" else 1]) as doc2:
            size = doc1.load_page(0).rect
            # If page size is auto, self.PAGESIZE will be none
            if self.PAGE_SIZE[0] is None:
                # Assume 72 DPI for original document resolution
                self.PAGE_SIZE = (size.width / 72, size.height / 72)
                self.MERGE_THRESHOLD = int(self.DPI_LEVEL / 120 * self.PAGE_SIZE[0] * self.PAGE_SIZE[1])
            filename = files[0 if self.MAIN_PAGE == "New Document" else 1].split("/")[-1]
            source_path = False
            if self.OUTPUT_PATH is None:
                self.OUTPUT_PATH = files[0].replace(filename, "")
                source_path = True
            
            total_operations = max(doc1.page_count, doc2.page_count)
            self.logMessage.emit(f"Total pages {total_operations}.")
            progress_per_operation = 100.0 / total_operations

            self.logMessage.emit("Creating temporary directory...")
            with TemporaryDirectory() as temp_dir:
                self.logMessage.emit(f"Temporary directory created: {temp_dir}")
                image_files = []

                for i in range(total_operations):
                    self.logMessage.emit(f"Processing page {i+1} of {total_operations}...")
                    self.logMessage.emit(f"Converting main page...")
                    image1 = self.pdf_to_image(i, doc1)
                    self.logMessage.emit(f"Converting secondary page...")
                    image2 = self.pdf_to_image(i, doc2)
                    self.logMessage.emit(f"Marking differences...")
                    markups = self.mark_differences(image1, image2)
                    del image1, image2

                    # Save marked images and prepare TOC entries
                    self.logMessage.emit(f"Saving output files...")
                    for j, image in enumerate(markups):
                        if self.OUTPUT_GS is True:
                            image = image.convert("L")
                        if self.OUTPUT_BW is True:
                            image = image.convert("1")
                        else:
                            image = image.convert("RGB")
                        image_file = path.join(temp_dir, f"{i}_{j}.pdf")
                        image.save(image_file, resolution=self.DPI_LEVEL, author="MAXFIELD", optimize=self.REDUCE_FILESIZE)
                        del image
                        image_files.append(image_file)
                        toc.append([1, f"Page {i+1} Variation {j+1}", i * len(markups) + j])

                    current_progress += progress_per_operation
                    self.progressUpdated.emit(int(current_progress))

                # Builds final PDF from each PDF image page
                self.logMessage.emit("Compiling PDF from output folder...")
                compiled_pdf = fitz.open()
                for img_path in image_files:
                    img = fitz.open(img_path)
                    compiled_pdf.insert_pdf(img, links=False)
                    img.close()

                # Update the table of contents
                compiled_pdf.set_toc(toc)
                
                # Save Final PDF File
                self.logMessage.emit(f"Saving final PDF...")
                output_path = f"{self.OUTPUT_PATH}{filename.split('.')[0]} Comparison.pdf"
                output_iterator = 0
                
                # Checks if a version alreaday exists and increments revision if necessary
                while path.exists(output_path):
                    output_iterator += 1
                    output_path = f"{self.OUTPUT_PATH}{filename.split('.')[0]} Comparison Rev {output_iterator}.pdf"
                compiled_pdf.save(output_path)
                compiled_pdf.close()

                self.logMessage.emit(f"Comparison file created: {output_path}")
                if source_path:
                    self.OUTPUT_PATH = None

        self.compareComplete.emit(5)
        return output_path


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
            "MAIN_PAGE": "New Document"
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
