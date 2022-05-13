import typing
import decimal
from PyQt5 import QtCore

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

        fmt = '{:.' + str(decimals) + 'f}'

        return fmt.format(number) + letter

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