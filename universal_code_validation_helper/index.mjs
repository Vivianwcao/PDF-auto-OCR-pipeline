// s3Helper.mjs
import {
  S3Client,
  GetObjectCommand,
  PutObjectCommand,
} from "@aws-sdk/client-s3";
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";
import { readableStreamToString } from "./utils.mjs";

// set up lambda connection
const lambdaClient = new LambdaClient({ region: "ca-central-1" });

//set up s3 connection
const s3Client = new S3Client({ region: "ca-central-1" });
const S3_BUCKET_NAME = "emi-v3";

/**
 * Retrieve JSON file from S3
 * @param {string} s3Key - The object key in S3
 * @returns {object} - json object
 */
async function getJsonFromS3(bucket, s3Key) {
  try {
    const command = new GetObjectCommand({
      Bucket: bucket,
      Key: s3Key,
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

async function uploadToS3(invoiceData, bucket, s3Key) {
  // **replace the existing data.json sent through gpt stamp reading lambda and/or updated by stamp reading lambda

  try {
    const dataString = JSON.stringify(invoiceData, null, 4); // pretty print optional

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
  console.log("EVENT", event);
  const { s3Path, supplierDUNS, buyerNameField, buyerAFECCField } = event;

  // to be returned, and viewd in state machine
  let response = event;
  response.coding_result = {
    afeListValidated: [],
    ccListValidated: [],
    allCodesValid: false,
    major_api: "",
    minor_api: "",
    lsd_api: "",
    message: "",
  };
  let { coding_result } = response;

  try {
    //retrieve data.json as an object from s3
    let invoiceData = await getJsonFromS3(S3_BUCKET_NAME, s3Path);

    const afeList = [invoiceData[buyerAFECCField]];
    const buyerName = invoiceData[buyerNameField];
    response.buyerName = buyerName;

    //if empty afeList exit early.
    if (!afeList.filter((code) => code.trim() !== "").length) {
      coding_result.message = "No AFE/CC provided!";
      invoiceData["validatedCodes"] = coding_result;
      // Upload updated invoiceData as data (without.json) to S3
      await uploadToS3(invoiceData, S3_BUCKET_NAME, s3Path);
      return response;
    }

    let jsonObj = { afeList, buyerName, supplierDUNS };
    // For Mantl Jobutrax
    const mantlJobutraxBuyers = ["Spur", "Cardinal"];
    if (
      supplierDUNS == "202730875" &&
      typeof buyerName === "string" &&
      mantlJobutraxBuyers.some((buyer) => buyerName.includes(buyer))
    )
      jsonObj.gl = invoiceData["GL No."];

    // call OpenInvoiceApiCalls lambda through aws SDK
    const command = new InvokeCommand({
      FunctionName: "OpenInvoiceJobutraxApiCalls",
      InvocationType: "RequestResponse", // wait for response -- limit 6MB; can also use "Event" for async --limit 256KB
      Payload: Buffer.from(JSON.stringify(jsonObj)), // encode your object
    });

    const result = await lambdaClient.send(command);

    // decode response if RequestResponse
    const resultObj = JSON.parse(Buffer.from(result.Payload).toString());
    console.log("Response from target Lambda:", resultObj);

    // passes Lambda-style internal errors returned in a 200 HTTP response.eg. buyerName not found in the list
    if (resultObj.statusCode && resultObj.statusCode != 200) {
      let bodyObj = JSON.parse(resultObj.body); //body is stringified from API
      coding_result.message = `API error: ${resultObj.statusCode}: ${bodyObj.error}`;
      invoiceData["validatedCodes"] = coding_result;
      // Upload updated invoiceData as data (without.json) to S3
      await uploadToS3(invoiceData, S3_BUCKET_NAME, s3Path);
      return response;
    }

    // Consume result
    //no further body parsing for non-proxy API setting
    let {
      afes = [],
      ccs = [],
      //only for Mantl Spur and Cardinal, else undefined
      major_api,
      minor_api,
      lsd_api,
    } = resultObj;

    //compare afeList with validated afeList and ccList --> if there's difference in total count --> allCodesValid is False
    let codesCountBefore = afeList.length;
    let codesCountAfter = 0;

    for (let afe of afes) {
      if (afe.length) codesCountAfter += 1;
    }
    for (let cc of ccs) {
      if (cc.length) codesCountAfter += 1;
    }

    // Update invoiceData with results, attach the fetch result to invoiceData

    coding_result.allCodesValid = codesCountBefore == codesCountAfter;
    coding_result.afeListValidated = afes;
    coding_result.ccListValidated = ccs;
    coding_result.major_api = major_api;
    coding_result.minor_api = minor_api;
    coding_result.lsd_api = lsd_api;
    coding_result.message = "Done verifying AFE/CC! :D";
    invoiceData["validatedCodes"] = coding_result;

    // Upload updated invoiceData to S3
    await uploadToS3(invoiceData, S3_BUCKET_NAME, s3Path);
    return response;
  } catch (e) {
    response.statusCode = 500;
    response.message = e.message;
    return response;
  }
};
