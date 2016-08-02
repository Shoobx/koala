# cython: profile=True

from __future__ import division
from itertools import izip
import collections
import re
# import numpy as np

ASCII = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# source: https://github.com/dgorissen/pycel/blob/master/src/pycel/excelutil.py

ROW_RANGE_RE = re.compile(r"(\$?[1-9][0-9]{0,6}):(\$?[1-9][0-9]{0,6})$")
COL_RANGE_RE = re.compile(r"(\$?[A-Za-z]{1,3}):(\$?[A-Za-z]{1,3})$")
CELL_REF_RE = re.compile(r"(\$?[A-Za-z]{1,3})(\$?[1-9][0-9]{0,6})$")

# We might need to test these util functions

def is_range(address):
    if isinstance(address, Exception):
        return address
    return address.find(':') > 0

def split_range(rng):
    if rng.find('!') > 0:
        start,end = rng.split(':')
        if start.find('!') > 0:
            sh,start = start.split("!")
        if end.find('!') > 0:
            sh,end = end.split("!")
    else:
        sh = None
        start,end = rng.split(':')
    
    return sh,start,end
        
def split_address(address):
    sheet = None
    if address.find('!') > 0:
        sheet,address = address.split('!')
    
    #ignore case
    address = address.upper()
    
    # regular <col><row> format    
    if re.match('^[A-Z\$]+[\d\$]+$', address):
        col,row = filter(None,re.split('([A-Z\$]+)',address))
    # R<row>C<col> format
    elif re.match('^R\d+C\d+$', address):
        row,col = address.split('C')
        row = row[1:]
    # R[<row>]C[<col>] format
    elif re.match('^R\[\d+\]C\[\d+\]$', address):
        row,col = address.split('C')
        row = row[2:-1]
        col = col[2:-1]
    else:
        raise Exception('Invalid address format ' + address)
    
    return (sheet,col,row)

resolve_range_cache = {}
def resolve_range(rng, should_flatten = False, sheet=''):
    
    # print 'RESOLVE RANGE splitting', rng
    sh, start, end = split_range(rng)
    
    if sh and sheet:
        if sh != sheet:
            raise Exception("Mismatched sheets %s and %s" % (sh,sheet))
        else:
            sheet += '!'
    elif sh and not sheet:
        sheet = sh + "!"
    elif sheet and not sh:
        sheet += "!"
    else:
        pass

    if rng+str(should_flatten)+sheet in resolve_range_cache:
        return resolve_range_cache[rng+str(should_flatten)+sheet]

    # single cell, no range
    if not is_range(rng):  return ([sheet + rng],1,1)

    sh, start_col, start_row = split_address(start)
    sh, end_col, end_row = split_address(end)
    start_col_idx = col2num(start_col)
    end_col_idx = col2num(end_col);

    start_row = int(start_row)
    end_row = int(end_row)

    nb_row = end_row - start_row + 1
    nb_col = end_col_idx - start_col_idx + 1

    # r = np.array([range(start_row, end_row + 1),]*nb_col, dtype='a5').T
    # c = num2col_vec(np.array([range(start_col_idx, end_col_idx + 1),]*nb_row))
    # if len(sheet)>0:
    #     s = np.chararray((nb_row, nb_col), itemsize=len(sheet))
    #     s[:] = sheet
    #     c = np.core.defchararray.add(s, c)
    # B = np.core.defchararray.add(c, r)

    
    # if start_col == end_col:
    #     data = B.T.tolist()[0]
    #     return data, len(data), 1
    # elif start_row == end_row:
    #     data = B.tolist()[0]
    #     return data, 1, len(data)
    # else:
    #     if should_flatten:
    #         return B.flatten().tolist(), 1, nb_col*nb_row
    #     else:
    #         return B.tolist(), nb_row, nb_col

    # single column
    if  start_col == end_col:
        nrows = end_row - start_row + 1
        data = [ "%s%s%s" % (s,c,r) for (s,c,r) in zip([sheet]*nrows,[start_col]*nrows,range(start_row,end_row+1))]
        BB = data,len(data),1
    
    # single row
    elif start_row == end_row:
        ncols = end_col_idx - start_col_idx + 1
        data = [ "%s%s%s" % (s,num2col(c),r) for (s,c,r) in zip([sheet]*ncols,range(start_col_idx,end_col_idx+1),[start_row]*ncols)]
        BB = data,1,len(data)
    
    # rectangular range
    else:
        cells = []
        for r in range(start_row,end_row+1):
            row = map(lambda c: sheet + num2col(c) + str(r), range(start_col_idx,end_col_idx+1))
            cells.append(row)
    
        if should_flatten:
            # flatten into one list
            l = list(flatten(cells, only_lists = True))
            BB = l,1,len(l)
        else:
            BB = cells, len(cells), len(cells[0])

    resolve_range_cache[rng+str(should_flatten)+sheet] = BB
    return BB

