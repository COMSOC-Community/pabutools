from typing import List, Tuple

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
