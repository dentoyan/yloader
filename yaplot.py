#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Stock Quote Plotter

python yaplot.py --symbol 'RWE.DE' --range '2016-01-30:'

'''

__version__ = '1.0.0'
__author__ = 'Joerg Dentler'
__email__ = 'Joerg.Dentler@gmx.net'

import os.path, sqlite3, sys, os, datetime
import dateutil.parser

from optparse import OptionParser

import matplotlib.pyplot as plt
import matplotlib.dates as mdates


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
    '--offset',
    type='int',
    help='offset',
    dest='offset',
    )

  parser.add_option(
    '--range',
    type='string',
    help='time range as iso YYYY-MM-DD:YYYY-MM-DD',
    dest='range',
    )

  return parser



class Plotter(object):
    '''
    Stock Quote Plotter
    '''

    def __init__(self, db):
        assert os.path.exists(db)
        self.db = sqlite3.connect(db)

    def fetch(self, symbol, r = None):
        '''
        fetch data
        '''
        self.symbol = symbol
        range = self.get_range(r)
        sql = "SELECT date, low, high FROM stock_quotes WHERE \
                symbol=\'%s\' AND date BETWEEN %s AND %s  \
                order by date ASC;" % (symbol, self._ts(range[0]), self._ts(range[1]))
        cursor = self.db.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        assert result, "No data"
        self.x = []
        self.y = [ [], [] ]
        for r in result:
            ts = dateutil.parser.parse(r[0])
            self.x.append(ts)
            self.y[0].append(r[1])
            self.y[1].append(r[2])


    def fetch_offset(self, symbol, offset):
        '''
        fetch data
        '''
        self.symbol = symbol
        sql = "SELECT date, low, high FROM (\
                SELECT * from stock_quotes WHERE \
                symbol=\'%s\' order by date DESC LIMIT %d) T1\
                ORDER BY date;" % (symbol, offset)
        cursor = self.db.cursor()
        cursor.execute(sql)
        result = cursor.fetchall()
        assert result, "No data"
        self.x = []
        self.y = [ [], [] ]
        for r in result:
            ts = dateutil.parser.parse(r[0])
            self.x.append(ts)
            self.y[0].append(r[1])
            self.y[1].append(r[2])

    def plot(self):
        fig, ax = plt.subplots()
        plt.grid()
        #plt.xlabel('t')
        plt.title(self.symbol)
        plt.plot(self.x, self.y[1], label="High")
        plt.plot(self.x, self.y[0], label="Low")
        plt.legend(loc=2)
        fig.autofmt_xdate()
        xfmt = mdates.DateFormatter('%d-%m-%y')
        ax.xaxis.set_major_formatter(xfmt)
        plt.show()
        plt.clf()


    def _ts(self, t):
        return "\'" + t.isoformat(' ') + "\'"


    DEFAULT_RANGE = 100

    def get_range(self, range = None):
        if range:
            ts = range.split(":")
            assert len(ts) == 2
            t1 = datetime.datetime.strptime(ts[0], "%Y-%m-%d")
            t2 = datetime.datetime.strptime(ts[1], "%Y-%m-%d") if ts[1] else \
                datetime.datetime.combine(datetime.date.today(), datetime.time())
            return [t1, t2]
        else:
            t2 = datetime.datetime.combine(datetime.date.today(), datetime.time())
            t1 = t2 - datetime.timedelta(days = self.DEFAULT_RANGE)
            return [t1, t2]


if __name__ == '__main__':
    parser = createParser()
    (options, args) = parser.parse_args()
    if not options.symbol:
        print('no stock symbol specified')
        sys.exit(1)
    p = Plotter(options.database)
    if options.offset:
        p.fetch_offset(options.symbol, options.offset)
    else:
        p.fetch(options.symbol, options.range)
    p.plot()


