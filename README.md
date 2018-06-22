# Yahoo Stock quote loader #

Pull stock data from yahoo finance into a sqlite3 database.

## Features ##

* store open, high, low, close, volume values
* download stock data from yahoo finance
* optimized update of database values
* watchlist table


## Create a new database ##

creates a new database and add a watchlist with some entries

./create_db


## Fetch Intial Values ##

Update all watchlist entries from starting date until now

python yalo.py --range '2013-01-01:'


## Plot Values ##

python yaplot.py --symbol 'RWE.DE' --range '2016-01-01:'


## Update Database ##

automatic database update is done by calling:

python yalo.py

the internal watchlist will be evaluated using the recent timestamp of symbols


