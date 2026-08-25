#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_sqlite() {
    tmp=$(mktemp -d)
    cd "$tmp"
    echo '### Test of sqlite'
    for CMDSQL in sqlite sqlite3 ; do
	echo "Current command: $CMDSQL"
	rm -f sqltest.$CMDSQL
	# create database & table
	sql $CMDSQL:///sqltest.$CMDSQL "CREATE TABLE foo(n INT, t TEXT);"
	sql --list-tables $CMDSQL:///sqltest.$CMDSQL
	file sqltest.$CMDSQL | perl -pe 's/ version \d+//'
	sql $CMDSQL:///sqltest.$CMDSQL "INSERT INTO foo VALUES(1,'Line 1');"
	sql $CMDSQL:///sqltest.$CMDSQL "INSERT INTO foo VALUES(2,'Line 2');"
	sql $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -n $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -s '.' $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -n -s '.' $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -s '' $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -s '	' $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql --html $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql -n --html $CMDSQL:///sqltest.$CMDSQL "SELECT * FROM foo;"
	sql --dbsize $CMDSQL:///sqltest.$CMDSQL
	sql $CMDSQL:///sqltest.$CMDSQL "DROP TABLE foo;"
	sql --dbsize $CMDSQL:///sqltest.$CMDSQL
	rm -f sqltest.$CMDSQL
    done
}

par_influx() {
    echo '### Test of influx'
    (
	# create database & table
	sql influx:/// "CREATE DATABASE parallel;"
	sql --show-databases influx:/// | grep -v $(whoami)
	# insert
	(echo INSERT cpu,host=serverA,region=us_west value=0.64;
	 echo INSERT cpu,host=serverA,region=us_west value=0.65;
	 echo 'select * from cpu' ) |
	    sql influx:///parallel
	sql --show-tables influx:///parallel | grep parallel;
	sql influx:///parallel 'SELECT * FROM cpu;'
	sql influx:///parallel 'SELECT "host", "region", "value" FROM "cpu"'
	sql --pretty influx:///parallel 'SELECT * FROM cpu;'
	sql --json influx:///parallel 'SELECT * FROM cpu;'
	sql --dbsize influx:///parallel
	sql -s . influx:///parallel 'SELECT * FROM cpu;'
	sql --html influx:///parallel 'SELECT * FROM cpu;'
	sql influx:///parallel 'drop database parallel'
    ) | perl -pe 's/\d/0/g; s/sql line (\d+)./sql line 000./
'
}


export -f $(compgen -A function | grep par_)
compgen -A function | G "$@" par_ | sort |
    parallel -j0 --tag -k --joblog +/tmp/jl-`basename $0` '{} 2>&1'
