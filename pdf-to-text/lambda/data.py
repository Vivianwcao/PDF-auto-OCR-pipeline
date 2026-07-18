"""supplier identifiers for SUPPLIERS_STRATEGY_SETTINGS, SUPPLIERS_FORMATTER and SUPPLIERS_INFO
must match.
Use unique identifiers for suppliers on the PDF, such as company names, tax numbers, etc.

"""

# supplier specific PdfPlumber strategy settings
# pdfPlumber extract_table, extract_line or extract_word requires
# its own strategy to be feed individually
# for pdf_parser.py
SUPPLIERS_STRATEGY_SETTINGS = {
    "360 Engineering": {
        "pdfplumber_table_settings": {
            # For tables
            "vertical_strategy": "lines",
            "horizontal_strategy": "text",
        }
    },
    # Mantl
    "MANTL Canada, Inc.": {
        "pdfplumber_lines_settings": {
            # For lines
            "layout": False,  # remove internal line white space
            "strip": True,  # Trims leading/trailing whitespace
            "return_chars": True,  # Get char level metadata like "doctop"
        },
        "pdfplumber_words_settings": {
            # For words
            "x_tolerance": 5,
            "y_tolerance": 3,
            "keep_blank_chars": False,
            "use_text_flow": True,
            "horizontal_ltr": True,
            "vertical_ttb": True,
            "split_at_punctuation": False,
        },
    },
    # Sundown GST/HST #
    "Sundown Oilfield Services": {
        "pdfplumber_lines_settings": {
            # For lines
            "layout": True,  # keep internal white space according to the pdf
            "strip": True,  # Trims leading/trailing whitespace
            "return_chars": False,  # Character-level metadata is explicitly disabled (doctop, upright, fontname, etc. are omitted)
        },
    },
}

