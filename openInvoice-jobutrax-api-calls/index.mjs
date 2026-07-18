import { getBuyerInfo } from "./helper.mjs";
import { jobutraxApiCall } from "./jobutraxApi.mjs";
import { oiApiCall } from "./oiApi.mjs";

export const handler = async (event) => {
  console.log("Event received:", JSON.stringify(event, null, 2));

  try {
    // Validate event properties
    let { afeList, buyerName, supplierDUNS, gl } = event;

    if (!Array.isArray(afeList)) {
      throw new Error("afeList must be an array");
    }
    if (!afeList.filter((code) => code.trim() !== "").length)
      throw new Error("afeList cannot be empty");
    if (!buyerName) throw new Error("buyerName is missing");
    if (!supplierDUNS) throw new Error("supplierDUNS is missing");

    // Validate buyer: if not valid buyer --> exit early
    const { duns: buyerDUNS, platform: buyerPlatform } =
      getBuyerInfo(buyerName) ?? {};
    if (!buyerDUNS)
      throw new Error(`No DUNS number found for buyer: ${buyerName}`);

    //list for OI and single string for Jobutrax
    let afes;
    let ccs;
    let major_api;
    let minor_api;
    let lsd_api;
    if (buyerPlatform === "oi") {
      //ades and ccs are lists
      ({ afes, ccs } = await oiApiCall(buyerDUNS, supplierDUNS, afeList));
      return { afes, ccs };
    } else if (buyerPlatform === "jobutrax") {
      if (!gl)
        throw new Error(
          "gl not provided for Mantl Jobutrax buyer: " + buyerName,
        );
      ({ afes, ccs, major_api, minor_api, lsd_api } = await jobutraxApiCall(
        buyerDUNS,
        afeList,
        gl,
      ));
    }

    return { afes, ccs, major_api, minor_api, lsd_api }; //return json obj for non-proxy API gateway, no stringfy or header needed.
  } catch (err) {
    console.error("Error:", err);
    return {
      statusCode: 500,
      body: JSON.stringify({
        error: err.message,
      }),
    };
  }
};
