
import sys
import fitz
from os import path
from time import sleep
from tempfile import TemporaryDirectory
from numpy import array, where, all, uint8, ones, delete, argsort
from PIL import Image, ImageChops, ImageDraw, ImageOps
from cv2 import threshold, THRESH_BINARY, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE, findContours, boundingRect, dilate
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
        self.PAGE_SIZE = tuple(compare_settings.get("PAGE_SIZES").get(compare_settings.get("PAGE_SIZE")))
        self.INCLUDE_IMAGES = compare_settings.get("INCLUDE_IMAGES")
        self.MAIN_PAGE= compare_settings.get("MAIN_PAGE")
        self.THRESHOLD = compare_settings.get("THRESHOLD")
        self.MIN_AREA = compare_settings.get("MIN_AREA")
        self.EPSILON = compare_settings.get("EPSILON")
        self.OUTPUT_PATH = compare_settings.get("OUTPUT_PATH")
        self.SCALE_OUTPUT = compare_settings.get("SCALE_OUTPUT")
        self.OUTPUT_BW = compare_settings.get("OUTPUT_BW")
        self.OUTPUT_GS = compare_settings.get("OUTPUT_GS")
        self.REDUCE_FILESIZE = compare_settings.get("REDUCE_FILESIZE")
        self.files = files
        self.progress_window = progress_window
        self.statistics = {
            "NUM_PAGES": 0,
            "MAIN_PAGE": None,
            "TOTAL_DIFFERENCES": 0,
            "PAGES_WITH_DIFFERENCES": []
            }
        
        self.progressUpdated.connect(self.progress_window.update_progress)
        self.logMessage.connect(self.progress_window.update_log)
        self.compareComplete.connect(self.progress_window.operation_complete)
    
    def run(self):
        try:
            self.handle_files(self.files)
        except fitz.FileDataError as e:
            self.logMessage.emit(f"Error opening file: {e}")
            self.compareComplete.emit(5)
            
    def merge_overlapping_boxes(self, boxes: list, overlap_threshold: float = 0.5) -> list[tuple[int]]:
        if not boxes:
            return []

        # Convert to x1, y1, x2, y2 format
        boxes_np = array([[x, y, x + w, y + h] for (x, y, w, h) in boxes])

        # Apply Non-Maximum Suppression to merge overlapping boxes
        x1 = boxes_np[:, 0]
        y1 = boxes_np[:, 1]
        x2 = boxes_np[:, 2]
        y2 = boxes_np[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        indices = argsort(y2)

        pick = []
        while len(indices) > 0:
            last = len(indices) - 1
            i = indices[last]
            pick.append(i)
            suppress = [last]
            for pos in range(0, last):
                j = indices[pos]
                xx1 = max(x1[i], x1[j])
                yy1 = max(y1[i], y1[j])
                xx2 = min(x2[i], x2[j])
                yy2 = min(y2[i], y2[j])

                w = max(0, xx2 - xx1)
                h = max(0, yy2 - yy1)
                overlap = (w * h) / areas[j]

                if overlap > overlap_threshold:
                    suppress.append(pos)
            indices = delete(indices, suppress)

        merged_boxes = boxes_np[pick].tolist()
        # Convert back to x, y, w, h format
        merged_boxes = [(int(x1), int(y1), int(x2 - x1), int(y2 - y1)) for (x1, y1, x2, y2) in merged_boxes]
        return merged_boxes

    def mark_differences(self, page_num: int, image1: Image.Image, image2: Image.Image) -> list[Image.Image]:
        # Overlay Image
        if self.INCLUDE_IMAGES["Overlay"] is True:
            if image1.size != image2.size:
                image2 = image2.resize(image1.size)
                self.logMessage.emit("Comparison", "Page sizes don't match and the 'Scale Pages' setting is off, attempting to match page sizes... results may be inaccurate.")
            image1array = array(image1)
            image2array = array(image2)
            image2array[~all(image2array == [255, 255, 255], axis=-1)] = [255, 0, 0]  # Convert non-white pixels in image2array to red for overlay.
            overlay_image = Image.fromarray(where(all(image1array == [255, 255, 255], axis=-1, keepdims=True), image2array, image1array))
            del image1array, image2array

        # Markup Image / Differences Image
        if self.INCLUDE_IMAGES["Markup"] is True or self.INCLUDE_IMAGES["Difference"] is True:
            # Compute the difference image for the 'Difference' output
            diff_image = Image.fromarray(
                where(
                    all(
                        array(
                            ImageOps.colorize(
                                ImageOps.invert(ImageChops.subtract(image2, image1).convert("L")),
                                black="blue",
                                white="white"
                            ).convert("RGB")
                        ) == [255, 255, 255], axis=-1
                    )[:, :, None],
                    array(
                        ImageOps.colorize(
                            ImageOps.invert(ImageChops.subtract(image1, image2).convert("L")),
                            black="red",
                            white="white"
                        ).convert("RGB")
                    ),
                    array(
                        ImageOps.colorize(
                            ImageOps.invert(ImageChops.subtract(image2, image1).convert("L")),
                            black="blue",
                            white="white"
                        ).convert("RGB")
                    )
                )
            )

            if self.INCLUDE_IMAGES["Markup"] is True:
                # Compute difference and threshold it to get binary image
                diff_gray = ImageChops.difference(image2, image1).convert("L")
                diff_array = array(diff_gray)
                _, thresh = threshold(diff_array, self.THRESHOLD, 255, THRESH_BINARY)
                del diff_gray

                # Apply dilation to merge nearby differences
                kernel_size = 3  # Adjust kernel size as needed
                kernel = ones((kernel_size, kernel_size), uint8)
                dilated = dilate(thresh, kernel, iterations=1)

                # Find contours on the dilated image
                contours, _ = findContours(dilated, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)
                del _, thresh, dilated

                # Filter and merge overlapping contours
                bounding_boxes = [boundingRect(c) for c in contours]
                bounding_boxes = self.merge_overlapping_boxes(bounding_boxes)

                marked_image = Image.new("RGBA", image1.size, (255, 0, 0, 255))
                marked_image.paste(image1, (0, 0))
                marked_image_draw = ImageDraw.Draw(marked_image)

                previous_differences = self.statistics["TOTAL_DIFFERENCES"]

                # Determine outline thickness based on DPI
                outline_thickness = max(1, int(self.DPI_LEVEL / 100))

                for box in bounding_boxes:
                    x, y, w, h = box
                    area = w * h
                    if area < self.MIN_AREA:
                        continue

                    # Draw the bounding box and fill with green
                    diff_box = Image.new("RGBA", (w, h), (0, 255, 0, 64))
                    ImageDraw.Draw(diff_box).rectangle([(0, 0), (w - 1, h - 1)], outline=(255, 0, 0, 255), width=outline_thickness)
                    marked_image.paste(diff_box, (x, y), mask=diff_box)
                    del diff_box

                    self.statistics["TOTAL_DIFFERENCES"] += 1

                differences_on_page = self.statistics["TOTAL_DIFFERENCES"] - previous_differences
                if differences_on_page > 0:
                    self.statistics["PAGES_WITH_DIFFERENCES"].append((page_num, differences_on_page))
                del marked_image_draw, contours

        # Output
        output = []
        if not self.SCALE_OUTPUT:
            resize_size = (int(self.PAGE_SIZE[0] * self.DPI_LEVEL), int(self.PAGE_SIZE[1] * self.DPI_LEVEL))
            if self.INCLUDE_IMAGES["New Document"]:
                output.append(image1.resize(resize_size) if self.MAIN_PAGE == "NEW" else image2.resize(resize_size))
            if self.INCLUDE_IMAGES["Old Document"]:
                output.append(image2.resize(resize_size) if self.MAIN_PAGE == "NEW" else image1.resize(resize_size))
            if self.INCLUDE_IMAGES["Markup"]:
                output.append(marked_image.resize(resize_size))
            if self.INCLUDE_IMAGES["Difference"]:
                output.append(diff_image.resize(resize_size))
            if self.INCLUDE_IMAGES["Overlay"]:
                output.append(overlay_image.resize(resize_size))
        else:
            if self.INCLUDE_IMAGES["New Document"]:
                output.append(image1 if self.MAIN_PAGE == "NEW" else image2)
            if self.INCLUDE_IMAGES["Old Document"]:
                output.append(image2 if self.MAIN_PAGE == "NEW" else image1)
            if self.INCLUDE_IMAGES["Markup"]:
                output.append(marked_image)
            if self.INCLUDE_IMAGES["Difference"]:
                output.append(diff_image)
            if self.INCLUDE_IMAGES["Overlay"]:
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
        current_progress = 0
        with fitz.open(files[0 if self.MAIN_PAGE == "NEW" else 1]) as doc1, fitz.open(files[0 if self.MAIN_PAGE == "OLD" else 1]) as doc2:
            size = doc1.load_page(0).rect
            # If page size is auto, self.PAGESIZE will be none
            if self.PAGE_SIZE[0] is None:
                # Assume 72 DPI for original document resolution
                self.PAGE_SIZE = (size.width / 72, size.height / 72)
            self.statistics["MAIN_PAGE"] = files[0 if self.MAIN_PAGE == "NEW" else 1]
            filename = files[0 if self.MAIN_PAGE == "NEW" else 1].split("/")[-1]
            source_path = False
            if self.OUTPUT_PATH is None:
                self.OUTPUT_PATH = path.dirname(files[0])
                source_path = True
            
            total_operations = max(doc1.page_count, doc2.page_count)
            self.logMessage.emit(f"Total pages {total_operations}.")
            progress_per_operation = 100.0 / total_operations

            self.logMessage.emit("Creating temporary directory...")
            with TemporaryDirectory() as temp_dir:
                self.logMessage.emit(f"Temporary directory created: {temp_dir}")
                image_files = []
                toc = []
                output_page_number = 2  # Start from 2 because the statistics page will be the first page

                # Process each page in the documents
                for i in range(total_operations):
                    self.logMessage.emit(f"Processing page {i+1} of {total_operations}...")
                    self.logMessage.emit(f"Converting main page...")
                    image1 = self.pdf_to_image(i, doc1)
                    self.logMessage.emit(f"Converting secondary page...")
                    image2 = self.pdf_to_image(i, doc2)
                    self.logMessage.emit(f"Marking differences...")
                    markups = self.mark_differences(i, image1, image2)
                    del image1, image2

                    # Save marked images and create ToC entries
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

                        # Determine the type of the page and add it to the ToC
                        page_type = ""
                        if j == 0:
                            page_type = "New Document" if self.MAIN_PAGE == "NEW" else "Old Document"
                        elif j == 1:
                            page_type = "Old Document" if self.MAIN_PAGE == "NEW" else "New Document"
                        elif j == 2:
                            page_type = "Markup"
                        elif j == 3:
                            page_type = "Difference"
                        elif j == 4:
                            page_type = "Overlay"
                        
                        toc.append([1, f"{page_type} - Page {i + 1}", output_page_number])
                        output_page_number += 1
                    
                    current_progress += progress_per_operation
                    self.progressUpdated.emit(int(current_progress))

                # Create statistics page
                self.logMessage.emit("Creating statistics page...")
                text = f"Document Comparison Report\n\nTotal Pages: {total_operations}\nFiles Compared:\n    {files[0]}\n    {files[1]}\nMain Page: {self.statistics['MAIN_PAGE']}\nTotal Differences: {self.statistics['TOTAL_DIFFERENCES']}\nPages with differences:\n"
                for page_info in self.statistics["PAGES_WITH_DIFFERENCES"]:
                    text += f"    Page {page_info[0]+1} Changes: {page_info[1]}\n"

                # Create statistics page and handle text overflow
                stats_doc = fitz.open()
                stats_page = stats_doc.new_page()
                text_blocks = text.split('\n')
                y_position = 72
                for line in text_blocks:
                    if y_position > fitz.paper_size('letter')[1] - 72:
                        stats_page = stats_doc.new_page()  # Create a new page if needed
                        y_position = 72  # Reset y position for the new page
                    stats_page.insert_text((72, y_position), line, fontsize=11, fontname="helv")
                    y_position += 12  # Adjust y_position by the line height

                # Save and close the stats document
                stats_filename = path.join(temp_dir, "stats.pdf")
                stats_doc.save(stats_filename)
                stats_doc.close()
                image_files.insert(0, stats_filename)  # Insert statistics page at the beginning

                # Add statistics page to the ToC
                toc.insert(0, [1, "Statistics", 1])

                # Build final PDF from each PDF image page
                self.logMessage.emit("Compiling PDF from output folder...")
                compiled_pdf = fitz.open()

                for img_path in image_files:
                    img = fitz.open(img_path)
                    compiled_pdf.insert_pdf(img, links=False)
                    img.close()

                # Save Final PDF File
                self.logMessage.emit(f"Saving final PDF...")
                output_path = f"{self.OUTPUT_PATH}/{filename.split('.')[0]} Comparison.pdf"
                output_iterator = 0
                
                # Checks if a version already exists and increments revision if necessary
                while path.exists(output_path):
                    output_iterator += 1
                    output_path = f"{self.OUTPUT_PATH}/{filename.split('.')[0]} Comparison Rev {output_iterator}.pdf"
                
                # Set the Table of Contents (ToC)
                compiled_pdf.set_toc(toc)
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
                    "AUTO": (None, None),
                    "LETTER": (8.5, 11),
                    "ANSI A": (11, 8.5),
                    "ANSI B": (17, 11),
                    "ANSI C": (22, 17),
                    "ANSI D": (34, 22)
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
                "INCLUDE_IMAGES": {"New Document": False, "Old Document": False, "Markup": True, "Difference": True, "Overlay": True},
                "DPI": "Medium DPI: Printable [300]",
                "DPI_LEVEL": 300,
                "PAGE_SIZE": "ANSI B",
                "THRESHOLD": 128,
                "MIN_AREA": 20,
                "EPSILON": 0.0,
                "OUTPUT_PATH": None,
                "SCALE_OUTPUT": True,
                "OUTPUT_BW": False,
                "OUTPUT_GS": False,
                "REDUCE_FILESIZE": True,
                "MAIN_PAGE": "New Document"
        }
        if options:
            for option in options:
                option, value = option.split(":")
                if (option == "-ps" or option == "--page_size") and value in settings["PAGE_SIZES"]:  
                    settings["PAGE_SIZE"] = value

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
    print(paths[0], paths[1], len(paths) == 2)
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
