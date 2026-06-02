"""
Module introducing all the functions used to handle fractions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gmpy2 import mpq

if TYPE_CHECKING:
    from pabutools.utils import Numeric

GMPY_FRAC = "gmpy2"
"""
Value of the `FRACTION` constant when gumpy2 fractions are to be used. 
"""

FLOAT_FRAC = "float"
"""
Value of the `FRACTION` constant when float fractions are to be used. 
"""

FRACTION = GMPY_FRAC
"""
Constant describing which module to use for computing fractions. It can either be "gmpy2" or "float". The default is 
"gmpy2".
"""


def frac(*arg: Numeric) -> Numeric:
    """
    Returns a fraction instantiated from the module defined by the `FRACTION` constant. If more than two numbers are
    provided, an error is raised.

    Parameters
    ----------
        Numeric
            One or two numbers.

    Returns
    -------
        Numeric
            The fraction.
    """
    # Normalize numpy scalars (and similar) to plain Python ints/floats so that
    # gmpy2.mpq and arithmetic operators accept them without errors.
    normalized = []
    for a in arg:
        try:
            a = a.item()
        except AttributeError:
            pass
        normalized.append(a)
    arg = tuple(normalized)

    if len(arg) == 1:
        if FRACTION == GMPY_FRAC:
            return mpq(arg[0])
        elif FRACTION == FLOAT_FRAC:
            return arg[0]
        else:
            raise ValueError(
                f"The current value of pabutools.fractions.FRACTION '{FRACTION}' is invalid, it needs to be in "
                "[gmpy2, float]."
            )
    elif len(arg) == 2:
        if FRACTION == GMPY_FRAC:
            return mpq(arg[0], arg[1])
        elif FRACTION == FLOAT_FRAC:
            return arg[0] / arg[1]
        else:
            raise ValueError(
                f"The current value of pabutools.fractions.FRACTION '{FRACTION}' is invalid, it needs to be in "
                "[gmpy2, float]."
            )
    raise ValueError("frac can only take 1 or 2 arguments")


def str_as_frac(s: str) -> Numeric:
    """
    Converts a string to a fraction instantiated from the module defined by the `FRACTION` constant.

    Parameters
    ----------
        s: str
            A string representing a number.

    Returns
    -------
        Numeric
            The fraction.
    """
    if FRACTION == GMPY_FRAC:
        return mpq(s)
    elif FRACTION == FLOAT_FRAC:
        return float(s)
    else:
        raise ValueError(f"The `FRACTION` constant has an unknown value: {FRACTION}")
