// Generic utility function that receive a list of AFEs(afeList) and send HTTP calls to OpenInvoice API to validate AFE or CC
// return an object that contains an list of valid AFEs or CCs and a boolean allCodesValid.
// **allCodesValid is only true if every code provided matches an AFE or a CC
// example input:
// {
//   "afeList": ["ab123", "ko234", "23twy"],
//   "buyerName": "Canadian Natural Resources Limited",
//   "supplierDUNS": "123456789"
// }
// example output: invalid code will be replaced with ""
// {
// 	"statusCode": 200,
// 	"body": "{
// 	  \"afes\": [\"ab123\", \"\", \"\"],
// 	  \"ccs\": [\"\", \"ko234\", \"\"]
// 	}"
//  }
import axios from "axios";
import https from "https";

import AWS from "aws-sdk";
AWS.config.update({ region: "ca-central-1" });
const ssm = new AWS.SSM();

let cachedParameters = null;
let cachedAgent = null;

export async function oiApiCall(buyerDUNS, supplierDUNS, afeList) {
  if (!cachedParameters) {
    // Fetch certificate and key from SSM
    const certificateParams = {
      Names: ["/emi-v3/oildex/certificate", "/emi-v3/oildex/ssl_key"],
      WithDecryption: true,
    };

    const response = await ssm.getParameters(certificateParams).promise();

    if (!response.Parameters || response.Parameters.length < 2) {
      throw new Error("Failed to retrieve SSL certificate or key from SSM");
    }

    cachedParameters = response.Parameters.reduce((acc, param) => {
      acc[param.Name.split("/").pop()] = param.Value;
      return acc;
    }, {});
    const { certificate, ssl_key } = cachedParameters;

    if (!certificate || !ssl_key) {
      throw new Error("certificate or ssl_key is missing from SSM parameters");
    }
    cachedAgent = new https.Agent({ cert: certificate, key: ssl_key });
    console.log("SSL certificate and key retrieved successfully");
  }

  const baseUrl = `https://api.openinvoice.com/docp/supply-chain/v2/`;
  const baseFilter = `buyerDUNS eq ${buyerDUNS} and supplierDUNS eq ${supplierDUNS}`;

  // Process each code in afeList
  const promises = afeList.map(async (code, index) => {
    if (!code || code.trim() === "") return { index, afe: "", cc: "" };

    const filter = `${baseFilter} and number eq ${code}`;
    const afesUrl = `${baseUrl}afes?$filter=${encodeURIComponent(filter)}`;
    const ccsUrl = `${baseUrl}cost-centers?$filter=${encodeURIComponent(filter)}`;

    try {
      // check if afe + if cc for each code
      const [afeResponse, ccResponse] = await Promise.all([
        axios.get(afesUrl, { httpsAgent: cachedAgent }),
        axios.get(ccsUrl, { httpsAgent: cachedAgent }),
      ]);

      const foundAfe =
        Array.isArray(afeResponse.data?.afes) &&
        afeResponse.data.afes.length > 0;
      const foundCc =
        Array.isArray(ccResponse.data?.costCenters) &&
        ccResponse.data.costCenters.length > 0;

      return { index, afe: foundAfe ? code : "", cc: foundCc ? code : "" };
    } catch (err) {
      console.error(`Error fetching code ${code}:`, err.message);
      return { index, afe: "", cc: "" };
    }
  });

  // preserves the order of the input array.
  // Async calls can resolve out of order
  // index is being used to preserve the original order in afeList.

  const results = await Promise.all(promises);

  results.sort((a, b) => a.index - b.index);
  const afes = results.map((r) => r.afe);
  const ccs = results.map((r) => r.cc);
  return { afes, ccs };
}
