// send Mantl Jobutrax pdf file to Xtracta_Customize group Workflow 1002281
// directly called by API Gateway, not part of the state machine, but can loop back in the state machine

// s3Helper.mjs
import { LambdaClient, InvokeCommand } from "@aws-sdk/client-lambda";

// set up lambda connection
const lambdaClient = new LambdaClient({ region: "ca-central-1" });

export const handler = async (event) => {
  console.log("EVENT:", JSON.stringify(event, null, 2));

  // Parse the body if it's a string (proxy integration)
  let actualEvent;
  try {
    actualEvent =
      typeof event.body === "string" ? JSON.parse(event.body) : event;
  } catch (err) {
    console.error("Failed to parse body:", err);
    return { statusCode: 400, body: "Invalid JSON body" };
  }

  let payload = {
    payload: actualEvent,
    params: {
      "Xtracta workflow ID": 1002281,
    },
    xtracta_id: 1002281,
    supplierDUNS: "202730875",
    buyerNameField: "Bill to Address",
    buyerAFECCField: "AFE No.",
    checkAFE: true,
  };

  // call Xtracta_upload_pdf_customize lambda through aws SDK
  const command = new InvokeCommand({
    FunctionName: "Xtracta_upload_pdf_customize",
    InvocationType: "Event", // async, fire-and-forget --limit 256KB
    Payload: Buffer.from(JSON.stringify(payload)), // encode your object
  });
  await lambdaClient.send(command);

  return {
    statusCode: 200,
    body: JSON.stringify({ message: "Processing started" }),
  };
};
