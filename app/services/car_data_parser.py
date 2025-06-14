from typing import Tuple, Optional

class CarDataParser:
    @staticmethod
    def parse_text_for_price(content_element) -> Tuple[Optional[int], Optional[str]]:
        text = content_element.get_text(strip=True) if content_element else None
        if text and "=" in text:
            text = text.split('=')[0].strip()

        if text is None:
            return None, None

        text = text.replace("'", "").replace(",", "").replace(".", "").strip()

        currency = None
        if '$' in text:
            currency = '$'
            text = text.replace('$', '').strip()
        elif 'USD' in text:
            currency = 'USD'
            text = text.replace('USD', '').strip()
        elif '€' in text:
            currency = '€'
            text = text.replace('€', '').strip()
        elif 'EUR' in text:
            currency = 'EUR'
            text = text.replace('EUR', '').strip()
        elif 'грн' in text.lower():
            currency = 'грн'
            text = text.lower().replace('грн', '').strip()
        elif '₴' in text:
            currency = '₴'
            text = text.replace('₴', '').strip()

        try:
            price = ''.join(c for c in text if c.isdigit())
            price = int(price) if price else None
        except ValueError:
            price = None

        return price, currency

    @staticmethod
    def parse_text_for_year(content_element) -> Optional[int]:
        year_text = content_element.get_text(strip=True) if content_element else None
        if year_text and ":" in year_text:
            digits = ''.join(c for c in year_text if c.isdigit())
            return int(digits) if digits else None
        elif year_text and " " in year_text:
            splitted_text = year_text.split(' ')
            digits = ''.join(c for c in splitted_text if c.isdigit() and len(c) == 4)
            return int(digits) if digits else None
        elif year_text and year_text.isdigit():
            return int(year_text)
        return None

    @staticmethod
    def parse_text_for_views(content_element) -> Optional[int]:
        text = content_element.get_text(strip=True)
        if content_element and len(content_element.contents) > 1 and " " not in text:
            digits = ''.join(c for c in text if c.isdigit())
            return int(digits) if digits else None
        elif text and " " in text:
            digits = ''.join(c for c in text if c.isdigit())
            return int(digits) if digits else None
        return int(text.strip()) if text else None

    @staticmethod
    def parse_text_for_mileage(content_element) -> Tuple[Optional[int], Optional[str]]:
        mileage_text = content_element.get_text(strip=True) if content_element else None
        if mileage_text and ":" in mileage_text:
            mileage_text = mileage_text.split(':')[1].strip()

        if mileage_text is None:
            return None, None

        mileage_text = mileage_text.replace("'", "").replace(",", "").strip()

        unit = None
        multiply_by_1000 = False
        if 'км' in mileage_text.lower():
            unit = 'км'
            if 'тис' in mileage_text.lower():
                multiply_by_1000 = True
                mileage_text = mileage_text.lower().replace('км', '').replace('тис.', '').replace('тис', '').replace('пробіг', '').strip()

        try:
            mileage = ''.join(c for c in mileage_text if c.isdigit())
            if mileage:
                mileage = int(mileage) * 1000 if multiply_by_1000 else int(mileage)
            else:
                mileage = None
        except ValueError:
            mileage = None

        return mileage, unit