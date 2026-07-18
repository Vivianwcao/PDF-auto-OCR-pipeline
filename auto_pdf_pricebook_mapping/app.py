import json
import csv
import os, logging
from collections import defaultdict
from s3_helpers import download_json_from_s3, upload_json_to_s3

# Configure logging once
logging.basicConfig(
    level=logging.DEBUG,  # root logger
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    force=True
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # in current module log INFO and above messages, filter out aws debug logs
# 2026-02-01 12:01:00 | INFO | app | Starting program

# Helper parse dict
def parse_obj(obj, field_name_list):
    parsed = {}
    for field in field_name_list:
        value = obj.get(field)
        if not value: # doesn't exist or falsy value like ""
            raise ValueError(f"Error: Missing or empty field: {field}")
        parsed[field] = value
    return parsed

# Helper find pricebook, return file path
def find_pricebook(pricebooks:list, supplierDUNS:str, buyerName_normalized:str) -> str | None:
    for entry in pricebooks:
        if entry["supplierDUNS"] == supplierDUNS and entry["buyerName"] in buyerName_normalized:
            logger.info(f"Found pricebook: {entry['pricebook']}")
            return entry["filePath"]
    logger.info(f"No pricebook found for {supplierDUNS} - {buyerName_normalized.capitalize()}")
    return None

# Helper - read local csv file --> list
def csv_to_list(filePath: str) -> list:
    with open(filePath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            try:
                # handles None, " " --> inf
                row["invoice_rate"] = float(row.get("invoice_rate", "").strip() or "inf")
            except ValueError:
                # handles non numbers
                row["invoice_rate"] = float("inf")
            rows.append(row)
        return rows

# group pricebook rows by invoice_description (easier for repeating descriptions) by sort by rate
def pricebook_by_groups(pricebook_list:list) -> list:
    #Step 1 group by invoice_descriptions
    grouped = defaultdict(list)
    for row in pricebook_list:
        grouped[row["invoice_description"]].append(row)
    
    # step 2 sort each group by invoice_rate
    for description, rows in grouped.items():
        rows.sort(key=lambda r: r["invoice_rate"]) # already a float
    # logger.info(f"grouped pricebook: {grouped}")
    return grouped

    # sample
    #     {
    #   "Junior engineer": [
    #       {'Pricebook_description':'xx0','Pricebook_partId':'11222',...},
    #       {'Pricebook_description':'xx1','Pricebook_partId':'11223',...}
    #   ],
    #   "Intermediate engineer": [
    #       {'Pricebook_description':'yyy','Pricebook_partId':'33444',...}
    #   ],
    #   "Senior engineer": [
    #       {'Pricebook_description':'zzz','Pricebook_partId':'66644',...}
    #   ]
    # }

# Helper - maps pricebook part id and uom
# updates original line-items list
def map_pricebook(grouped_pricebook, line_item_list, parsed: list) -> str:
    matched = 0
    total = len(line_item_list)
    for item in line_item_list:
        # use .get() with fallback for line-items. some don't have every field extracted.
        item_rate_str = item.get(parsed["line_item_rate_field"], "").strip()
        item_desc = item.get(parsed["line_item_description_field"], "").strip()       
        if not item_rate_str or not item_desc:
            total -= 1
            continue
        matched_group = grouped_pricebook.get(item_desc)
        if not matched_group:
            logger.info(f"No match found for: {item_desc}")
            continue
        item_rate = float(item_rate_str or "inf")
        matched_before = matched
        for row in matched_group:
            if row["invoice_rate"] >= item_rate: # invoice_rate is converted to float when pricebook csv is parsed
                # create new field part_id, keep original description for filtering out taxes calculation (Tourism Levy) in mapping script
                item["part_id"] = row["pricebook_partId"]
                item["pricebook_description"] = row["pricebook_description"]
                item[parsed["line_item_uom_field"]] = row["pricebook_uom"]
                logger.info(f"Match found: {item_desc} --> {row['pricebook_partId']}")
                matched += 1
                break
        if matched_before == matched:
            logger.info(f"No match found for: {item_desc} with rate: {item_rate}")        
    return f"{matched}/{total}"

# pricebook mapping list - quick for fuzzy match
pricebooks = [
    # 360
    {
        "supplierDUNS":"CT3450270", 
        "buyerName": "orphan well", 
        "pricebook": "owa-msa2025001000", 
        "filePath": os.path.join(os.path.dirname(__file__), "pricebooks", "360 - OWA - MSA # 2025001000.csv")
    }
]

def lambda_handler(event, context):
    logger.info(f"EVENT: {event}")
    return_obj = event
    try:
        # check supplierDuns and buyer against the mapper. get pricebook name
        if not event:
            raise ValueError("Event object not provided.")
            
        checkPricebook = event.get("checkPricebook", False)
        if not checkPricebook or checkPricebook == "false": # string returned from Xtracta
            return_obj["message"] = "No pricebook mapping required."
            return return_obj
        
        field_names = [
            "s3Path", 
            "supplierDUNS", 
            "buyerNameField", 
            "line_item_description_field", 
            "line_item_uom_field", 
            "line_item_rate_field"
        ]
        parsed = parse_obj(event, field_names)

        # retrieve json from s3
        json_dict = download_json_from_s3(parsed["s3Path"])

        buyerName_normalized = json_dict.get(parsed["buyerNameField"], "").strip().lower()
        pricebook_file_path = find_pricebook(pricebooks, parsed["supplierDUNS"], buyerName_normalized)
        if not pricebook_file_path:
            return_obj["message"] = f"No pricebook found for {parsed['supplierDUNS']} - {buyerName_normalized}"
            return return_obj
        if "Items" not in json_dict:
            return_obj["message"] = "No Items list found in the json file retrieved from s3."
            return return_obj            
        line_items = json_dict["Items"]
        # read csv to compare and swap partIds in json
        pricebook_list = csv_to_list(pricebook_file_path)
        pricebook_grouped = pricebook_by_groups(pricebook_list)  
        result = map_pricebook(pricebook_grouped, line_items, parsed)

        # upload json to s3 (same file key)
        upload_json_to_s3(json_dict, parsed["s3Path"])
        return_obj["message"] = f"Successfully matched {result} line-items."

    except Exception as e:
        return_obj["message"] = f"Pricebook checking error: {e}"
        return return_obj
    else:
        return return_obj


if __name__ == "__main__":
    with open("./input.json") as f:
        event = json.load(f)

    result = lambda_handler(event, None)
    print(result)
