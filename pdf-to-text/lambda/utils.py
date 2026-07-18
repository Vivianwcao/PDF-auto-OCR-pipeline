"""Helper functions for header and line items formaters"""
import re
from datetime import datetime

def extract_dates(text: str, date_pattern: str):
    """ helper function to extract a list of ticket dates, for 360 (case, format strict)
    """
    matches = re.findall(date_pattern, text, flags=re.IGNORECASE)
    extracted = []

    for day, month, year in matches:
        try:
            date_obj = datetime.strptime(f"{day} {month} {year}", "%d %b %Y")
            extracted.append(date_obj.strftime("%Y-%m-%d"))
        except ValueError:
            continue

    return extracted

# datetime.strptime() requires an exact match between the input string and the format string.
# If the input string doesn’t match the format exactly, strptime() raises a ValueError.
# Tries to parse using provided or default to short year format (%y).
# If that fails, tries full year (%Y).
# If both fail, returns the original string unchanged.

# Accepted format codes:
# Examples of common ones:
# %Y → 4-digit year (e.g., 2025)
# %y → 2-digit year (e.g., 25)
# %m → month (01–12)
# %d → day (01–31)
# %H → hour (00–23)
# %M → minute (00–59)
# %S → second (00–59)
# %f → microsecond (000000–999999)
# %a, %A → weekday name
# %b, %B → month name
# %p → AM/PM
def format_date(date_str, input_format="%m/%d/%y", output_format="%Y-%m-%d"):
    """Convert date string to ISO format."""
    
    fallback_input_format = "%m/%d/%Y"# YYYY
    try:
        # convert into a datetime object
        dt = datetime.strptime(date_str, input_format)
        # convert into a string
        return dt.strftime(output_format)
    except:
        try:
            dt = datetime.strptime(date_str, fallback_input_format) 
            # convert into a string
            return dt.strftime(output_format)
        except:
            return date_str  # Return original if both YY, YYYY fail

def extract_dates_helper(text, pattern):
    """Extract dates matching a specific given pattern from text."""
    matches = re.findall(pattern, text, re.IGNORECASE)
    dates = []
    
    month_map = {
        'jan': 1, 'january': 1,
        'feb': 2, 'february': 2,
        'mar': 3, 'march': 3,
        'apr': 4, 'april': 4,
        'may': 5,
        'jun': 6, 'june': 6,
        'jul': 7, 'july': 7,
        'aug': 8, 'august': 8,
        'sep': 9, 'sept': 9, 'september': 9,
        'oct': 10, 'october': 10,
        'nov': 11, 'november': 11,
        'dec': 12, 'december': 12,
    }
    
    for match in matches:
        day, month_str, year = match
        month_num = month_map.get(month_str.lower(), 1)
        try:
            dt = datetime(int(year), month_num, int(day))
            dates.append(dt.strftime("%Y-%m-%d"))
        except:
            continue
    
    return dates

