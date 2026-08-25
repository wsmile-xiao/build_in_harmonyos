#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Clean up environment to make room for the test functions
while read f ; do
    eval unset -f "$f";
done < <(compgen -A function | grep ^_)

. `which env_parallel.bash`
env_parallel --session

true <<'EOF'
#!/bin/bash

# Find the command line limit formula
# macosx.p = 10.7.5
# El capitan = 10.11.4

. `which find-first-fail`
doit() {
    nfunc=$1
    lfunc=$2
    lfuncname=$3
    nvar=$4
    lvar=$5
    lvarname=$6
    onechar=$7
    varval="$(perl -e 'print "x "x('$lvar'/2)')"
    varname=$(perl -e 'print "x"x'$lvarname)
    funcval="$(perl -e 'print "x "x('$lfunc'/2)')"
    funcname=$(perl -e 'print "x"x'$lfuncname)
    for a in `seq $nvar`; do eval "export v$varname$a='$varval'" ; done
    for a in `seq $nfunc`; do eval "f$funcname$a() { $funcval; }" ; done
    for a in `seq $nfunc`; do eval "export -f f$funcname$a" ; done
    myrun() {
	/bin/echo $(perl -e 'print "a"x('$2')." x"x('$1'/2)')
    }
    export -f myrun
    binlen=dummy
    binlen=$(find-first-fail -q myrun $onechar)
    perl -e '
    $envc=(keys %ENV);
    $envn=length join"",(keys %ENV);
    $envv=length join"",(values %ENV);
    $onechar='$onechar';
    $maxlen=-39+262144 - $envn - $envv - $onechar*5 - $envc*10;
    print("Computed max len = $maxlen\n");
    $bin='$binlen';
    print("Diff:",$bin-$maxlen," Actual:$bin Vars: $onechar $envc $envn $envv\n");
       '
}
export -f doit

val="$(seq 2 100 1000)"
val="10 20 50 100 200 500 1000"
val="12 103 304 506 1005"
parallel --timeout 20 --shuf --tag -k doit ::: $val ::: $val ::: $val ::: $val ::: $val ::: $val ::: $val 2>/dev/null

# Test with random data
(seq 10;seq 100;seq 100;seq 100;seq 100; seq 300 ;seq 1000) |
    shuf | parallel -n 7 --timeout 20 --tag -k doit
EOF

# Each should generate at least 2 commands

par_many_args() {
    export PARALLEL="--unsafe"
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    geny() { yes | head -c $1; }
    for a in `seq 6000`; do eval "export a$a=1" ; done
    geny 10000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc' |
	perl -pe 's/( y){10,}//g'
    echo
}

par_many_var() {
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    for a in `seq 6000`; do eval "export a$a=1" ; done
    gen 40000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc -c' |
	perl -pe 's/\d{10,}.\d+ //g; s/(\d+)\d\d\d/${1}XXX/g;' |
	grep XXX
    echo
}

par_many_var_func() {
    export PARALLEL="--unsafe"
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    for a in `seq 2000`; do eval "export a$a=1" ; done
    for a in `seq 2000`; do eval "a$a() { 1; }" ; done
    for a in `seq 2000`; do eval export -f a$a ; done
    gen 40000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc' |
	perl -pe 's/\d{10,}.\d+ //g'
    echo
}

par_many_func() {
    export PARALLEL="--unsafe"
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    for a in `seq 3000`; do eval "a$a() { 1; }" ; done
    for a in `seq 3000`; do eval export -f a$a ; done
    gen 40000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc'
    echo |
	perl -pe 's/\d{10,}.\d+ //g'
    echo
}

par_big_func() {
    export PARALLEL="--unsafe"
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    big=`seq 1000`
    for a in `seq 1`; do eval "a$a() { '$big'; }" ; done
    for a in `seq 1`; do eval export -f a$a ; done
    gen 80000 | stdout parallel --load 2 -Xkj1  'pecho {} {} {} {} | wc' |
	perl -pe 's/\d{10,}.\d+ //g'
    echo
}

par_many_var_big_func() {
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    big=`seq 1000`
    for a in `seq 5000`; do eval "export a$a=1" ; done
    for a in `seq 10`; do eval "a$a() { '$big'; }" ; done
    for a in `seq 10`; do eval export -f a$a ; done
    gen 40000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc -c' |
	perl -pe 's/\d{10,}.\d+ //g; s/(\d+)\d\d\d/${1}XXX/g;' 
    echo
}

par_big_func_name() {
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    big=`perl -e print\"x\"x10000`
    for a in `seq 10`; do eval "export a$big$a=1" ; done
    gen 30000 | stdout parallel -Xkj1  'pecho {} {} {} {} | wc -c' |
	perl -pe 's/\d{10,}.\d+ //g; s/(\d+)\d\d\d/${1}XXX/g;' |
	grep 1.XXX
    echo
}

par_big_var_func_name() {
    export LC_ALL=C
    rm -f ~/.parallel/tmp/sshlogin/*/linelen
    gen() { seq -f %f 1000000000000000 1000000000050000 | head -c $1; }
    pecho() { perl -e 'print "@ARGV\n"' "$@"; }
    export -f pecho
    big=`perl -e print\"x\"x5000`
    for a in `seq 10`; do eval "export a$big$a=1" ; done
    for a in `seq 10`; do eval "a$big$a() { 1; }" ; done
    for a in `seq 10`; do eval export -f a$big$a ; done
    gen 80000 | stdout parallel --load 4 -Xkj1  'pecho {} {} {} {} | wc -c' |
	perl -pe 's/\d{10,}.\d+ //g; s/(\d+)\d\d\d/${1}XXX/g;' |
	grep XXX
    echo
}

export PARALLEL="--unsafe"
macsshlogin=$(parallel --timeout 30 --halt now,success=1 ssh {} echo {} ::: ota@mac macosx.p)

if scp /usr/local/bin/parallel $macsshlogin:bin/ ; then
    true
else
    echo "**"
    echo "** Mac not found. Skip testing"
    echo "**"
    exit 1
fi

export LC_ALL=C
export -f $(compgen -A function | grep par_)
compgen -A function |
    grep par_ |
    LC_ALL=C sort |
    env_parallel --timeout 3000% --tag -k -S 6/$macsshlogin 'PATH=$HOME/bin:$PATH; {}' |
    perl -pe 's/(\d+)\d\d\d/${1}XXX/g'
