import re
import structlog
from app.config import settings

logger = structlog.get_logger(__name__)

BENGALI_TO_ENGLISH_DIGITS = {
    '০': '0', '১': '1', '২': '2', '৩': '3', '৪': '4',
    '৫': '5', '৬': '6', '৭': '7', '৮': '8', '৯': '9'
}

def convert_bengali_numerals(text: str) -> str:
    res = []
    for char in str(text):
        res.append(BENGALI_TO_ENGLISH_DIGITS.get(char, char))
    return "".join(res)

def normalize_to_e164(raw_number: str, default_country_code: str = None) -> str:
    """
    Normalizes a raw phone number string (potentially containing Bengali numerals or local formatting)
    to standard E.164 international format (e.g., +8801700000000).
    """
    if not raw_number:
        return ""
        
    if default_country_code is None:
        default_country_code = getattr(settings, "default_country_code", "+880")
    if not default_country_code.startswith("+"):
        default_country_code = "+" + default_country_code

    # 1. Convert Bengali numbers to ASCII digits
    converted = convert_bengali_numerals(raw_number)
    
    # 2. Extract leading plus (if any) and all digits
    has_plus = converted.strip().startswith("+")
    digits_only = re.sub(r'\D', '', converted)
    
    if not digits_only:
        logger.warning("normalize_to_e164_no_digits_found", raw=raw_number)
        return raw_number.strip()
        
    # 3. Apply normalization rules
    if has_plus:
        normalized = "+" + digits_only
    elif digits_only.startswith("880") and len(digits_only) == 13:
        normalized = "+" + digits_only
    elif digits_only.startswith("0"):
        # Local format (e.g., 017... -> strip leading zero and prepend default country code)
        normalized = default_country_code + digits_only.lstrip("0")
    else:
        # Fallback: attach default country code if no prefix exists
        normalized = default_country_code + digits_only

    logger.debug("normalized_to_e164", raw=raw_number, normalized=normalized, default_cc=default_country_code)
    return normalized
