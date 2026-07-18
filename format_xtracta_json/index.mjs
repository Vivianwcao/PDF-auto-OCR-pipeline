// This lambda function takes the Xtracta json from s3 buckjet (emi-v3/uploads/timestamp.json),
// and reformat it into a json ready for AFE checking and mapping script parsing
// upload the formatted json to emi-v3/parsed_pdf/fileName.json

// s3Helper.mjs
import {
  S3Client,
  GetObjectCommand,
  PutObjectCommand,
} from "@aws-sdk/client-s3";
import { readableStreamToString } from "./utils.mjs";

//set up s3 connection
const s3Client = new S3Client({ region: "ca-central-1" });
const S3_BUCKET_NAME = "emi-v3";

async function getJsonFromS3(bucket, s3Key) {
  try {
    const command = new GetObjectCommand({
      Bucket: bucket,
      Key: s3Key, //**Do not include .json extension here */
    });

    const response = await s3Client.send(command);

    // Convert response.Body (stream) to string
    const bodyString = await readableStreamToString(response.Body);

    // Parse JSON
    const data = JSON.parse(bodyString);
    return data;
  } catch (error) {
    console.error(`Error retrieving ${s3Key} from S3:`, error);
    throw error;
  }
}

async function uploadToS3(dataObj, bucket, s3Key) {
  // **replace the existing data.json sent through gpt stamp reading lambda and/or updated by stamp reading lambda

  try {
    const dataString = JSON.stringify(dataObj, null, 4); // pretty print optional

    const command = new PutObjectCommand({
      Bucket: bucket,
      Key: s3Key,
      Body: dataString,
      ContentType: "application/json",
    });

    await s3Client.send(command);
    console.log(`Data successfully uploaded to S3 at ${s3Key}`);
  } catch (error) {
    console.error(`Error uploading to S3: ${error}`);
    throw error;
  }
}

export const handler = async (event) => {
  try {
    // "uploads/2025-10-22-01-26-50.json"
    let { filePath } = event;
    console.log("EVENT: ", event);

    // getJsonFromS3 returns already parsed JSON
    let dataObj = await getJsonFromS3(S3_BUCKET_NAME, filePath);
    console.log(dataObj);

    let { Items } = dataObj;

    // Format all header fields (top levels, not Items)
    for (let key in dataObj) {
      // == null checks either null or undefined
      if (dataObj[key] == null || dataObj[key] === "null") dataObj[key] = "";
    }

    // extract key fields
    let {
      supplierDUNS,
      Invocation_ID_xtracta,
      buyerNameField,
      buyerAFECCField,
      xtracta_id,
      checkAFE,
      checkPricebook,
      line_item_description_field,
      line_item_uom_field,
      line_item_rate_field,
      File_Name_xtracta,
    } = dataObj;

    // Xtracta has converted boolean into text --> convert back to boolean
    checkAFE = checkAFE === "true";
    checkPricebook = checkPricebook === "true";

    // Format line-items
    // Items in the json sent from Xtracta is in format Items: {column1: [...], column2: [...], ...}
    // We want to convert it to Items: [{field1: ..., field2: ..., field3: ..., ...}, {field1: ..., field2: ..., field3: ..., ...}, ...]
    let rows = {};
    for (let key in Items) {
      for (let i = 0; i < Items[key].length; i++) {
        rows[i] = rows[i] || {};
        rows[i][key] = Items[key][i];
      }
    }
    let formatted_items = [];
    for (let row in rows) {
      formatted_items.push(rows[row]);
    }

    // Update Item list
    dataObj.Items = formatted_items;
    console.log("Final invoice data: ", dataObj);

    // eg. parsed_pdf/2025-10-22T05-44-03-655Z.json
    let jsonFileName =
      File_Name_xtracta ?
        File_Name_xtracta.split(".")[0]
      : new Date().toISOString().replace(/[:.]/g, "-");
    const jsonFilePath = `parsed_pdf/${jsonFileName}.json`;

    await uploadToS3(dataObj, S3_BUCKET_NAME, jsonFilePath);

    const response = {
      statusCode: 200,
      supplierDUNS,
      s3Path: jsonFilePath,
      invocationId: Invocation_ID_xtracta,
      buyerNameField,
      buyerAFECCField,
      xtracta_id,
      checkAFE,
      checkPricebook,
      line_item_description_field,
      line_item_uom_field,
      line_item_rate_field,
    };
    return response;
  } catch (e) {
    return {
      statusCode: 500,
      body: JSON.stringify({ Error: e.message }),
    };
  }
};
