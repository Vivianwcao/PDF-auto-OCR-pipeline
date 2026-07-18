""" extract header and line-items data using extract_lines, extract_words, extract_table methods of pdfPlumber
"""
import pdfplumber

def overwrite_pdfplumber_table_settings(**overrides):
    """Overwrite PdfPlumber settings
    """
    defaults = {
        # Settings for "tables" Strategy:
        "vertical_strategy": "lines", # lines or text
        "horizontal_strategy": "lines", # lines or text
        "intersection_tolerance": 5, # How close lines (visual divider) must be to form corners/intersections
        "intersection_x_tolerance": 5,
        "intersection_y_tolerance": 5, 
        "snap_tolerance": 3, # Combine nearby parallel lines into one
        "join_tolerance": 3, # Connect broken line segments
        "join_x_tolerance": 3,
        "join_y_tolerance": 3,
        "edge_min_length": 3, # Ignore lines shorter than this

        # Settings for "text" Strategy:
        "text_x_tolerance": 3, # How close X-positions must be to be same column
        "text_y_tolerance": 3, # How close Y-positions must be to be same row
        "min_words_vertical": 3, # Minimum words needed to recognize a column
        "min_words_horizontal": 1, # Minimum words needed to recognize a row

    }
    defaults.update(overrides)
    return defaults

def overwrite_pdfplumber_lines_settings(**overrides):
    """Overwrite PdfPlumber settings
    """
    defaults = {
        # text-lines extraction
        "layout": False,
        "strip": True,
        "return_chars": False,
    }
    defaults.update(overrides)
    return defaults

def overwrite_pdfplumber_words_settings(**overrides):
    """Overwrite PdfPlumber settings
    """
    defaults = {
        # Words extraction
        "x_tolerance": 3,
        "y_tolerance": 3,
        "keep_blank_chars": False,
        "use_text_flow": True,
        "horizontal_ltr": True,
        "vertical_ttb": True,
        "extra_attrs": [],
        "split_at_punctuation": False,
    }
    defaults.update(overrides)
    return defaults


def clean_text(text):
    """
    Clean extracted text from PDF.
    - Normalize unicode characters to ASCII equivalents
    - Remove zero-width spaces
    - Keep newlines (\n) intact for parsing
    """
    import unicodedata
    
    if not text:
        return text
    
    # Replace common unicode characters with ASCII equivalents
    replacements = {
        '\u2013': '-',  # en dash (–)
        '\u2014': '-',  # em dash (—)
        '\u2018': "'",  # left single quote (')
        '\u2019': "'",  # right single quote (')
        '\u201c': '"',  # left double quote (")
        '\u201d': '"',  # right double quote (")
        '\u00a0': ' ',  # non-breaking space
        '\u200b': '',   # zero-width space
        '\u00ad': '',   # soft hyphen
        '\u2022': '*',  # bullet point (•)
        '\u2026': '...', # ellipsis (…)
    }
    
    for unicode_char, replacement in replacements.items():
        text = text.replace(unicode_char, replacement)
    
    # Normalize unicode (NFKD = compatibility decomposition)
    text = unicodedata.normalize('NFKD', text)
    
    # Encode to ASCII, ignore errors (removes any remaining non-ASCII)
    text = text.encode('ascii', 'ignore').decode('ascii')
    
    return text


def pdf_extract_text(pdf_file) -> str:
    """Extract text from all pages of a PDF, with first page first. Cleans unicode."""
    with pdfplumber.open(pdf_file) as pdf:
        texts = [pdf.pages[0].extract_text() or ""]  # first page
        texts.append("--PAGE_1_END--")  # page 1 divider
        for page in pdf.pages[1:]:  # rest of the pages
            texts.append(page.extract_text() or "")
        
        # Join all text and clean unicode at the source
        full_text = "\n".join(texts)
        return clean_text(full_text)

def pdf_extract_tables(pdf_file, merged_table_settings):
    """Extract tables from a PDF. Optionally use table settings. Cleans unicode in cells."""
    all_tables = []

    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # extract_tables() accepts a dictionary for settings directly 
            tables = page.extract_tables(merged_table_settings)
            for table in tables:
                # Remove empty rows and clean unicode in each cell
                cleaned_table = []
                for row in table:
                    if any(row):  # Skip empty rows
                        # Clean each cell in the row
                        cleaned_row = [clean_text(cell) if cell else cell for cell in row]
                        cleaned_table.append(cleaned_row)
                
                all_tables.append(cleaned_table)
    
    return all_tables
    
def pdf_extract_lines(pdf_file, merged_lines_settings) -> list:
    """
    Extract text lines from all pages of a PDF.
    Returns list of line dicts with text and position info.
    
    Each line dict contains:
    {
        "text": "Invoice 12345",
        "x0": 100.0,          # Left edge
        "top": 200.0,         # Top edge
        "x1": 250.0,          # Right edge
        "bottom": 215.0,      # Bottom edge
        "height": 15.0,       # Line height
        "width": 150.0,       # Line width
        "top": 200.0,         # --> Add page number manually
        "page": 1             # --> Add page number manually
    }
    """
    
    with pdfplumber.open(pdf_file) as pdf:
        all_lines = []
        for page in pdf.pages:
            # extract_lines() accepts key words arguments for settings, unpack **kwargs
            page_lines = page.extract_text_lines(**merged_lines_settings) # returns a list of objects
            # Add page number to each word object manually
            for line in page_lines:
                line["page"] = page.page_number # pdfplumber.Page already has a page number: 1 based
                chars = line.get("chars")
                if not chars: # chars dosn't exists or chars is empty [] or other false values
                    line["doctop"] = None # for instance if merged_lines_settings has "return_chars": False
                else:
                    line["doctop"] = chars[0]["doctop"] # All chars of one line have consistent doctop
                all_lines.append(line)  # append each line object
        return all_lines

def pdf_extract_words(pdf_file, merged_words_settings) -> list:
    """
    Extract words from all pages of a PDF with position info.
    
    Each word dict contains:
    {
        "text": "Invoice",
        "x0": 100.0,          # Left edge
        "top": 200.0,         # Top edge
        "doctop": 200.0,      # **Important
        "x1": 150.0,          # Right edge
        "bottom": 215.0,      # Bottom edge
        "height": 15.0,       # Word height
        "width": 50.0,        # Word width
        "page": 1             # Page number (added by me below)
    }
    """
    with pdfplumber.open(pdf_file) as pdf:
        all_words = []
        
        for page in pdf.pages:
            # Extract words - only use relevant parameters for extract_words()
            # extract_words() accepts key words arguments for settings, unpack **kwargs
            page_words = page.extract_words(**merged_words_settings)  # returns a list of objects
            
            # Add page number and clean text
            for word in page_words:
                text = word.get("text")
                if not text:
                    continue
                word["text"] = clean_text(text)
                word["page"] = page.page_number # pdfplumber.Page already has a page number: 1 based
                all_words.append(word)  
        return all_words