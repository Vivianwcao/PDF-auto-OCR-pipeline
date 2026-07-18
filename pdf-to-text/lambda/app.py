import boto3
import json
import logging
from io import BytesIO
from pdf_parser import (
    overwrite_pdfplumber_table_settings,
    overwrite_pdfplumber_lines_settings,
    overwrite_pdfplumber_words_settings,
    pdf_extract_tables, 
    pdf_extract_text, 
    pdf_extract_lines, 
    pdf_extract_words
    )
from formatters import (
    extract_header_fields_using_text, 
    extract_header_fields_using_tables, 
    extract_header_fields_using_positions, 
    extract_line_items_list_using_tables, 
    extract_line_items_list_using_positions,
    extract_line_items_list_using_lines
)
from data import SUPPLIERS_INFO, SUPPLIERS_STRATEGY_SETTINGS, SUPPLIERS_FORMATTER, SUPPLIERS_VALIDATION_FIELDS
from utils import format_date
from validation import validate_items

s3_client = boto3.client("s3")
bucket = "emi-v3"

PAGE_DIVIDER = "--PAGE_1_END--"

# Configure logging once
logging.basicConfig(
    level=logging.INFO,  # root logger
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # only in current module log DEBUG messages, filter out aws bebug logs
# 2026-02-01 12:01:00 | INFO | app | Starting program
# 2026-02-01 12:01:01 | DEBUG | service | Loading data

# return the pdf content in bytes
def get_file_from_s3(bucket_name, file_key):
    """Retrieve a file from S3 and return its contents as bytes."""    
    file_key = file_key.strip()
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = response["Body"].read()  # Read file content as bytes
        logger.info(f"Successfully retrieved file: {file_key} from bucket: {bucket_name}")
        return file_content
    except Exception as error:
        logger.error(f"Error retrieving file from S3: {error}")
        raise  # Re-throw to be handled by the caller

def upload_to_s3(data, bucket_name, file_key):
    """Upload JSON data to S3."""
    try:
        # Convert to JSON string
        data_string = json.dumps(data, indent=4)

        # Upload parameters
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=data_string,
            ContentType="application/json"
        )

        logger.info(f"Data successfully uploaded to S3 at {file_key}")

    except Exception as error:
        logger.error(f"Error uploading to S3: {error}")
        raise  # Re-throw to be handled by the caller

