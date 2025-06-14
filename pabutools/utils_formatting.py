from typing import List, Tuple

"""
Utility function for internal logging: formats rows into an aligned table-style string,
to improve readability in debug logs of the PB-EAR algorithm.

Based on the paper:
"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
Date: 2025-04-23
"""


def format_table(headers: List[str], rows: List[Tuple[str, str, str, str]]) -> str:
    """
    Format a table of rows with headers into a clean aligned string.

    Parameters
    ----------
    headers : list of str
        Column titles.
    rows : list of tuples of str
        Each tuple corresponds to a row.

    Returns
    -------
    str
        A formatted string representing the table.
    """
    col_widths = [max(len(str(row[i])) for row in [headers] + rows) for i in range(len(headers))]
    header_line = " | ".join(f"{headers[i]:<{col_widths[i]}}" for i in range(len(headers)))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    lines = [header_line, separator]
    for row in rows:
        lines.append(" | ".join(f"{row[i]:<{col_widths[i]}}" for i in range(len(headers))))
    return "\n".join(lines)
