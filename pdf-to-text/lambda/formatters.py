"""Extract and organize header and line items data from text, lines, words and tables obtained in pdf_parser.py"""

import re
import copy
import math
import logging
from utils import extract_dates_helper, extract_smart_address, extract_field

logger = logging.getLogger(__name__)
logger.setLevel(
    logging.DEBUG
)  # only in current module log DEBUG messages, filter out aws bebug logs


def extract_header_fields_using_text(
    text: str, supplier: dict, page_divider: str
) -> dict:

    print(text)

    # Required fields
    header_fields_text_or_lines = supplier.get("header_fields_text_or_lines", [])
    header_totals_patterns_text_or_lines = supplier.get(
        "header_totals_patterns_text_or_lines", {}
    )
    header_special_patterns_text_or_lines = supplier.get(
        "header_special_patterns_text_or_lines", None
    )

    # Optional fields with None defaults
    ticket_date_pattern = supplier.get(
        "ticket_date_pattern", None
    )  # 360 needs a list of ticket dates
    address_config_text = supplier.get("address_config_text", None)

    # Split text into sections (page 1 and rest)
    header_section = text.split(page_divider)[0] if page_divider in text else text

    header_data = {}
    # Extract standard header fields - using default regex.
    # Works for fields like "Date: 2025-10-02", "LSD: 3241"
    if header_fields_text_or_lines:
        for label in header_fields_text_or_lines:
            value = extract_field(label, header_section, header_fields_text_or_lines)
            header_data[label] = value
    logger.debug(f"HEADER DATA: {header_data}")

    # Apply optional special patterns (search in header section before line items table)
    # Works for fields without labels such as Notes or Supplier's name
    # re.DOTALL matches every character, including newlines (multi-lines)
    if header_special_patterns_text_or_lines:
        for key, pattern in header_special_patterns_text_or_lines.items():
            logger.debug(f"{key}: {pattern}")
            match = re.search(pattern, header_section, re.DOTALL)
            if (
                match and match.lastindex and match.lastindex >= 1
            ):  # ← Check group(1) exists
                # Clean up the captured text
                value = match.group(1).strip()
                # Remove extra whitespace and normalize
                value = re.sub(r"\s+", " ", value)
                header_data[key] = value
            else:
                header_data[key] = ""

    # Extract multi-line address if configured (Not required. when each address line is mixed up with other info across the page)
    if address_config_text:
        field_name = address_config_text.get("field_name", "To Address")
        address_value = extract_smart_address(
            header_section, address_config_text, header_fields_text_or_lines
        )
        header_data[field_name] = address_value

    # Extract totals (search entire text) - if to be extracted from raw text
    if header_totals_patterns_text_or_lines:
        for key, pattern in header_totals_patterns_text_or_lines.items():
            match = re.search(pattern, text)
            if (
                match and match.lastindex and match.lastindex >= 1
            ):  # ← Check group(1) exists
                # Remove commas and format as decimal
                value = match.group(1).replace("$", "").replace(",", "").strip()
                header_data[key] = value
            else:
                header_data[key] = ""

    # Extract list of ticket dates if pattern provided - eg, for 360
    if ticket_date_pattern:
        header_data["Dates"] = extract_dates_helper(text, ticket_date_pattern)

    return header_data


def extract_header_fields_using_tables() -> dict:
    pass


