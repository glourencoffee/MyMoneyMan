import typing
import decimal
from PyQt5 import QtCore

def formatNumber(number: decimal.Decimal, decimals: int = 0, remove_trailing_zero: bool = False) -> str:
    """Returns the string representation of a number.
    
    This method exists because calling `str(number)` may return its
    representation in scientific notation.

    >>> str(decimal.Decimal('0.000000120'))
    '1.20E-7'
    >>> formatNumber(decimal.Decimal('0.000000120'), decimals=9)
    '0.000000120'
    >>> formatNumber(decimal.Decimal('0.000000120'), decimals=9, remove_trailing_zero=True)
    '0.00000012'
    """

    number_fmt = '{:.' + str(decimals) + 'f}'
    number_str = number_fmt.format(number)

    if remove_trailing_zero and number_str.find('.') != -1:
        return number_str.rstrip('0').rstrip('.')

    return number_str

def shortFormatNumber(number: decimal.Decimal, decimals: int = 0) -> str:
    thousands = 0

    n = abs(number)

    while n > 1000:
        n /= 1000
        thousands += 1
    
    thousands_letter = ('', 'K', 'M', 'B', 'T')

    try:
        letter = thousands_letter[thousands]
        number = number / (1000 ** thousands)

        return formatNumber(number, decimals) + letter

    except IndexError:
        return round(number, decimals)

def indexLocation(index: typing.Union[QtCore.QModelIndex, QtCore.QPersistentModelIndex],
                  extended: bool = False,
                  sep: str = ':'
) -> str:
    location = f'({index.row()}, {index.column()})'

    if index.isValid() and extended:
        parent_location = indexLocation(index.parent(), extended=True, sep=sep)
        
        return parent_location + sep + location
    
    return location

def makeRepr(cls: typing.Type[typing.Any], obj: typing.Dict[str, typing.Any]) -> str:
    s = f'<{cls.__name__}: '

    for k, v in obj.items():
        if isinstance(v, str):
            v = "'" + v + "'"
        else:
            v = repr(v)
        
        s += f'{k}={v} '

    return s.rstrip() + '>'