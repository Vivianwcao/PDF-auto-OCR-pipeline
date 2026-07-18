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
  const {
    invocationId,
    s3Path,
    supplierDUNS,
    buyerNameField,
    buyerAFECCField,
  } = event;

  let response = {
    statusCode: 200,
    data: { test: "Not required" }, // what v3 needs, if s3Path doesn't exist will use this data instead
    invocationId, // what v3 needs, for finding which window in v3 operation console to place the data for mapping
    s3Path, // what v3 needs. with or without file extension .json, Primary source for retrieving the data file from s3
  };

  try {
    //retrieve data.json as an object from s3
    let invoiceData = await getJsonFromS3(S3_BUCKET_NAME, s3Path);

    const afeList = [invoiceData[buyerAFECCField]];
    const buyerName = invoiceData[buyerNameField];
    response.buyerName = buyerName;

    let allCodesValid = false;

    //if empty afeList exit early.
    if (!afeList.filter((code) => code.trim() !== "").length) {
      invoiceData["validatedCodes"] = {
        afeListValidated: [],
        ccListValidated: [],
        allCodesValid: allCodesValid,
      };
      // Upload updated invoiceData as data (without.json) to S3
      await uploadToS3(invoiceData, S3_BUCKET_NAME, s3Path);

      response.message = "No AFE/CC provided!";
      return response;
    }

    let jsonObj = { afeList, buyerName, supplierDUNS };

    // call OpenInvoiceApiCalls lambda through aws SDK
    const command = new InvokeCommand({
      FunctionName: "OpenInvoiceApiCalls",
      InvocationType: "RequestResponse", // wait for response -- limit 6MB; can also use "Event" for async --limit 256KB
      Payload: Buffer.from(JSON.stringify(jsonObj)), // encode your object
    });

    const result = await lambdaClient.send(command);

    // decode response if RequestResponse
    const resultObj = JSON.parse(Buffer.from(result.Payload).toString());
    console.log("Response from target Lambda:", resultObj);

    // const jsonString = JSON.stringify(jsonObj);
    // console.log("JSON to be sent for API call: ", jsonString);

    // //API call afeList, buyerName, supplierDUNS
    // let url = "https://4eaoeep1oj.execute-api.ca-central-1.amazonaws.com/prod/";

    // const res = await fetch (url, {
    //   method: "POST",
    //   headers: {
    //     "Content-Type": "application/json",
    //     "Content-Length": Buffer.byteLength(jsonString).toString(), //**This is mandatory field for making HTTP call to API
    //   },
    //   body: jsonString
    // });

    // // catches real HTTP errors, net work errors
    // if (!res.ok) {
    //   throw new Error(`HTTP error: ${res.status}: ${resultObj.error}`);
    // }

    // // Get the res object
    // const resultObj = await res.json(); //parse the json string automatically --> json object by fetch
    // console.log("API call response: ", resultObj);

    // passes Lambda-style internal errors returned in a 200 HTTP response.eg. buyerName not found in the list
    if (resultObj.statusCode && resultObj.statusCode != 200) {
      let bodyObj = JSON.parse(resultObj.body); //body is stringified from API

      response.message = `API error: ${resultObj.statusCode}: ${bodyObj.error}`;
      return response;
    }

    // Consume result
    //no further body parsing for non-proxy API setting
    let { afes: afeListValidated, ccs: ccListValidated } = resultObj;

    console.log("AFE list validated: ", afeListValidated);
    console.log("CC list validated: ", ccListValidated);

    //compare afeList with validated afeList and ccList --> if there's difference in total count --> allCodesValid is False
    let codesCountBefore = afeList.length;
    let codesCountAfter = 0;

    for (let afe of afeListValidated) {
      if (afe.length) codesCountAfter += 1;
    }
    for (let cc of ccListValidated) {
      if (cc.length) codesCountAfter += 1;
    }
    allCodesValid = codesCountBefore == codesCountAfter;
    console.log(
      "Total codes count before and after and allCodesValid: ",
      `${codesCountBefore}, ${codesCountAfter}, ${allCodesValid}`,
    );

    // Update invoiceData with results, attach the fetch result to invoiceData
    invoiceData["validatedCodes"] = {
      afeListValidated,
      ccListValidated,
      allCodesValid,
    };
    console.log("UPDATED DATA: ", JSON.stringify(invoiceData));

    // Upload updated invoiceData to S3
    await uploadToS3(invoiceData, S3_BUCKET_NAME, s3Path);

    response.message = "Done verifying AFE/CC! :D";
    response.allCodesValid = allCodesValid;
    response.afeListValidated = afeListValidated;
    response.ccListValidated = ccListValidated;
    return response;
  } catch (e) {
    response.statusCode = 500;
    response.message = e.message;
    return response;
  }
};