def extract_header_fields_using_positions(words: list, supplier: dict) -> dict:

    header_fields_layout = copy.deepcopy(
        supplier.get("header_fields_layout_words", {})
    )  # ← Add deepcopy
    header_upper_bound = supplier.get("header_fields_upper_bound", 0)
    header_lower_bound = supplier.get("header_fields_lower_bound", math.inf)
    # get words within the given margin
    filtered_words = [
        word
        for word in words
        if word.get("top") >= header_upper_bound
        and word.get("bottom") <= header_lower_bound
    ]

    # STEP 1 get content_box margins

    # 1st loop, populate content box dimentsions (left, top) --> top of the the content box which is bottom of the header
    # use "top" instead of "doctop", and tighten match with page number
    # use top + bottom instead of top + height --> capture any # of lines within the content-box margin
    for key, value in header_fields_layout.items():
        target_page = value.get("page")

        for word in filtered_words:
            # Skip if wrong page
            if word.get("page") != target_page:
                continue

            # Check if key starts with this word: each key can contain multiple words
            # eliminate noise like single "G" instead of GL, must be more than 2 characters
            text = word.get("text")
            if text and len(text) > 1 and key.startswith(text):
                value["box-left"] = word.get("x0")
                value["box-top"] = word.get("bottom")  # row y1
                break

    # 2nd loop, populate content box dimentsions (right, bottom) using neighboring fields
    for key, value in header_fields_layout.items():
        bottom_field = value.get("bottom")
        right_field = value.get("right")
        top_field = value.get("top")
        target_page = value.get("page")

        for word in filtered_words:
            # Skip if wrong page
            if word.get("page") != target_page:
                continue

            word_text = word.get("text")

            # Check bottom field
            # eliminate noise like single "G" instead of GL, must be more than 2 characters
            if (
                word_text
                and len(word_text) > 1
                and bottom_field
                and bottom_field.startswith(word_text)
            ):
                value["box-bottom"] = word.get("top")

            # Check right field
            # eliminate noise like single "G" instead of GL, must be more than 2 characters
            if (
                word_text
                and len(word_text) > 1
                and right_field
                and right_field.startswith(word_text)
            ):
                value["box-right"] = word.get("x0")

            # Early exit if both found
            if "box-bottom" in value and "box-right" in value:
                break

        # if no neiboring fields (border), set inifity
        if "box-bottom" not in value.keys():
            value["box-bottom"] = header_lower_bound or math.inf
        if "box-right" not in value.keys():
            # if right most field or last field use field above's x1
            value["box-right"] = header_fields_layout.get(top_field, {}).get(
                "box-right", math.inf
            )

    logger.info(
        f"Populated header_fields_layout dictionary after STEP 1: {header_fields_layout}"
    )

    # STEP 2 populate header_fields_layout dictionary with content
    for key, value in header_fields_layout.items():
        target_page = value.get("page")
        box_left = value.get("box-left")
        box_right = value.get("box-right")
        box_top = value.get("box-top")
        box_bottom = value.get("box-bottom")

        for word in filtered_words:
            # Skip if wrong page
            if word.get("page") != target_page:
                continue

            # Check if word is within content box
            if (
                word.get("x0") >= box_left
                and word.get("x1") <= box_right
                and word.get("top") >= box_top
                and word.get("bottom") <= box_bottom
            ):
                value.setdefault("content", []).append(word.get("text"))
                # **No break here, wants to append all texts within this margin

    return {
        key: " ".join(value.get("content", []))
        for key, value in header_fields_layout.items()
    }


def extract_line_items_list_using_tables(tables: list, supplier: dict) -> dict:
    """
    return {Items: [{}, {}, {}, {}...], Totals: {}}
    """
    line_items_headers = supplier.get("line_items_headers")
    line_items_totals_labels = supplier.get("line_items_totals_labels")
    anchor_total = supplier.get(
        "anchor_total"
    )  # The last total to look for to stol ectractions, usually BALANCE DUE or Total, etc

    items = []
    # Initialize totals dict with all expected keys as empty strings
    totals = {key: "" for key in line_items_totals_labels.keys()}
    stop_extraction = False
    stop_extraction = False

    # check type
    for table in tables:
        if not isinstance(table, list):
            continue

        # check type
        for row in table:
            if not isinstance(row, list):
                continue
            # clean each key value pairs list
            row = [(cell or "").strip() for cell in row]

            # skip empty rows
            if not any(row):
                continue

            # detect totals section
            # Check if row[0] matches any total label pattern
            matched_total_key = None
            for total_key, label_pattern in line_items_totals_labels.items():
                if re.match(label_pattern, row[0]):
                    matched_total_key = total_key
                    break

            # If this row is a total or tax, capture it
            if matched_total_key:
                # Only update if it is not captured yet
                if not totals[matched_total_key] and len(row) > 1:
                    # Update the value (overwrites the empty string)
                    totals[matched_total_key] = (
                        row[1].replace("$", "").replace(",", "").strip()
                    )

                if matched_total_key == anchor_total:
                    stop_extraction = True
                    break  # STOP EXTRACTING ONCE extracting the BALANCE DUE, and then stop
                continue  # ← Jumps to next row immediately

            # skip non line-item rows
            if len(row) < len(line_items_headers):
                continue

            # skip table header row(s)
            if row == line_items_headers:
                continue

            # build dictionary dynamically
            item = {}
            for i, key in enumerate(line_items_headers):
                value = row[i].replace("$", "").replace(",", "").strip()
                item[key] = value
            items.append(item)

            # also extract Date list (for 360)
        if stop_extraction:
            break

    return {"Items": items, "Totals": totals}


