#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# GNU Parallel SQL tests
# The tests must be able to run in parallel

export SQLITE=sqlite3:///%2Frun%2Fshm%2Fparallel.db
export PG=pg://`whoami`:`whoami`@localhost/`whoami`
export MYSQL=mysql://`whoami`:`whoami`@localhost/`whoami`
export CSV=csv:///%2Frun%2Fshm
export INFLUX=influx:///parallel

export DEBUG=false
rm -f /run/shm/parallel.db
mkdir -p /run/shm/csv

overlay_mysql() {
    # MySQL is rediculously slow: Force it to work in RAM
    sudo service mysql stop
    mysqldir=/var/lib/mysql
    upper=/dev/shm/mysql
    work=/dev/shm/mysql-work
    sudo umount $mysqldir 2>/dev/null
    mkdir -p $upper $work
    sudo mount -t overlay overlay -o lowerdir=$mysqldir,upperdir=$upper,workdir=$work $mysqldir
    sudo chown mysql:mysql $mysqldir
    sudo service mysql start
}

p_showsqlresult() {
    # print results stored in $SERVERURL/$TABLE
    SERVERURL=$1
    TABLE=$2
    sql $SERVERURL "select Host,Command,V1,V2,Stdout,Stderr from $TABLE order by seq;"
}

p_wrapper() {
    INNER=$1
    SERVERURL=$(eval echo $2)
    # Use a random table for each test
    TABLE=TBL$RANDOM
    DBURL=$SERVERURL/$TABLE
    T1=$(mktemp)
    T2=$(mktemp)
    # Run $INNER (all the par_* functions)
    eval "$INNER"
    echo Exit=$?
    # $INNER can start background processes - wait for those
    wait
    echo Exit=$?
    # For debugging show the tempfiles
    $DEBUG && sort -u "$T1" "$T2";
    rm "$T1" "$T2"
    p_showsqlresult $SERVERURL $TABLE
    # Drop the table if not debugging
    $DEBUG || sql $SERVERURL "drop table $TABLE;" >/dev/null 2>/dev/null
}

p_template() {
    # Run the jobs with both master and worker
    (
	# Make sure there is work to be done
	sleep 6;
	parallel --sqlworker $DBURL "$@" sleep .3\;echo >"$T1"
    ) &
    parallel  --sqlandworker $DBURL "$@" sleep .3\;echo ::: {1..5} ::: {a..e} >"$T2";
}

par_sqlandworker() {
    p_template
}

par_sqlandworker_lo() {
    p_template -S lo
}

par_sqlandworker_results() {
    p_template --results /tmp/out--sql
}

par_sqlandworker_linebuffer() {
    p_template --linebuffer
}

par_sqlandworker_tag() {
    p_template --tag
}

par_sqlandworker_linebuffer_tag() {
    p_template --linebuffer --tag
}

par_sqlandworker_compress_linebuffer_tag() {
    p_template --compress --linebuffer --tag
}

par_sqlandworker_unbuffer() {
    p_template -u
}