# supplier specific formatting requirements
# for formatter.py
SUPPLIERS_FORMATTER = {
    "360 Engineering": {
        # Extract requirements for header fields / line-items
        "require_text": True,
        "require_text_lines": False,
        "require_words": False,
        "require_tables": True,
        # Extraction methods (pick 1 or more for header fields)
        "extract_header_using_text": True,
        "extract_header_using_tables": False,
        # Extraction methods (pick only 1 for line items)
        "extract_line_items_using_tables": True,
        # Header: text - Look in page 1 - use universal regex
        "header_fields_text_or_lines": [
            "Invoice #",
            "From",
            "Invoice Date",
            "Due Date",
            "Job",
            "AFE No.",
            "Cost Center",
            "To",
            "Attention",
            "Approver Code",
            "P.O. No.",
            "Major",
            "Minor",
            "Terms",
            "Location",
        ],
        # Header: text - Look in page 1 - use tailored positional regex (often no labels / not on the SAME line as the label)
        "header_special_patterns_text_or_lines": {
            "Notes": r"(Job\s*Name:.*?)(?=Description\s+UOM\s+Quantity\s+Rate\s+Amount)"
        },
        # Header: text - Look in entire pdf (will remove $ and ,)
        "header_totals_patterns_text_or_lines": {
            "SUBTOTAL": r"SUBTOTAL\s*\$?([\d,]+\.\d{2})",
            # CA-GST only (5%), GST only (5%), SK GST (5%)
            "GST": r"(?:CA-GST only \(5%\)|GST only \(5%\)|SK GST \(5%\))\s*\$?([\d,]+\.\d{2})",
            # SK PST (6%)
            "PST": r"SK PST \(6%\)\s*\$?([\d,]+\.\d{2})",
            "BALANCE DUE": r"BALANCE DUE\s*\$?([\d,]+\.\d{2})",
        },
        # Header: extracts 360 list of ticket dates current format
        "ticket_date_pattern": r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(\d{4})\b",
        "date_fields": [
            "Invoice Date",
            "Due Date",
        ],  # Header fields that need date formatting
        "date_format": "%m/%d/%y",  # input date_fields (above) current format
        # Header: Extracts 360 multi-line supplier address
        "address_config_text": {
            "field_name": "To Address",
            "start_after": ["Attention", "Approver Code", "Terms"],
            "stop_before": ["Location", "Job Name"],  # ← Remove "Minor" from here
            "stop_at_postal_code": True,
            "max_lines": 5,
        },
        # Line-items list (repeating) - tables
        "line_items_headers": ["Description", "UOM", "Quantity", "Rate", "Amount"],
        "line_items_totals_labels": {
            "SUBTOTAL": r"^SUBTOTAL$",
            # Exact stencils first, then anything containing GST
            "GST": r"^(?:CA-GST only \(5%\)|GST only \(5%\)|SK GST \(5%\)|.*GST.*)$",
            # Exact stencil first, then anything containing PST
            "PST": r"^(?:SK PST \(6%\)|.*PST.*)$",
            "BALANCE DUE": r"^BALANCE DUE$",
        },
        "anchor_total": "BALANCE DUE",  # Stop extracting more line-items when this is found
    },
    # Mantl
    "MANTL Canada, Inc.": {
        # Extract requirements for header fields / line-items
        "require_text": True,
        "require_text_lines": True,
        "require_words": True,
        "require_tables": False,
        # Extraction methods (pick 1 or more for header fields)
        "extract_header_using_text": True,
        "extract_header_using_positions": True,
        "extract_header_using_tables": False,
        # Extraction methods (pick only 1 for line items)
        "extract_line_items_using_positions": True,
        "extract_line_items_using_tables": False,
        # Header: text - Look in page 1 - use universal regex - more robust and not affected by orders
        "header_fields_text_or_lines": [
            "Invoice Date",
            "WORK AREA",
        ],
        # Header: text - Look in page 1 - use tailored positional regex (often no labels / not on the SAME line as the label)
        "header_special_patterns_text_or_lines": {
            "Invoice #": r"Invoice\s+(\d+)\s+Invoice Date",  # between line 1 and line 3 on every page / page 1
            "Bill to Address": r"Bill-to Address From\s*\n(.*?)\s*MANTL Canada, Inc\.\n",
            "Buyer Address": r"MANTL Canada, Inc.\n(.*?)Calgary, AB T2P3S2",  # only captures the zip code line
            "InvoiceDate": r"Invoice Date\s*:\s*(.*?)\n",
        },
        # Header: text - Look in entire pdf (will remove $ and ,)
        "header_totals_patterns_text_or_lines": {
            "Subtotal CAD": r"Subtotal CAD[\s\S]*?([()\d,.-]+)\s*\n",
            "GST CAD": r"GST CAD[\s\S]*?([()\d,.-]+)\s*\n",
            "PST CAD": r"PST(?:\s+CAD|\s+\([^)]*\))[\s\S]*?([()\d,.-]+)\s*\n",
            # allows any amount of space before or after the optional $ + any combination of digits, commas, or dots, any length.
            "Total Incl. Tax CAD": r"Total Incl\. Tax[\s\S]*?([()\d,.-]+)\s*\n",
        },
        "date_fields": [
            "Invoice Date",
            "InvoiceDate",
        ],  # Header fields that need date formatting
        "date_format": "%y/%m/%d",  # input date_fields (above) current format
        # Mandatory fields for parsing header section with positions (words) - when no table structures or very inconsistent layout
        # Header - words
        # top, bottom, left, right --> neighboring fields
        "header_fields_layout_words": {
            "Bill-to Customer No.": {
                "top": None,
                "bottom": "Field No.",
                "left": None,
                "right": "Ordered By:",
                "page": 1,
            },
            "Ordered By:": {
                "top": None,
                "bottom": "LSD No.",
                "left": "Bill-to Customer No.",
                "right": "PO No.",
                "page": 1,
            },
            "PO No.": {
                "top": None,
                "bottom": "Payment Terms",
                "left": "Ordered By:",
                "right": "Invoice Date",
                "page": 1,
            },
            "Invoice Date": {
                "top": None,
                "bottom": "MANTL Sales Order No.",
                "left": "PO No.",
                "right": None,
                "page": 1,
            },
            "Field No.": {
                "top": "Bill-to Customer No.",
                "bottom": "AFE No.",
                "left": None,
                "right": "LSD No.",
                "page": 1,
            },
            "LSD No.": {
                "top": "Ordered By:",
                "bottom": "GL No.",
                "left": "Field No.",
                "right": "Payment Terms",
                "page": 1,
            },
            "Payment Terms": {
                "top": "PO No.",
                "bottom": None,
                "left": "LSD No.",
                "right": "MANTL Sales Order No.",
                "page": 1,
            },
            "MANTL Sales Order No.": {
                "top": "Invoice Date",
                "bottom": None,
                "left": "Payment Terms",
                "right": None,
                "page": 1,
            },
            "AFE No.": {
                "top": "Field No.",
                "bottom": None,
                "left": None,
                "right": "GL No.",
                "page": 1,
            },
            "GL No.": {
                "top": "LSD No.",
                "bottom": None,
                "left": "AFE No.",
                "right": None,
                "page": 1,
            },
        },
        # Header section extraction margin - hardcode
        "header_fields_upper_bound": 190.53199920999998,
        "header_fields_lower_bound": 338.76699315,
        # Mandatory fields for parsing header section with positions (words)
        # This is used for default line-items positioning parsing (left aligned) using word positions or tables
        # Line-items
        "line_items_headers": [
            "Item No.",
            "Description",
            "Quantity",
            "UOM",
            "Unit Price",
            "Line Amount",
        ],
        # Hard coded header fields x-positions ranges
        # Optional for exacting line items using positions (words)
        # Needed when line items have different alignments (left, center, right) for each column
        "line_items_headers_x_range": {
            "Item No.": {"x0": 70, "x1": 197.9000001},
            "Description": {"x0": 197.9000001, "x1": 420},
            "Quantity": {"x0": 420, "x1": 478},
            "UOM": {"x0": 478, "x1": 521},
            "Unit Price": {"x0": 521, "x1": 600},
            "Line Amount": {"x0": 600, "x1": 720},
        },
        # header bottom position - hardcode
        "page_header_bottom": 128.78199920999998,
        # footer top position
        "page_footer_top": 547.59302674,
        # Stop extracting more line-items when this is found
        "anchor_total": "Subtotal CAD",
    },
    # Sundown GST/HST #
    "Sundown Oilfield Services": {
        # Extract requirements for header fields / line-items
        "require_text": True,
        "require_text_lines": True,
        "require_words": False,
        "require_tables": False,
        # Extraction methods (pick 1 or more for header fields)
        "extract_header_using_text": True,
        "extract_header_using_positions": False,
        "extract_header_using_tables": False,
        # Extraction methods (pick only 1 for line items)
        "extract_line_items_using_positions": False,
        "extract_line_items_using_tables": False,
        "extract_line_items_using_lines": True,
        # Header: text - Look in page 1 - use default regex
        # Need to include all possible header fields (labels used in regex as guards)
        "header_fields_text_or_lines": [
            "Invoice No",
            "Job Number(s)",
            "Date",
            "LSD",
            "PO No.",  # single line PO will be extracted
            "Cost Center",
            "GST/HST No.",
            "WCB No.",
        ],
        # Header: text - Look in entire pdf (will remove $ and ,), case-sensitive
        "header_totals_patterns_text_or_lines": {
            "Subtotal": r"Subtotal:[ \t]+([^\n\r]*)",
            # "GST" is special because regular match will match "GST/HST No." first since it's a substring
            "GST": r"GST:[ \t]+([^\n\r]*)",
            "PST": r"PST:[ \t]+([^\n\r]*)",
            "Total": r"Total:[ \t]+([^\n\r]*)",
        },
        # Header: text - Look in page 1 - use tailored positional regex (often no labels / not on the SAME line as the label)
        "header_special_patterns_text_or_lines": {
            # Matches "Invoice No:" + invoice number, then captures the following line (company name) up to before "Job Number(s)" or newline.
            "Invoice to": r"Invoice No:\s*\S+\s*([^\n]+?)(?=\s*(?:\n|Job Number\(s\)))",
            # Captures a single line containing an @, usually an email or username.
            # Inspector pattern stops at newline or any header field, never spans multiple lines.
            "Inspector": r"([^\n]*?@[^\n]*?)(?=\n|Job Number\(s\)|Date|LSD|PO No\.|Cost Center|GST/HST No\.|WCB No\.)",
            # PO spans across multiple lines, use this field for Xtracta
            # stop extracting when hitting "GST/HST No." or "Cost Center:", whichever comes first
            "PO block": r"PO No\.:(.*?)(?=GST/HST No\.|Cost Center:)",
        },
        # Line-items - using text_lines (order matters)
        "line_items_headers": ["Date", "Form No", "Amount"],
        # line-items title fields, and content regex patterns
        "line_items_extraction_patterns": {
            "Date": r"^[^\s]+",  # first token (e.g., 2025-10-17)
            "Description": r"(?<=\s).*?(?=\s+[0-9,.$]+$)",  # middle blob text
            "Amount": r"[0-9,.$]+$",  # trailing numeric value
        },
        # Stop extracting more line-items when a new line starts with this
        "anchor_total": "Subtotal:",
        "line_items_skip_list": ["Sundown Oilfield Service", "Invoice #:", "Page"],
    },
}
# Information on supplier's lines items and subtotals field names.
# used for validating line extractions before sending to next lambda function.
# for validation.py
SUPPLIERS_VALIDATION_FIELDS = {
    "360 Engineering": {
        "subtotal": "SUBTOTAL",
        # easier to find the target field name particular to supplier's invoice
        "line_items_fields": ["Quantity", "Rate"],
        "line_subtotal_field": "Amount",
    },
    "MANTL Canada, Inc.": {
        "subtotal": "Subtotal CAD",
        "line_items_fields": ["Quantity", "Unit Price"],
        "line_subtotal_field": "Line Amount",
    },
    # Sundown GST/HST #
    "Sundown Oilfield Services": {
        "subtotal": "Subtotal",
        "line_items_fields": ["Amount"],
        "line_subtotal_field": "Amount",
    },
}

