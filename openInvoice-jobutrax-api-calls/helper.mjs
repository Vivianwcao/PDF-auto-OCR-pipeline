const buyerDuns = {
  // Fraction OpenInvoice buyers - use lowercase
  "paramount resources": { duns: "241197748", platform: "oi" },
  "canadian natural resources": { duns: "209137967", platform: "oi" },
  cnul: { duns: "209137967", platform: "oi" },
  nuvista: { duns: "201898199", platform: "oi" },
  "birchcliff energy": { duns: "207002457", platform: "oi" },
  "parallax energy": { duns: "243415101", platform: "oi" },
  "teine energy": { duns: "244269655", platform: "oi" },
  "baytex energy": { duns: "249844952", platform: "oi" },
  "petrus resources": { duns: "248415254", platform: "oi" },
  spartan: { duns: "858222169", platform: "oi" },
  "whitecap resources": { duns: "243826232", platform: "oi" },
  "coelacanth energy": { duns: "737703405", platform: "oi" },
  "advantage energy": { duns: "201812844", platform: "oi" },
  "tourmaline oil corp": { duns: "243813578", platform: "oi" },
  "vermilion energy": { duns: "801424250", platform: "oi" },
  "vermillion energy": { duns: "801424250", platform: "oi" },
  "insignia energy": { duns: "883597767", platform: "oi" },
  "orlen upstream canada": { duns: "243340515", platform: "oi" },
  "peyto exploration & development corp": { duns: "256778903", platform: "oi" },
  "arc resources": { duns: "253875702", platform: "oi" },
  "logan energy": { duns: "243301847", platform: "oi" },
  "hwn energy": { duns: "248507761", platform: "oi" },
  "kelt exploration": { duns: "203215744", platform: "oi" },
  "mancal energy": { duns: "256861436", platform: "oi" },
  "artis exploration": { duns: "203441316", platform: "oi" },
  "storm development": { duns: "719216400", platform: "oi" },
  "saturn oil": { duns: "879092112", platform: "oi" },
  bonterra: { duns: "255387904", platform: "oi" },
  cygnet: { duns: "785217803", platform: "oi" },

  // Mantl OpenInvoice buyers - use lowercase
  "strathcona resources": { duns: "244245622", platform: "oi" },
  "surge energy": { duns: "259917664", platform: "oi" },
  "ish energy": { duns: "248085789", platform: "oi" },
  "longshore resources": { duns: "820417962", platform: "oi" },
  "vantage point resources": { duns: "782328314", platform: "oi" },
  "karve energy": { duns: "259724847", platform: "oi" },
  "lynx energy": { duns: "200240121", platform: "oi" },
  "caltex trilogy": { duns: "770663409", platform: "oi" },
  "obsidian energy": { duns: "241577774", platform: "oi" },
  "taqa north": { duns: "243408312", platform: "oi" },
  "tundra oil & gas": { duns: "241710045", platform: "oi" },
  "ipc canada": { duns: "202060849", platform: "oi" },
  "woodland development": { duns: "208818634", platform: "oi" },
  "burgess creek exploration": { duns: "243203540", platform: "oi" },
  "journey energy": { duns: "884659913", platform: "oi" },
  "harvest operation": { duns: "201817959", platform: "oi" },
  "ranahan ressources": { duns: "714185709", platform: "oi" },
  "blue sky resources": { duns: "256826561", platform: "oi" },
  "battle river energy": { duns: "203845185", platform: "oi" },
  "islander oil": { duns: "795502533", platform: "oi" },
  "prairie provident resources": { duns: "887429165", platform: "oi" },
  "sharptail energy": { duns: "752547158", platform: "oi" },
  "hemisphere energy": { duns: "242917573", platform: "oi" },
  "spectrum resource": { duns: "894723865", platform: "oi" },
  "prairie thunder resources": { duns: "722380524", platform: "oi" },
  "corex resources": { duns: "204394704", platform: "oi" },

  // Mantl Jobutrax
  "cardinal energy": { duns: "203153713", platform: "jobutrax" }, // Jobutrax
  "spur petroleum": { duns: "203505508", platform: "jobutrax" }, // Jobutrax
};

export function getBuyerInfo(searchString) {
  if (!searchString) return {};

  const searchStrLower = searchString.toLowerCase();

  for (const [companyName, info] of Object.entries(buyerDuns)) {
    const lowerCompany = companyName.toLowerCase();
    if (
      searchStrLower.includes(lowerCompany) ||
      lowerCompany.includes(searchStrLower)
    ) {
      return info;
    }
  }
  // no match found
  return {};
}