par_sqlandworker_total_jobs() {
    p_template echo {#} of '{=1 $_=total_jobs(); =};'
}

par_append() {
    parallel --sqlmaster  $DBURL sleep .3\;echo ::: {1..5} ::: {a..e} >"$T2";
    parallel --sqlmaster +$DBURL sleep .3\;echo ::: {11..15} ::: {A..E} >>"$T2";
    parallel --sqlworker  $DBURL sleep .3\;echo >"$T1"
}

par_shuf() {
    MD5=$(echo $SERVERURL | md5sum | perl -pe 's/(...).*/$1/')
    T=/tmp/parallel-bug49791-$MD5
    [ -e $T ] && rm -rf $T
    parallel_orig=$PARALLEL
    export PARALLEL="$parallel_orig --shuf --result $T"
    parallel --sqlandworker $DBURL sleep .3\;echo \
	     ::: {1..5} ::: {a..e} >"$T2";
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    unset PARALLEL
    wait;
    # Did it compute correctly?
    cat $T/1/*/*/*/stdout
    # Did it shuffle (Compare job table to non-shuffled)
    SHUF=$(sql $SERVERURL "select Host,Command,V1,V2,Stdout,Stderr from $TABLE order by seq;")
    export PARALLEL="$parallel_orig --result $T"
    parallel --sqlandworker $DBURL sleep .3\;echo \
	     ::: {1..5} ::: {a..e} >"$T2";
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    parallel --sqlworker    $DBURL sleep .3\;echo >"$T2" &
    unset PARALLEL
    wait;
    NOSHUF=$(sql $SERVERURL "select Host,Command,V1,V2,Stdout,Stderr from $TABLE order by seq;")
    DIFFSIZE=$(diff <(echo "$SHUF") <(echo "$NOSHUF") | wc -c)
    if [ $DIFFSIZE -gt 2500 ]; then
	echo OK: Diff bigger than 2500 char
    fi
    [ -e $T ] && rm -rf $T
    touch "$T1"
}

par_empty() {
    echo Do nothing: TBL99999 does not exist because it is not created
    true;
}

par_sql_joblog() {
    echo '### should only give a single --joblog heading'
    echo '### --sqlmaster/--sqlworker'
    parallel -k --joblog - --sqlmaster $DBURL --wait sleep .3\;echo ::: {1..5} ::: {a..e} |
	perl -pe 's/\d+\.\d+/999.999/g' | sort -n &
    sleep 0.5
    T=$(mktemp)
    parallel -k --joblog - --sqlworker $DBURL > "$T"
    wait
    # Needed because of race condition
    cat "$T"; rm "$T"
    echo '### --sqlandworker'
    parallel -k --joblog - --sqlandworker $DBURL sleep .3\;echo ::: {1..5} ::: {a..e} |
	perl -pe 's/\d+\.\d+/999.999/g' | sort -n
    # TODO --sqlandworker --wait
}

par_no_table() {
    echo 'bug #50018: --dburl without table dies'
    echo should default to table USERNAME
    parallel --sqlandworker $SERVERURL echo ::: OK
    echo $?
    parallel --sqlmaster $SERVERURL echo ::: OK
    echo $?
    parallel --sqlworker $SERVERURL
    echo $?
    # For p_wrapper to remove table
    parallel --sqlandworker $DBURL true ::: dummy ::: dummy
}

export -f $(compgen -A function | grep p_)
export -f $(compgen -A function | G par_ "$@")

# Run the DBURLs in parallel, but only one of the same DBURL at the same time

joblog=/tmp/jl-`basename $0`
export joblog
true > $joblog

do_dburl() {
    export dbvar=$1
    hostname=`hostname`
    username=`whoami`
    compgen -A function | G par_ | sort |
	stdout parallel -vj1 --timeout 200 --tagstring {#}{} --joblog +$joblog p_wrapper {} \$$dbvar |
	perl -pe 's/tbl\d+/TBL99999/gi;' |
	perl -pe 's/(from TBL99999 order) .*/$1/g' |
	perl -pe 's/ *\b'"$hostname"'\b */hostname/g' |
	perl -pe 's/ *\b'"$username"'\b */username/g' |
	perl -pe 's{/tmp/parallel-bug49791-[0-9a-f]+}{/tmp/parallel-bug49791-NNN}g' |
	grep -v -- --------------- |
	perl -pe 's/ *\bhost\b */host/g' |
	perl -pe 's/ +/ /g' |
	# SQLITE par_empty       Error: near line 1: in prepare, no such table: TBL99999 (1)
	# SQLITE par_empty       Parse error near line 1: no such table: TBL99999
	perl -pe 's/Error: near line 1: in prepare, (.*)/Parse error near line 1: $1/'
}
export -f do_dburl
parallel -j0 --timeout 1000% -v -k --tag do_dburl ::: CSV INFLUX MYSQL PG SQLITE