def extract_line_items_list_using_positions(
    words: list, lines: list, supplier: dict
) -> dict:
    line_headers = supplier.get("line_items_headers")
    line_headers_string = " ".join(line_headers)
    page_header_y1 = supplier.get("page_header_bottom")
    page_footer_y0 = supplier.get("page_footer_top")
    anchor = supplier.get("anchor_total")
    y_tolerance = 3  # Allow slight misalignment for row position (y axis)

    # doctop the header row -- for locating the header
    row_header_doctop = None

    # a list of the page_header_y1 position of each valid row of all pages
    row_doctop_list = []
    line_items = []

    # STEP 1: Populate row_doctop_list (top positions)
    found_header = False

    for row in lines:
        line_text = row.get("text")
        row_y0 = row.get("top")
        row_y1 = row.get("bottom")
        row_doctop = row.get("doctop")

        # Stop at anchor
        if anchor in line_text:
            break

        # Find line items header row
        if line_text == line_headers_string:
            found_header = True
            row_header_doctop = row_doctop
            continue  # Skip the header row itself

        # After finding header, only collect rows within valid bounds
        if found_header:
            # Check if row is in content area
            if (
                row_y0 >= page_header_y1 - y_tolerance
                and row_y1 <= page_footer_y0 + y_tolerance
            ):
                row_doctop_list.append(row_doctop)

    logger.info(f"Found {len(row_doctop_list)} content rows")
    logger.info(f"row_doctop_list: {row_doctop_list}")

    # STEP 2: Populating cell_x_positions using header row
    # Used for determine cutoff lines between columns.

    # if harded-coded line_x_positions_hardcode is provided use it
    if "line_items_headers_x_range" in supplier:
        cell_x_positions = supplier["line_items_headers_x_range"]
    # otherwise dynamically populate cell positions using default left alignment
    else:
        # Initialize cell_x_positions structure
        cell_x_positions = {header: {} for header in line_headers}
        # Get only header row words
        header_words = [
            w
            for w in words
            if w.get("doctop") is not None
            and abs(w.get("doctop") - row_header_doctop) <= y_tolerance
        ]
        logger.debug(f"header_words: {header_words}")

        # Sort left to right (confirms proper column order)
        header_words.sort(key=lambda w: w.get("x0"))
        logger.debug(f"sorted header_words: {header_words}")

        for word in header_words:
            for i, header in enumerate(line_headers):
                text = word.get("text")
                if not (text and len(text) > 1 and header.startswith(text)):
                    continue

                # Set this column's left boundary
                cell_x_positions[header]["x0"] = word.get("x0")

                # Set previous column's right boundary
                if i > 0:
                    prev_header = line_headers[i - 1]
                    cell_x_positions[prev_header]["x1"] = word.get("x0")

                # Set last column's right boundary to infinity (in case the last column is not right-aligned)
                if i == len(line_headers) - 1:
                    cell_x_positions[header]["x1"] = float("inf")
                break
        logger.debug(f"Default dynamic cell_x_positions: {cell_x_positions}")

    # STEP 3: Generate item_list
    last_word_index = -1

    for row_doctop in row_doctop_list:
        temp_line = {}
        row_words = []  # current row
        # work on one row per iteration
        # 3a. Build one row_words list and update last_word_index
        for i, word in enumerate(words):
            if (
                i > last_word_index
                and abs(word.get("doctop") - row_doctop) <= y_tolerance
            ):
                row_words.append(word)
                last_word_index = i  # Update used word index

        # another row is added to row_words list

        # 3b. Build temp_line and assign words to columns for current row
        for word in row_words:
            for header, bounds in cell_x_positions.items():
                if bounds.get("x0") <= word.get("x0") < bounds.get("x1", math.inf):
                    temp_line.setdefault(header, []).append(word.get("text"))
                    break

        # 3c. Join words in each cell and add to line_items (["word"] --> "Word" )
        if temp_line:
            line_items.append(
                {key: " ".join(words_list) for key, words_list in temp_line.items()}
            )
    logger.debug(f"line_items count: {len(line_items)}")
    return {"Items": line_items}


def extract_line_items_list_using_lines(lines: list, supplier: dict) -> dict:

    # line items headere fields list
    header_fields_list = supplier.get("line_items_headers")
    # How cells of each row are extracted
    line_extraction_regex = supplier.get("line_items_extraction_patterns")
    # anchor key word to stop line extraction
    anchor = supplier.get("anchor_total")
    # Skip extracting if starting with any of the following
    skip_lines_list = supplier.get("line_items_skip_list")
    line_items = []

    found_header = False

    # Helper function, check if every field of the header list is in the given string(line) in order
    def check_in_order(headers, str):
        last_index = -1  # not found
        for field in headers:
            i = str.find(field)
            if i == -1 or i < last_index:
                return False
            last_index = i
        return True

    for line in lines:
        line_text = line.get("text", "").strip()

        # checks if line_text starts with anchor --> stop
        if line_text.startswith(anchor):
            break

        # Skip extracting if starting these
        if line_text.startswith(tuple(skip_lines_list)):
            continue

        # check if header is found
        if not found_header:
            found_header = check_in_order(header_fields_list, line_text)
            continue

        # process line items after header
        if found_header:
            # copy structure, extract content usung regex of each field
            line_item = {
                # if match found set value to match or set value to ""
                # remove $ and , in all fields (monetary or description)
                k: (
                    m.group(0).strip().replace(",", "").replace("$", "")
                    if (m := re.search(v, line_text))
                    else ""
                )
                for k, v in line_extraction_regex.items()
            }
            line_items.append(line_item)
    return {"Items": line_items}
