"""
Collection of util functions.
"""

from __future__ import annotations

from collections.abc import Iterable, Generator
from enum import Enum
from itertools import combinations, chain

from typing import Union

from gmpy2 import mpq

from pabutools.fractions import frac

Numeric = Union[int, float, mpq]
"""
Type for numeric values. Is the union of int, float and mpq fractions (from the gumpy2 package).
"""


def mean_generator(
    generator: Iterable[Numeric] | Iterable[tuple[Numeric, int]]
) -> Numeric:
    """
    Computes the mean of a sequence of numbers given as a generator. If the generator contains tuples, the first element
    is assumed to be the value and the second its multiplicity.

    Parameters
    ----------
        generator: Iterable[Numeric] | Iterable[tuple[Numeric, int]
            The generator.

    Returns
    -------
        Numeric
            The mean of the values.
    """
    n: int = 0
    mean: Numeric = 0
    for x in generator:
        multiplicity: int = 1
        value: Numeric = x
        if isinstance(x, tuple):
            value = x[0]
            multiplicity = x[1]
        for i in range(multiplicity):
            n += 1
            mean += frac(value - mean, n)
    return mean


def powerset(iterable: Iterable) -> Generator:
    """
    Returns a generator of all the subsets of a given iterable.

    Parameters
    ----------
        iterable: Iterable
            An iterable.

    Returns
    -------
        Generator
            A generator of all the subsets of the iterable.
    """
    s = list(iterable)
    return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))


def gini_coefficient(values: Iterable[Numeric]) -> Numeric:
    """
    Returns the Gini coefficient of the vector of values given as argument.

    Parameters
    ----------
        values: Iterable[Numeric]
            A vector of values.

    Returns
    -------
        Numeric
            The Gini coefficient.

    """
    all_nul: bool = True
    num_values: int = 0
    for v in values:
        if v < 0:
            raise ValueError(
                "Negative values not supported by gini coefficient implementation."
            )
        if all_nul and v > 0:
            all_nul = False
        num_values += 1
    if all_nul:
        return 0
    sorted_values: list[Numeric] = sorted(values)
    total_cum_sum: Numeric = 0
    for i, v in enumerate(sorted_values):
        total_cum_sum += v * (num_values - i)
    return frac(num_values + 1 - frac(2 * total_cum_sum, sum(values)), num_values)


def round_cmp(a: Numeric, b: Numeric, precision: int = 6) -> int:
    """
    Compares two numbers after rounding them to a specified precision.

    Parameters
    ----------
        a : Numeric
            The first number for comparison.
        b : Numeric
            The second number for comparison.
        precision : int, optional
            The number of decimal places to which the numbers should be rounded.
            Defaults to 6.

    Returns
    -------
        int
            A negative number if the rounded value of 'a' is less than the rounded value of 'b',
            0 if they are approximately equal after rounding,
            a positive number if the rounded value of 'a' is greater than the rounded value of 'b'.

    """
    return round(a, precision) - round(b, precision)


class DocEnum(Enum):
    """
    Enumeration with documentation of its members. Taken directly from
    `stack overflow <https://stackoverflow.com/questions/50473951/how-can-i-attach-documentation-to-members-of-a-python-enum/50473952#50473952>`_.
    """

    def __new__(cls, value, doc=None):
        self = object.__new__(cls)
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self


def format_table(headers: list[str], rows: list[tuple[str, str, str, str]]) -> str:
    """
    Format a table of rows with headers into a clean aligned string.

    Contributed by Vivian Umansky.

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
