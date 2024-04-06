## `PyPDFCompare` Command-Line Options

Use `pdf_compare` followed by the options and file paths to compare two PDF files.

pdf_compare [options] FilePath1 FilePath2


### Options

- `-ps:pagesize`, `--page_size:pagesize`  
  Sets the page size for the comparison file.  
  **Default:** `AUTO`  
  **Options:** `AUTO`, `LETTER`, `ANSI_A`, `ANSI_B`, `ANSI_C`, `ANSI_D`  
  Example: `-ps:AUTO`

- `-dpi:level`  
  Sets the DPI (dots per inch) or quality level for the comparison file.  
  **Default:** `600`  
  Example: `-dpi:600`

- `-o:path`, `--output:path`  
  Sets the output path for the comparison file.  
  **Default:** None (Source Path)  
  Example: `-o:"~\\Desktop\\My Path"`

- `-s:bool`, `--scale:bool`  
  Scales the files to the same size before comparison.  
  **Default:** `True`  
  Example: `-s:True`

- `-bw:bool`, `--black_white:bool`  
  Sets the comparison file to be black and white to lower the file size.  
  **Default:** `False`  
  Example: `-bw:False`

- `-gs:bool`, `--grayscale:bool`  
  Sets the comparison file to be grayscale (includes shades between black and white) to lower the file size.  
  **Default:** `False`  
  Example: `-gs:False`

- `-r:bool`, `--reduce_filesize:bool`  
  Reduces the file size but also reduces overall quality.  
  **Default:** `True`  
  Example: `-r:True`

- `-mp:page`, `--main_page:page`  
  Sets the main focus page to either the newer or older document.  
  **Default:** `NEW`  
  **Options:** `NEW`, `OLD`  
  Example: `-mp:NEW`
