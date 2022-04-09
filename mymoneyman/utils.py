import decimal

def short_format_number(number: decimal.Decimal, decimals: int = 0) -> str:
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