def lambda_handler(event, context):
    try:
        logger.debug(f"Event: {event}")

        # STEP 1 Get the PDF from S3 bucket
        file_key = event["primaryFile"]["path"]
        file_name = event["primaryFile"]["name"]
        logger.info(f"Fetching {file_name} from {bucket}/{file_key}")
        pdf_bytes = get_file_from_s3(bucket, file_key)

       # Convert bytes to a BytesIO stream 
        pdf_file = BytesIO(pdf_bytes)

        # STEP 2: Extract text (Mandatory for finding supplier's name)
        extracted_text = pdf_extract_text(pdf_file)
        pdf_file.seek(0) # reset the stream
    
        # STEP 3: Determine supplier-specific strategy settings and merge with defaults
        for key in SUPPLIERS_STRATEGY_SETTINGS:
            if key.lower() in extracted_text.lower():
                # Get short-hand supplier_identifier
                supplier_identifier = key
                supplier_table_settings = SUPPLIERS_STRATEGY_SETTINGS.get(key, {}).get("pdfplumber_table_settings", {})
                supplier_lines_settings = SUPPLIERS_STRATEGY_SETTINGS.get(key, {}).get("pdfplumber_lines_settings", {})
                supplier_words_settings = SUPPLIERS_STRATEGY_SETTINGS.get(key, {}).get("pdfplumber_words_settings", {})
                # Merge supplier settings with defaults
                merged_table_settings = overwrite_pdfplumber_table_settings(**supplier_table_settings)
                merged_lines_settings = overwrite_pdfplumber_lines_settings(**supplier_lines_settings)
                merged_words_settings = overwrite_pdfplumber_words_settings(**supplier_words_settings)
                break
        else:
            # Handle case when no supplier is found
            raise ValueError("No supplier found in extracted text.")
            # or log a warning, use defaults, etc.
            
        supplier = SUPPLIERS_FORMATTER.get(supplier_identifier)
        if not supplier:
            raise ValueError(f"Unknown supplier: {supplier_identifier}")

        # Extract PDF
        extracted_lines = None
        extracted_words = None
        extracted_tables = None
        combined_data = {}
        header = {}
        line_items = {}

        # STEP 4: Get lines, tables, words using PDFPlumber methods based in invoice structure
        # Extract lines if needed   
        if supplier.get("require_text_lines"): 
            pdf_file.seek(0)
            extracted_lines = pdf_extract_lines(pdf_file, merged_lines_settings)

        # Extract words if needed
        if supplier.get("require_words"):
            pdf_file.seek(0)
            extracted_words = pdf_extract_words(pdf_file, merged_words_settings)

        # Extract tables if needed
        if supplier.get("require_tables"):
            pdf_file.seek(0)
            extracted_tables = pdf_extract_tables(pdf_file, merged_table_settings)

        # STEP 5: Extract Header/line-items using lines, tables, words data based in invoice structure
        # extract header fields
        if supplier.get("extract_header_using_text"):
            header.update(extract_header_fields_using_text(extracted_text, supplier, PAGE_DIVIDER))
        
        if supplier.get("extract_header_using_tables"):
            header.update(extract_header_fields_using_tables())

        if supplier.get("extract_header_using_positions"):
            header.update(extract_header_fields_using_positions(extracted_words, supplier))    

        # STEP 6: Extract line-items
        if supplier.get("extract_line_items_using_tables"):
            line_items.update(extract_line_items_list_using_tables(extracted_tables, supplier))

        elif supplier.get("extract_line_items_using_positions"):
            line_items.update(extract_line_items_list_using_positions(extracted_words, extracted_lines, supplier))

        elif supplier.get("extract_line_items_using_lines"):
            line_items.update(extract_line_items_list_using_lines(extracted_lines, supplier))

        # STEP 7: Final formating on header-text fields
        # date fields, eg "Invoice Date", "Due Date" --> YYYY-MM-DD
        date_fields = supplier.get("date_fields", None) # fields that require date formatting
        date_format = supplier.get("date_format", "%m/%d/%y")  # raw date format
        
        if date_fields:
            for field in date_fields:
                if field in header and header[field]:
                    header[field] = format_date(header[field], date_format)
            
        # STEP 8: get supplier's additional info like DUNs
        supplier_info = SUPPLIERS_INFO.get(supplier_identifier)
        
        # combine all data
        combined_data = header | line_items | supplier_info

        # STEP 9: validate line_items total vs subtotal
        supplier_terms = SUPPLIERS_VALIDATION_FIELDS.get(supplier_identifier)
        are_valid_lines = validate_items(combined_data, supplier_terms) # bool
        combined_data["are_valid_lines"] = are_valid_lines
        # STEP 10: upload combined data to S3

        # # overwrite with raw data - for testing pdfPlumber result
        # combined_data = {"text" : extracted_text, "tables": extracted_tables, "lines": extracted_lines, "words": extracted_words}

        # STEP 11: Upload to S3
        s3_path = f"parsed_pdf/{file_name.rsplit('.', 1)[0]}.json"

        # formatted
        upload_to_s3(combined_data, bucket, s3_path)
        logger.info(f"Processed {file_name} and saved to {s3_path}")

        # STEP 12 build payload and params objects for Xtracta API (if line extraction fails) required by php lambda
        xtracta_group = supplier_info.get("xtracta_group")
        xtracta_id = supplier_info.get("xtracta_id")
        params = {}
        payload = {}
        invocationId = event.get("invocationId")
        payload["invocationId"] = invocationId
        primary_file = event.get("primaryFile") or {}
        payload["primaryFile"] = {}
        payload["primaryFile"] = {"name": primary_file.get("name"), "path": primary_file.get("path")}
        params["Xtracta workflow ID"] = xtracta_id

        return {
            "statusCode": 200,
            "invocationId": invocationId,
            "s3Path": s3_path,
            "areValidLines": are_valid_lines,
            "xtracta_id": xtracta_id,
            "xtracta_group": xtracta_group,
            # php Lambda requires invocationId, primaryFile.name & .path and Xtracta Workflow Id to send to Xtracta
            "params": params, # required for sending to Xtracta 
            "payload":payload, # required for sending to Xtracta 
            "supplierDUNS": supplier_info.get("supplierDUNS"),
            "buyerNameField": supplier_info.get("buyerNameField"),
            "buyerAFECCField": supplier_info.get("buyerAFECCField"),
            "checkAFE": supplier_info.get("checkAFE"),
            # For pricebook checking
            "checkPricebook": supplier_info.get("checkPricebook"),        
            "line_item_description_field": supplier_info.get("line_item_description_field"), 
            "line_item_uom_field": supplier_info.get("line_item_uom_field"), 
            "line_item_rate_field": supplier_info.get("line_item_rate_field"), 
        }
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)

        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