def is_address_component(text):
    """Check if text looks like part of an address (not a field label)."""
    # Address components with P.O. Box
    if text.startswith('P.O.') or text.startswith('PO Box'):
        return True
    
    # If it has a colon, it's likely a field label
    if ':' in text:
        return False
    
    # Contains street indicators
    street_indicators = ['St', 'Ave', 'Rd', 'Blvd', 'Dr', 'Ct', 'Lane', 'Way', 'Suite', '#']
    if any(indicator in text for indicator in street_indicators):
        return True
    
    # Contains postal code (Canadian format)
    if re.search(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d', text):
        return True
    
    return False

def is_address_like(text):
    """Check if text looks like an address component."""
    if not text:
        return False
    
    # Starts with number or #
    if text[0].isdigit() or text.startswith('#'):
        return True
    
    # Contains street indicators
    street_indicators = ['St', 'Ave', 'Rd', 'Blvd', 'Dr', 'Ct', 'Lane', 'Way', 'Suite', 'Street', 'Avenue', 'Road']
    if any(f" {indicator}" in text or text.startswith(indicator) for indicator in street_indicators):
        return True
    
    # Contains city/province/postal pattern (e.g., "Calgary AB T2P 4J8")
    if re.search(r'[A-Z]{2}\s+[A-Z]\d[A-Z]\s*\d[A-Z]\d', text):
        return True
    
    # Common city names with province abbreviations
    if re.search(r',?\s+(?:AB|BC|SK|MB|ON|QC|NS|NB|PE|NL|NT|YT|NU)\s+', text):
        return True
    
    return False

def extract_smart_address(text, config, all_labels):
    """
    Extract multi-line address using flexible configuration.
    Handles various invoice formats dynamically.
    Can extract address that appears inline or on subsequent lines.
    """
    start_after_labels = config.get("start_after", [])
    stop_before_labels = config.get("stop_before", [])
    stop_at_postal = config.get("stop_at_postal_code", True)
    max_lines = config.get("max_lines", 10)
    
    # Try each possible start label in order
    start_pos = None
    same_line_address = ""
    
    for label in start_after_labels:
        # Match the label and capture everything after it on the same line
        pattern = rf"{re.escape(label)}[ \t]*:?[ \t]*([^\n]*)"
        match = re.search(pattern, text)
        if match:
            try:
                same_line_content = match.group(1).strip()
                start_pos = match.end()
                
                # Check if this line has address content after the field value
                # Remove the field value itself (e.g., "D777" for Approver Code)
                # by checking if any other label appears on the same line
                remaining_on_line = same_line_content
                for other_label in all_labels:
                    if other_label in same_line_content:
                        # Split at the label and keep only part before it
                        parts = same_line_content.split(other_label)
                        # The part before is the field value
                        # Check if there's content after the other label
                        if len(parts) > 1:
                            after_other_label = parts[1].split(':')[-1].strip() if ':' in parts[1] else parts[1].strip()
                            if after_other_label and is_address_like(after_other_label):
                                same_line_address = after_other_label
                        break
                else:
                    # No other label found, check if the content itself is address-like
                    if is_address_like(same_line_content):
                        same_line_address = same_line_content
                
                break  # Successfully processed, exit loop
                
            except IndexError:
                continue  # No capture group, try next label
    
    if start_pos is None:
        return ""
    
    # Collect address lines
    address_lines = []
    
    # Add same-line address if found
    if same_line_address:
        address_lines.append(same_line_address)
    
    # Extract subsequent lines after the start position
    remaining = text[start_pos:]
    lines_after = remaining.split('\n')[1:max_lines+1]  # Skip first line (already processed)
    
    found_postal_code = False
    for line in lines_after:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # First, check for embedded country before stop labels (e.g., "Canada Location:")
        country_match = re.match(r'^(Canada|United States|USA|US)\s+', line, re.IGNORECASE)
        if found_postal_code and country_match:
            try:
                address_lines.append(country_match.group(1))
            except IndexError:
                pass  # No group captured
            break
        
        # Stop at configured stop labels ONLY after finding postal code
        if found_postal_code and any(stop_label in line for stop_label in stop_before_labels):
            break
        
        # Check if this line is a field label (e.g., "Minor:")
        is_field_label = any(line.startswith(label + ":") or line == label + ":" for label in all_labels)
        
        # If we've already found postal code and this is a standalone field label, skip it
        if found_postal_code and is_field_label:
            continue
        
        # Check if line has an embedded label (like "Terms: Net 30")
        line_to_add = line
        has_embedded_label = False
        
        for other_label in all_labels:
            if other_label in line and not line.startswith(other_label):
                # Address content before the label
                before_label = line.split(other_label)[0].strip()
                if before_label and is_address_like(before_label):
                    line_to_add = before_label
                    has_embedded_label = True
                    break
        
        # Also check for stop_before labels embedded in line
        if not has_embedded_label:
            for stop_label in stop_before_labels:
                if stop_label in line and not line.startswith(stop_label):
                    before_label = line.split(stop_label)[0].strip()
                    if before_label and is_address_like(before_label):
                        line_to_add = before_label
                        has_embedded_label = True
                        break
        
        # Stop if line starts with colon
        if line.startswith(':'):
            break
            
        # Add the line if it looks like an address
        if is_address_like(line_to_add):
            address_lines.append(line_to_add)
            
            # Mark if we found postal code
            if re.search(r'[A-Z]\d[A-Z]\s*\d[A-Z]\d', line_to_add):
                found_postal_code = True
                if not stop_at_postal:
                    continue
                # Continue to check for country on next line
                continue
        elif found_postal_code:
            # After postal code, check if this is a country name
            if len(line.split()) <= 2 and line[0].isupper() and not any(c.isdigit() for c in line):
                address_lines.append(line)
            break  # Stop after trying to find country
        else:
            # If line doesn't look like address and we haven't found postal yet
            # BUT if line had embedded label, continue (might be "Terms: Net 30" line)
            contains_field_label = any(label in line for label in all_labels)
            if contains_field_label:
                continue  # Skip this line, check next one
            # Otherwise, stop
            break
            # If had embedded label but extracted nothing, continue to next line
    
    # Join all address lines with space
    return " ".join(address_lines)

def extract_field(label, text, all_labels):
    """
    Extract field value that appears after a label.
    Only captures content on the SAME line as the label.
    Stops at: line end or next label occurrence.
    """
    # Use [ \t]* instead of \s* to match spaces/tabs but NOT newlines
    same_line_pattern = rf"{re.escape(label)}[ \t]*:?[ \t]*([^\n\r]*)"
    match = re.search(same_line_pattern, text)
    
    if not match:
        return ""

    try:
        value = match.group(1).strip()
    except IndexError:
        return ""  # No capture group
    
    # If the captured value is empty, return empty string
    if not value:
        return ""
    
    # Check if another label appears in this captured value
    for other_label in all_labels:
        if other_label != label:
            # Look for the other label (with optional spaces and colon)
            label_pattern = rf"{re.escape(other_label)}[ \t]*:?"
            label_match = re.search(label_pattern, value)
            if label_match:
                # Take only the part before the other label
                value = value[:label_match.start()].strip()
                break
    
    return value