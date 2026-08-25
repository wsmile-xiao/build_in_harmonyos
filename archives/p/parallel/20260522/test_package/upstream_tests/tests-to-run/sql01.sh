#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

exec 2>&1

## Setup
# mysqlrootpass=${mysqlrootpass:-M-b+Ydjq4ejT4E}
# MYSQL_ADMIN_DBURL=mysql://root:$mysqlrootpass@/mysql
# sql $MYSQL_ADMIN_DBURL "drop user 'sqlunittest'@'localhost'"
# sql $MYSQL_ADMIN_DBURL DROP DATABASE sqlunittest;
# sql $MYSQL_ADMIN_DBURL CREATE DATABASE sqlunittest;
# sql $MYSQL_ADMIN_DBURL "CREATE USER 'sqlunittest'@'localhost' IDENTIFIED BY 'CB5A1FFFA5A';"
# sql $MYSQL_ADMIN_DBURL "GRANT ALL PRIVILEGES ON sqlunittest.* TO 'sqlunittest'@'localhost';"

export MYSQL_TEST_DBURL=mysql://tange:tange@/
export DBURL="$MYSQL_TEST_DBURL"

par_shebang-Y() {
    echo '### Test of #! -Y with file as input'
    shebang=/tmp/shebang-Y
    cat >"$shebang" <<EOF
#!/usr/local/bin/sql -Y $MYSQL_TEST_DBURL

SELECT 'Yes it does' AS 'Testing if -Y works';
EOF
    chmod 755 "$shebang"
    "$shebang"
}

par_shebang_file() {
    echo '### Test of #! --shebang with file as input'
    shebang=/tmp/shebang-file
    cat >"$shebang" <<EOF
#!/usr/local/bin/sql --shebang $MYSQL_TEST_DBURL

SELECT 'Yes it does' AS 'Testing if --shebang works';
EOF
    chmod 755 "$shebang"
    "$shebang"
}

par_sql_on_cmdline() {
    echo '### Test reading sql on command line'
    sql $MYSQL_TEST_DBURL "SELECT 'Yes it does' as 'Test reading SQL from command line';"
}

par_read_sql_from_file() {
    echo '### Test reading sql from file'
    unittest=/tmp/unittest.sql
    cat >"$unittest" <<EOF
DROP TABLE IF EXISTS unittest;
CREATE TABLE unittest (
          id INT,
          data VARCHAR(100)
        );
INSERT INTO unittest VALUES (1,'abc');
INSERT INTO unittest VALUES (3,'def');
SELECT 'Yes it does' as 'Test reading SQL from file works';
EOF
    sql $MYSQL_TEST_DBURL <"$unittest"
}

testtable() {
    tbl=$1
    cat <<EOF
    DROP TABLE IF EXISTS $tbl;
CREATE TABLE $tbl (
          id INT,
          data VARCHAR(100)
        );
INSERT INTO $tbl VALUES (1,'abc');
INSERT INTO $tbl VALUES (3,'def');
EOF
}
export -f testtable

par_dburl_user_password_host_port() {
    echo '### Test dburl with username password host port'
    (
	testtable userpasshost;
	echo "SELECT 'OK' as 'Test dburl with username password host port'";
    ) | sql mysql://tange:tange@localhost:3306/tange
}

par_sql_aliases() {
    echo "### Test .sql/aliases"
    mkdir -p ~/.sql
    echo :sqlunittest mysql://sqlunittest:CB5A1FFFA5A@localhost:3306/sqlunittest >> ~/.sql/aliases
    perl -i -ne '$seen{$_}++ || print' ~/.sql/aliases
    sql :sqlunittest "SELECT 'Yes it does' as 'Test if .sql/aliases works';"

    echo "### Test sql:sql::alias"
    sql sql:sql::sqlunittest "SELECT 'Yes it works' as 'Test sql:sql::alias';"
}

par__noheaders() {
    echo "### Test --noheaders --no-headers -n"
    testtable noheader | sql "$DBURL"
    sql -n "$DBURL" 'select * from noheader order by id' |
	parallel -k --colsep '\t' echo {2} {1}
    sql --noheaders "$DBURL" 'select * from noheader order by id' |
	parallel -k --colsep '\t' echo {2} {1}
    sql --no-headers "$DBURL" 'select * from noheader order by id' |
	parallel -k --colsep '\t' echo {2} {1}
}

par_sep() {
    echo "### Test --sep -s";
    sql --no-headers -s : pg:/// 'select 1,2' |
	parallel --colsep ':' echo {2} {1}
    sql --no-headers --sep : pg:/// 'select 1,2' |
	parallel --colsep ':' echo {2} {1}
}

par_passthrough() {
    echo "### Test --passthrough -p";
    testtable passthrough | sql "$DBURL"
    sql -p -H "$DBURL" 'select * from passthrough'
    echo
    sql --passthrough -H "$DBURL" 'select * from passthrough'
    echo
}

par_html() {
    echo "### Test --html";
    testtable html | sql "$DBURL"
    sql --html "$DBURL" 'select * from html'
    echo
}

par__listproc() {
    echo "### Test --show-processlist|proclist|listproc";
    # Take the minimum of 3 runs to avoid error counting
    # if one of the other jobs happens to be running    
    (
	sql --show-processlist "$DBURL" | wc -lw
	sql --show-processlist "$DBURL" | wc -lw
	sql --show-processlist "$DBURL" | wc -lw
    ) | sort | head -n1
    (
	sql --proclist "$DBURL" | wc -lw
	sql --proclist "$DBURL" | wc -lw
	sql --proclist "$DBURL" | wc -lw
    ) | sort | head -n1
    (
	sql --listproc "$DBURL" | wc -lw
	sql --listproc "$DBURL" | wc -lw
	sql --listproc "$DBURL" | wc -lw
    ) | sort | head -n1
}

par__dbsize() {
    echo "### Test --db-size --dbsize";
    sql --dbsize "$DBURL" | wc -w
    sql --db-size "$DBURL" | wc -w
}

par__tablesize() {
    echo "### Test --table-size --tablesize"
    sql --showtables "$DBURL" | grep TBL | parallel sql "$DBURL" drop table
    sql --tablesize "$DBURL" | wc -l
    sql --table-size "$DBURL" | wc -l
}

par_debug() {
    echo "### Test --debug"
    stdout sql --debug "$DBURL" "SELECT 'Yes it does' as 'Test if --debug works';" |
	replace_tmpdir |
	perl -pe 's:/...........sql:/tmpfile:g'
}

par_version() {
    echo "### Test --version -V"
    sql --version | wc
    sql -V | wc
}

par_retry() {
    echo "### Test -r - retry 3 times"
    stdout sql -r --debug pg://nongood@127.0.0.3:2227/ "SELECT 'This should fail 3 times';"
    echo "### Test --retries=s"
    stdout sql --retries=4 --debug pg://nongood@127.0.0.3:2227/ "SELECT 'This should fail 4 times';"
}

par_help() {
    echo "### Test --help -h"
    sql --help
    sql -h
}


export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 3000% -j0 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
