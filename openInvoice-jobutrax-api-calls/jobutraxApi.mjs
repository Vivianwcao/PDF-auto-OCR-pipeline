// calling Jobutrax API to verify a single given code is afe or cc or invalid, extract LSD, and also verify major and minor code.
import axios from "axios";
import { SSMClient, GetParameterCommand } from "@aws-sdk/client-ssm";

const baseUrl = "https://jobutrax.pandell.com/api/v1/invoices/masters/";

let cachedToken = null;

export async function jobutraxApiCall(buyerDUNS, afeList, gl) {
  if (!cachedToken) {
    // Fetch token
    const ssmClient = new SSMClient({ region: "ca-central-1" });
    const command = new GetParameterCommand({
      Name: "/emi-v3/jobutrax/mantl/api-key",
      WithDecryption: true,
    });
    const response = await ssmClient.send(command);
    cachedToken = response.Parameter.Value;
  }

  //by this stage afeList is a non-empty list, gl is a non-empty string, lsd CAN be empty though.
  //afeList contains a single code for Jobutrax
  const code = afeList[0];
  let afes = [];
  let ccs = [];
  let major_api = "";
  let minor_api = "";
  let lsd_api = "";

  //1. check cc
  const ccData = await getApi(
    `${baseUrl}cost_centers?buyerDUNS=${buyerDUNS}&code=${encodeURIComponent(code)}`,
    cachedToken,
  );
  if (ccData.success) {
    ccs.push(code);
    const lsd_str = ccData?.data?.[0]?.description;
    if (lsd_str && lsd_str.length) lsd_api = extractLocation(lsd_str);
  } else {
    //2. check afe
    const afeData = await getApi(
      `${baseUrl}afes?buyerDUNS=${buyerDUNS}&code=${encodeURIComponent(code)}`,
      cachedToken,
    );
    if (!afeData?.success) {
      // Invalid afe/cc, stop checking Gl or LSD
      return { afes, ccs, major_api, minor_api, lsd_api };
    } else {
      afes.push(code);
      const lsd_str = afeData?.data?.[0]?.description;
      if (lsd_str && lsd_str.length) lsd_api = extractLocation(lsd_str);
    }
  }
  //3. check gl by now afe/cc is valid(gl is a non-empty string)
  const [major, minor] = gl.split(/[.\-\/\s]+/);
  const major_res = await getApi(
    `${baseUrl}major_codes?buyerDUNS=${buyerDUNS}&code=${encodeURIComponent(major)}`,
    cachedToken,
  );
  if (major_res.success) major_api = major;
  if (minor) {
    const minor_res = await getApi(
      `${baseUrl}minor_codes?buyerDUNS=${buyerDUNS}&code=${encodeURIComponent(minor)}`,
      cachedToken,
    );
    if (minor_res.success) minor_api = minor;
  }
  return { afes, ccs, major_api, minor_api, lsd_api };
}

// API get request helper
const getApi = async (paramString, token) => {
  try {
    const response = await axios.get(paramString, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (err) {
    // catch any non 200 response
    // 422 "message": "The selected code does not exist."
    // 503 "message": "Service Unavailable"
    // 401 "error": "Unauthenticated"
    return { success: false };
  }
};

// extract location from lsd helper
// Works for Spur and Cardinal
const extractLocation = (lsd) => {
  // begins with digits,
  // is at least 10 characters long,
  // contains at least two dashes,
  // and is composed only of digits, letters, forward slashes, and dashes,
  // ending at the next whitespace or the end of the string.
  const regex = /(?:^|\s)(?=(?:[^-\s]*-){2,})(\d[0-9A-Za-z\/-]{9,})(?=\s|$)/;

  const match = lsd.match(regex);
  // returns undefined or first match
  return match?.[1];
};
