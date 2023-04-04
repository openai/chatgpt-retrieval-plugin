from typing import Optional, List

import arrow


def to_unix_timestamp(date_str: str) -> int:
    """
    Convert a date string to a unix timestamp (seconds since epoch).

    Args:
        date_str: The date string to convert.

    Returns:
        The unix timestamp corresponding to the date string.

    If the date string cannot be parsed as a valid date format, returns the current unix timestamp and prints a warning.
    """
    # Try to parse the date string using arrow, which supports many common date formats
    try:
        date_obj = arrow.get(date_str)
        return int(date_obj.timestamp())
    except arrow.parser.ParserError:
        # If the parsing fails, return the current unix timestamp and print a warning
        print(f"Invalid date format: {date_str}")
        return int(arrow.now().timestamp())


def validate_date_str(date_str: str, formats: Optional[List[str]] = None) -> bool:
    """
    Validate if a date string is actually a date object or not.

    Args:
        date_str: The date string to convert.

    Returns:
        True if date_str is valid else False
        :param date_str:Delete for the end_date
        :param formats: List of formats againsts which we want to validate the date
    """
    try:
        if not formats:
            arrow.get(date_str)
            return True
        for date_format in formats:
            arrow.get(date_str, date_format)
        return True
    except arrow.parser.ParserError as e:
        raise Exception(f"Date parsing exception happened {e}")
