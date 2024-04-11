
import sys
import fitz
from os import path
from time import sleep

from tempfile import TemporaryDirectory
from numpy import array, where, all, int32
from PIL import Image, ImageChops, ImageDraw, ImageOps
from cv2 import findContours, threshold, approxPolyDP, arcLength, contourArea, boundingRect, THRESH_BINARY, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE

from PySide6.QtCore import QThread, Signal, Slot
from PySide6.QtWidgets import QMainWindow, QProgressBar, QApplication, QWidget, QVBoxLayout, QTextBrowser

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
                border: 1px solid #7b7b7b;
            }
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                color: #c8c8c8;
                background-color: #202020;
            }
            QProgressBar::chunk {
                background-color: #0075d5;
                width: 1px;
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

class CompareThread(QThread):
    progressUpdated = Signal(int)
    compareComplete = Signal(int)
    logMessage = Signal(str)
    
    def __init__(self, files: list[str], progress_window: ProgressWindow, options: list[str] = None, parent=None):
        super(CompareThread, self).__init__(parent)
        compare_settings = self.load_settings(options)
        self.DPI_LEVEL = compare_settings.get("DPI_LEVEL")
        self.PAGE_SIZE = tuple(compare_settings.get("PAGE_SIZES").get(compare_settings.get("PAGE_NAME")))
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
                output.append(image1.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))) if self.MAIN_PAGE == "NEW" else image2.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Old Copy"] is True:
                output.append(image2.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))) if self.MAIN_PAGE == "NEW" else image1.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Markup"] is True:
                output.append(marked_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Difference"] is True:
                output.append(diff_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
            if self.INCLUDE_IMAGES["Overlay"] is True:
                output.append(overlay_image.resize((int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))))
        else:
            if self.INCLUDE_IMAGES["New Copy"] is True:
                output.append(image1 if self.MAIN_PAGE == "NEW" else image2)
            if self.INCLUDE_IMAGES["Old Copy"] is True:
                output.append(image2 if self.MAIN_PAGE == "NEW" else image1)
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
        with fitz.open(files[0 if self.MAIN_PAGE == "NEW" else 1]) as doc1, fitz.open(files[0 if self.MAIN_PAGE == "OLD" else 1]) as doc2:
            size = doc1.load_page(0).rect
            # If page size is auto, self.PAGESIZE will be none
            if self.PAGE_SIZE[0] is None:
                # Assume 72 DPI for original document resolution
                self.PAGE_SIZE = (size.width / 72, size.height / 72)
                self.MERGE_THRESHOLD = int(self.DPI_LEVEL / 120 * self.PAGE_SIZE[0] * self.PAGE_SIZE[1])
            filename = files[0 if self.MAIN_PAGE == "NEW" else 1].split("/")[-1]
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

                
    def load_settings(self, options: list[str]) -> dict:
        settings = {
            "PAGE_SIZES": {
                "AUTO": [None, None],
                "LETTER": [8.5, 11],
                "ANSI_A": [11, 8.5],
                "ANSI_B": [17, 11],
                "ANSI_C": [22, 17],
                "ANSI_D": [34, 22]
            },
            "INCLUDE_IMAGES": {"New Copy": False, "Old Copy": False, "Markup": True, "Difference": True, "Overlay": True},
            "DPI_LEVEL": 600,
            "PAGE_NAME": "AUTO",
            "THRESHOLD": 128,
            "MIN_AREA": 100,
            "EPSILON": 0.0,
            "OUTPUT_PATH": None,
            "SCALE_OUTPUT": True,
            "OUTPUT_BW": False,
            "OUTPUT_GS": False,
            "REDUCE_FILESIZE": True,
            "MAIN_PAGE": "NEW"
        }
        if options:
            for option in options:
                option, value = option.split(":")
                if (option == "-ps" or option == "--page_size") and value in settings["PAGE_SIZES"]:  
                    settings["PAGE_NAME"] = value

                elif option == "-dpi" and value.isdigit():
                    settings["DPI_LEVEL"] = int(value)

                elif (option == "-o" or option == "--output") and path.exists(value):
                    settings["OUTPUT_PATH"] = value

                elif (option == "-s" or option == "--scale") and (value == "True" or value == "False"):
                    if value == "True":
                        settings["SCALE_OUTPUT"] = True
                    else:
                        settings["SCALE_OUTPUT"] = False
                elif (option == "-bw" or option == "--black_white") and (value == "True" or value == "False"):
                    if value == "True":
                        settings["OUTPUT_BW"] = True
                    else:
                        settings["OUTPUT_BW"] = False
                elif (option == "-gs" or option == "--grayscale") and (value == "True" or value == "False"):
                    if value == "True":
                        settings["OUTPUT_GS"] = True
                    else:
                        settings["OUTPUT_GS"] = False
                elif (option == "-r" or option == "--reduce_filesize") and (value == "True" or value == "False"):
                    if value == "True":
                        settings["REDUCE_FILESIZE"] = True
                    else:
                        settings["REDUCE_FILESIZE"] = False
                elif (option == "-mp" or option == "--main_page") and (value == "NEW" or value == "OLD"):
                    if value == "NEW":
                        settings["MAIN_PAGE"] = "NEW"
                    else:
                        settings["MAIN_PAGE"] = "OLD"
        return settings


def main():
    """
    python PyPDFCompare.py [options] FilePath1 FilePath2
    options:
    -ps:pagesize, --page_size:pagesize  Ex: -ps:AUTO
        Sets the page size of the comparison file
        Default: AUTO
        Page Sizes:
            AUTO
            LETTER
            ANSI_A
            ANSI_B
            ANSI_C
            ANSI_D
    
    -dpi:level  Ex:-dpi:600
        Sets the dpi or quality level for the comparison file.
        Default: 600
    
    -o:path, --output:path  Ex: -o:"~\\Desktop\\My Path"
        Sets the output path for the comparison file.
        Default: None (Source Path)
    
    -s:bool, --scale:bool   Ex: -s:True
        Scales the files to the same size prior to comparison.
        Default: True
    
    -bw:bool, --black_white:bool    Ex: -bw:False
        Sets the comparison file to be black and white [Lower file size]
        Default: False
    
    -gs:bool, --grayscale:bool  Ex: gs:False
        Sets the colcomparison e to be grayscale (Includes values between black and white) [Lower file size]
        Default: False
    
    -r:bool, --reduce_filesize:bool Ex: -r:True
        Reduces the file size but also reduces overall quality
        Default: True
    
    -mp:page, --main_page:page  Ex: -mp:NEW
        Sets the main focus page to either FilePath1 (NEW) or FilePath2 (OLD)
        Default: NEW
        Options:
            NEW
            OLD
    """
    args = sys.argv[1:]
    paths = args[len(args)-2:]
    options = args[:len(args)-2]
    if path.exists(paths[0]) and path.exists(paths[1]) and len(paths) == 2:
        _, ext1 = path.splitext(paths[0])
        _, ext2 = path.splitext(paths[1])
        if ext1 == ".pdf" or ext2 == ".pdf":
            app = QApplication()
            progress_window = ProgressWindow()
            progress_window.show()
            compare_thread = CompareThread(paths, progress_window, options=options)
            compare_thread.start()
            app.exec()
        else:
            print("Arguments must contain pdf paths.")
            return
    else:
        print("Arguments must contain 2 pdf paths.")
        return

if __name__ == "__main__":
    main()