# Additional supplier info for check AFE, CC, Sites,... etc.
# for adiitional lambda processing
SUPPLIERS_INFO = {
    "360 Engineering": {
        "supplierDUNS": "CT3450270",
        # Tells you which fields to look for
        "buyerNameField": "To",
        "buyerAFECCField": "AFE No.",
        "checkAFE": False,
        # For pricebook checking
        "checkPricebook": True,
        "line_item_description_field": "Description",
        "line_item_uom_field": "UOM",
        "line_item_rate_field": "Rate",
        "xtracta_id": 1002282,
        # the Xtracta group. Customize (needs to send back to step functions for further processing like checking AFE)
        # Send to Xtracta through custom php lambda with file Name and path, different API key
        "xtracta_group": "Customize",
    },
    "MANTL Canada, Inc.": {
        "supplierDUNS": "202730875",
        # Tells validate_AFE lambda which fields to look for
        "buyerNameField": "Bill to Address",
        "buyerAFECCField": "AFE No.",
        "checkAFE": True,
        "checkPricebook": False,
        "xtracta_id": 1002281,
        # the Xtracta group. Customize (needs to send back to step functions for further processing like checking AFE)
        # Send to Xtracta through custom php lambda with file Name and path, different API key
        "xtracta_group": "Customize",
    },
    # Sundown GST/HST #
    "Sundown Oilfield Services": {
        "supplierDUNS": "CT0510843",
        "buyerNameField": "Invoice To",
        "buyerAFECCField": "",
        "checkAFE": False,
        "checkPricebook": False,
        "xtracta_id": 1002333,
        # the Xtracta group. Canada (default group, not sending back to step functions the second time)
        "xtracta_group": "Canada",
    },
}