col2num_cache = {}
# e.g., convert BA -> 53
def col2num(col):
    if col in col2num_cache:
        return col2num_cache[col]
    if not col:
        raise Exception("Column may not be empty")
    
    tot = 0
    for i,c in enumerate([c for c in col[::-1] if c != "$"]):
        if c == '$': continue
        tot += (ord(c)-64) * 26 ** i

    col2num_cache[col] = tot
    return tot

# convert back
num2col_cache = {}

def num2col(num):
    if num in num2col_cache:
        return num2col_cache[num]
    if num < 1:
        raise Exception("Number must be larger than 0: %s" % num)

    s = ''
    q = num
    while q > 0:
        (q,r) = divmod(q,26)
        if r == 0:
            q = q - 1
            r = 26
        s = ASCII[r-1] + s

    num2col_cache[num] = s
    return s

# num2col_vec = np.vectorize(num2col)

def address2index(a):
    sh,c,r = split_address(a)
    return (col2num(c),int(r))

def index2addres(c,r,sheet=None):
    return "%s%s%s" % (sheet + "!" if sheet else "", num2col(c), r)

def get_linest_degree(excel,cl):
    # TODO: assumes a row or column of linest formulas & that all coefficients are needed

    sh,c,r,ci = cl.address_parts()
    # figure out where we are in the row

    # to the left
    i = ci - 1
    while i > 0:
        f = excel.get_formula_from_range(index2addres(i,r))
        if f is None or f != cl.formula:
            break
        else:
            i = i - 1
        
    # to the right
    j = ci + 1
    while True:
        f = excel.get_formula_from_range(index2addres(j,r))
        if f is None or f != cl.formula:
            break
        else:
            j = j + 1
    
    # assume the degree is the number of linest's
    degree =  (j - i - 1) - 1  #last -1 is because an n degree polynomial has n+1 coefs

    # which coef are we (left most coef is the coef for the highest power)
    coef = ci - i 

    # no linests left or right, try looking up/down
    if degree == 0:
        # up
        i = r - 1
        while i > 0:
            f = excel.get_formula_from_range("%s%s" % (c,i))
            if f is None or f != cl.formula:
                break
            else:
                i = i - 1
            
        # down
        j = r + 1
        while True:
            f = excel.get_formula_from_range("%s%s" % (c,j))
            if f is None or f != cl.formula:
                break
            else:
                j = j + 1

        degree =  (j - i - 1) - 1
        coef = r - i
    
    # if degree is zero -> only one linest formula -> linear regression -> degree should be one
    return (max(degree,1),coef) 

def flatten(l, only_lists = False):
    instance = list if only_lists else collections.Iterable

    for el in l:
        if isinstance(el, instance) and not isinstance(el, basestring):
            for sub in flatten(el, only_lists = only_lists):
                yield sub
        else:
            yield el

def uniqueify(seq):
    seen = set()
    seen_add = seen.add
    return [ x for x in seq if x not in seen and not seen_add(x)]

def is_number(s): # http://stackoverflow.com/questions/354038/how-do-i-check-if-a-string-is-a-number-float-in-python
    try:
        float(s)
        return True
    except:
        return False

def is_leap_year(year):
    if not is_number(year):
        raise TypeError("%s must be a number" % str(year))
    if year <= 0:
        raise TypeError("%s must be strictly positive" % str(year))

    # Watch out, 1900 is a leap according to Excel => https://support.microsoft.com/en-us/kb/214326
    return (year % 4 == 0 and year % 100 != 0 or year % 400 == 0) or year == 1900

def get_max_days_in_month(month, year):
    if not is_number(year) or not is_number(month):
        raise TypeError("All inputs must be a number")
    if year <= 0 or month <= 0:
        raise TypeError("All inputs must be strictly positive")

    if month in (4, 6, 9, 11):
        return 30
    elif month == 2:
        if is_leap_year(year):
            return 29
        else:
            return 28
    else:
        return 31

