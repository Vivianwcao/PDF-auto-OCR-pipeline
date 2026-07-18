import logging

""" validate if extracted lines-items add up to provided subtotal
"""

logger = logging.getLogger(__name__)
logger.setLevel(
    logging.DEBUG
)  # only in current module log DEBUG messages, filter out aws bebug logs


def validate_items(final_obj, supplier_validation_fields: dict) -> bool:
    # parse number helper function
    def parseNum(string: str) -> float:
        # eg. string is ""
        if not string:
            return 0.0
        try:
            return float(
                string.replace("$", "").replace(",", "").replace(" ", "").strip()
            )
        except ValueError:
            # String must represent a valid float entirely; otherwise it raises ValueError
            return 0.0

    tolerance = 0.6
    items = final_obj.get("Items") or []
    subtotal = parseNum(final_obj.get(supplier_validation_fields.get("subtotal")))
    # if subtotal is "" or 0, return False immediately
    if subtotal == 0:
        return False

    line_items_fields = supplier_validation_fields.get("line_items_fields", [])
    line_subtotal_field = supplier_validation_fields.get("line_subtotal_field", "")
    count = len(line_items_fields)

    # sum of line quantity * rate
    subtotal_cal_quantity_rate = 0
    # sum of line_subtotals
    subtotal_cal_line_subtotal = 0

    for item in items:
        # if list contains 2 strings (quantity, rate)
        if count == 2:
            # quantity, rate amount
            x = parseNum(item.get(line_items_fields[0]))
            y = parseNum(item.get(line_items_fields[1]))
            cal_amount = x * y

            # Only include non-zero rows (skip title/subtotal rows)
            if cal_amount != 0:
                subtotal_cal_quantity_rate += cal_amount
                subtotal_cal_line_subtotal += parseNum(item.get(line_subtotal_field))

        # if only 1 string --> line amount
        # eg. Sundown every line must have an amount, no title-only or subtotal-only row
        elif count == 1:
            z = parseNum(item.get(line_items_fields[0]))
            if z != 0:
                subtotal_cal_quantity_rate += z
        else:
            return False

    logger.info(
        f"Strategy 1 (qty*rate): {subtotal_cal_quantity_rate} vs actual subtotal: {subtotal}"
    )
    logger.info(
        f"Strategy 2 (line subtotals): {subtotal_cal_line_subtotal} vs actual subtotal: {subtotal}"
    )

    # Try both strategies - if either matches, return True
    strategy1_match = abs(subtotal_cal_quantity_rate - subtotal) < tolerance
    strategy2_match = abs(subtotal_cal_line_subtotal - subtotal) < tolerance

    isValid = False
    if strategy1_match:
        logger.debug("✓ Validation passed using Strategy 1 (quantity * rate)")
        isValid = True
    if strategy2_match:
        logger.debug("✓ Validation passed using Strategy 2 (line subtotals from PDF)")
        isValid = True
    else:
        logger.debug("✗ Validation failed - neither strategy matched")
        isValid = False

    return isValid
