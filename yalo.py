#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Yahoo Stock Quote Loader

python yalo.py --symbol 'RWE.DE' --range '2011-01-30:'

'''

__version__ = '1.0.0'
__author__ = 'Joerg Dentler'
__email__ = 'Joerg.Dentler@gmx.net'



import csv, io, requests, datetime, time, re, sys, os
import dateutil.parser
import sqlite3

from optparse import OptionParser


VERSION = '%prog - version 1.0.0'
USAGE = '''usage: %prog [parameter]

for example:
./%prog --symbol 'RWE.DE' --range '2011-01-30:'
'''

def createParser():
  parser = OptionParser(version=VERSION, usage=USAGE)

  parser.add_option(
    '--database',
    dest='database',
    default="stock_quotes.db",
    help='Database path',
    )

  parser.add_option(
    '--symbol',
    dest='symbol',
    help='Stock symbol',
    )

  parser.add_option(
    '--range',
    type='string',
    help='time range as iso YYYY-MM-DD:YYYY-MM-DD',
    dest='range',
    )

  return parser



class Loader(object):
    '''
    Stock Quote Loader
    '''

    def __init__(self, db):
        assert os.path.exists(db)
        self.db = sqlite3.connect(db)

    def split_crumb_store(self, v):
        return v.split(':')[2].strip('"')

    def find_crumb_store(self, lines):
        # Looking for
        # ,"CrumbStore":{"crumb":"9q.A4D1c.b9
        for l in lines:
            if re.findall(r'CrumbStore', l):
                return l
        assert False, "Did not find CrumbStore"

    def get_cookie_value(self, r):
        return {'B': r.cookies['B']}

    def get_page_data(self, symbol):
        url = "https://finance.yahoo.com/quote/%s/?p=%s" % (symbol, symbol)
        r = requests.get(url)
        cookie = self.get_cookie_value(r)
        # Code to replace possible \u002F value
        # ,"CrumbStore":{"crumb":"FWP\u002F5EFll3U"
        # FWP\u002F5EFll3U
        lines = r.content.decode('unicode-escape').strip(). replace('}', '\n')
        return cookie, lines.split('\n')

    def get_cookie_crumb(self, symbol):
        cookie, lines = self.get_page_data(symbol)
        crumb = self.split_crumb_store(self.find_crumb_store(lines))
        return cookie, crumb

    def __fetch_range(self, symbol, range):
        r = [ int(time.mktime(range[0].timetuple())),
              int(time.mktime(range[1].timetuple())) ]
        cookie, crumb = self.get_cookie_crumb(symbol)
        url = "https://query1.finance.yahoo.com/v7/finance/download/%s?period1=%s&period2=%s&interval=1d&events=history&crumb=%s" % \
            (symbol, repr(r[0]), repr(r[1]), crumb)
        response = requests.get(url, cookies=cookie)
        text = response.iter_lines()
        self.csv = csv.reader(text, delimiter=',')
        return self.write(symbol)

    def insert(self, symbol, v):
        '''
        insert into db
        symbol TEXT NOT NULL,
        date DATE NOT NULL,
        open REAL,
        high REAL,
        low REAL,
        close REAL NOT NULL,
        volume REAL,
        '''
        sql = """INSERT OR REPLACE INTO stock_quotes VALUES (%s, %s, %s, %s, %s, %s, %s);
              """  % (
              "\"" + symbol + "\"",
              self.ts(v[0]),
              "\"" + v[1] + "\"",
              "\"" + v[2] + "\"",
              "\"" + v[3] + "\"",
              "\"" + v[4] + "\"",
              "\"" + v[6] + "\"")

        cursor = self.db.cursor()
        cursor.execute(sql)

    def ts(self, tss):
        t = datetime.datetime.strptime(tss, "%Y-%m-%d")
        return "\'" + t.isoformat(' ') + "\'"

    def write(self, symbol):
        '''
        write csv dataset into database

        ['Date', 'Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
        ['2018-01-29', 'null', 'null', 'null', 'null', 'null', 'null']
        ['2018-01-30', '16.500000', '16.580000', '16.184999', '16.184999', '15.806137', '8155615']
        '''
        r = 0
        first_row = True
        for row in self.csv:
            if not first_row and row[1] != 'null':
                self.insert(symbol, row)
                r += 1
            first_row = False;
        self.db.commit()
        if r:
            print("%s - %d rows written" % (symbol, r))
        return r

    def get_symbols(self):
        sql = "select distinct symbol from watchlist;"
        cursor = self.db.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        assert result, "No symbol data"
        symbols = []
        for s in result:
            symbols.append(s[0])
        return symbols

    def get_recent_date(self, symbol):
        sql = "select distinct date from stock_quotes where symbol=\'%s\'\
         order by date desc;" % (symbol)
        cursor = self.db.cursor()
        cursor.execute(sql)
        r = cursor.fetchone()
        if not r:
            return None
        ts = dateutil.parser.parse(r[0])
        #print("%s - recent val from %s" % (symbol, ts.isoformat(' ')))
        return ts

    def quotes_since(self, symbol, since):
        sql = "select distinct count(date) from stock_quotes where symbol=\'%s\'\
         and date >= %s order by date desc;" % (symbol, self.ts(since))
        cursor = self.db.cursor()
        cursor.execute(sql)
        r = cursor.fetchone()
        return int(r[0]) if r else None

    def get_range(self, symbol, range = None):
        assert symbol
        if range:
            ts = range.split(":")
            assert len(ts) == 2
            t1 = datetime.datetime.strptime(ts[0], "%Y-%m-%d")
            t2 = datetime.datetime.strptime(ts[1], "%Y-%m-%d") if ts[1] else \
                datetime.datetime.combine(datetime.date.today(), datetime.time())
            return [t1, t2]
        else:
            t1 = self.get_recent_date(symbol)
            assert t1, "No data for " % (symbol)
            t2 = datetime.datetime.combine(datetime.date.today(), datetime.time())
            return [t1, t2]

    def fetch_range(self, symbol, range):
        if range[0] == range[1]:
            return False
        t1 = self.get_recent_date(symbol)
        if not self.__fetch_range(symbol, range):
            return False
        t2 = self.get_recent_date(symbol)
        return (t1 is None and t2 is not None) or (t2 > t1)

    def fetch(self, symbol = None, r = None):
        if symbol:
            return self.fetch_range(symbol, self.get_range(symbol, r))
        else:
            rv = False
            for s in self.get_symbols():
                print("fetch: %s" % (s))
                if self.fetch_range(s, self.get_range(s, r)):
                    rv = True
            # at least one value transmitted
            return rv


if __name__ == '__main__':
    parser = createParser()
    (options, args) = parser.parse_args()
    loader = Loader(options.database)
    if not loader.fetch(options.symbol, options.range):
        sys.exit(2)