def normalize_year(y, m, d):
    if m <= 0:
        y -= int(abs(m) / 12 + 1)
        m = 12 - (abs(m) % 12)
        normalize_year(y, m, d)
    elif m > 12:
        y += int(m / 12)
        m = m % 12

    if d <= 0:
        d += get_max_days_in_month(m, y)
        m -= 1
        y, m, d = normalize_year(y, m, d)

    else:
        if m in (4, 6, 9, 11) and d > 30:
            m += 1
            d -= 30
            y, m, d = normalize_year(y, m, d)
        elif m == 2:
            if (is_leap_year(y)) and d > 29:
                m += 1
                d -= 29
                y, m, d = normalize_year(y, m, d)
            elif (not is_leap_year(y)) and d > 28:
                m += 1
                d -= 28
                y, m, d = normalize_year(y, m, d)
        elif d > 31:
            m += 1
            d -= 31
            y, m, d = normalize_year(y, m, d)

    return (y, m, d)

def date_from_int(nb):
    if not is_number(nb):
        raise TypeError("%s is not a number" % str(nb))

    # origin of the Excel date system
    current_year = 1900
    current_month = 0
    current_day = 0

    while(nb > 0):
        if not is_leap_year(current_year) and nb > 365:
            current_year += 1
            nb -= 365
        elif is_leap_year(current_year) and nb > 366:
            current_year += 1
            nb -= 366
        else:
            current_month += 1
            max_days = get_max_days_in_month(current_month, current_year)
            
            if nb > max_days:
                nb -= max_days
            else:
                current_day = nb
                nb = 0

    return (current_year, current_month, current_day)

def criteria_parser(criteria):

    if is_number(criteria):
        def check(x):
            return x == criteria #and type(x) == type(criteria)
    elif type(criteria) == str:
        search = re.search('(\W*)(.*)', criteria.lower()).group
        operator = search(1)
        value = search(2)
        value = float(value) if is_number(value) else str(value)

        if operator == '<':
            def check(x):
                if not is_number(x):
                    raise TypeError('excellib.countif() doesnt\'t work for checking non number items against non equality')
                return x < value
        elif operator == '>':
            def check(x):
                if not is_number(x):
                    raise TypeError('excellib.countif() doesnt\'t work for checking non number items against non equality')
                return x > value
        elif operator == '>=':
            def check(x):
                if not is_number(x):
                    raise TypeError('excellib.countif() doesnt\'t work for checking non number items against non equality')
                return x >= value
        elif operator == '<=':
            def check(x):
                if not is_number(x):
                    raise TypeError('excellib.countif() doesnt\'t work for checking non number items against non equality')
                return x <= value
        elif operator == '<>':
            def check(x):
                if not is_number(x):
                    raise TypeError('excellib.countif() doesnt\'t work for checking non number items against non equality')
                return x != value
        else:
            def check(x):
                return x == criteria
    else:
        raise Exception('Could\'t parse criteria %s' % criteria)

    return check


def find_corresponding_index(list, criteria):

    # parse criteria
    check = criteria_parser(criteria)

    valid = []

    for index, item in enumerate(list):
        if check(item):
            valid.append(index)

    return valid

def check_length(range1, range2):
    
    if len(range1.values) != len(range2.values):
        raise ValueError('Ranges don\'t have the same size')
    else:
        return range2

def extract_numeric_values(*args):
    values = []

    for arg in args:
        if isinstance(arg, collections.Iterable) and type(arg) != list and type(arg) != tuple: # does not work fo other Iterable than RangeCore, but can t import RangeCore here for circular reference issues
            for x in arg.values:
                if is_number(x) and type(x) is not bool: # excludes booleans from nested ranges
                    values.append(x)
        elif type(arg) is tuple or type(arg) is list:
            for x in arg: 
                if is_number(x) and type(x) is not bool: # excludes booleans from nested ranges
                    values.append(x)
        elif is_number(arg):
            values.append(arg)

    return values



if __name__ == '__main__':
    pass
    print resolve_range("Cashflow!L76:DG76")
    print resolve_range("B1:D1")
    print resolve_range("B10:B13")
    # print resolve_range("A1:AC3", should_flatten=True)
    # import cProfile
    # cProfile.run('resolve_range("A1:DF30")')
    # import timeit
    # print timeit.timeit('resolve_range("A1:DF30")', number=100, setup="from __main__ import resolve_range")



















