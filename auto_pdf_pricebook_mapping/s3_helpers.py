import json
import boto3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)  # in current module log INFO and above messages, filter out aws debug logs
# 2026-02-01 12:01:00 | INFO | app | Starting program

s3_client = boto3.client("s3")
bucket_name = "emi-v3"

def download_json_from_s3(file_key) -> dict:
    """Retrieve a file from S3 and return its contents as bytes."""    
    file_key = file_key.strip()
    try:
        response = s3_client.get_object(
            Bucket=bucket_name, 
            Key=file_key
        )
        json_bytes = response["Body"].read() # bytes
        logger.info(f"Successfully retrieved file: {file_key} from bucket: {bucket_name}")
        json_dict = json.loads(json_bytes)
        return json_dict
    except Exception as error:
        logger.error(f"Error retrieving file from S3: {error}")
        raise  # Re-throw to be handled by the caller

def upload_json_to_s3(data, file_key):
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