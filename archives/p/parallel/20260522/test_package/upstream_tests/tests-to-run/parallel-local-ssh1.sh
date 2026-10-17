#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# SSH only allowed to localhost/lo
rm -rf tmp
mkdir tmp
cd tmp
unset run_test

cat <<'EOF' | sed -e s/\$SERVER1/$SERVER1/\;s/\$SERVER2/$SERVER2/ | stdout parallel -vj300% -k --joblog /tmp/jl-`basename $0` -L1 -r

echo TODO

## echo '### Test --trc --basefile --/./--foo7 :/./:foo8 " "/./" "foo9 ./foo11/./foo11'

EOF

par__sshlogin_with_comma() {
    echo "### --sshlogin with \,"
    parallel -S 'ssh -J lo\,localhost 127.0.0.1' echo ::: OK
    echo "### --sshlogin with ,,"
    parallel -S 'ssh -J lo,,localhost 127.0.0.1' echo ::: OK
    echo "### Both , and ,, in -S"
    parallel -S'1/ssh -oProxyJump=vagrant@parallel-server1,,vagrant@parallel-server2 vagrant@parallel-server3,1/vagrant@parallel-server1' ::: hostname hostname |
	sort
    parallel --nonall -S'1/ssh -oProxyJump=vagrant@parallel-server1,,vagrant@parallel-server2 vagrant@parallel-server3,1/vagrant@parallel-server1' hostname |
        sort
    parallel --onall -S'1/ssh -oProxyJump=vagrant@parallel-server1,,vagrant@parallel-server2 vagrant@parallel-server3,1/vagrant@parallel-server1' ::: hostname |
        sort
}

par__sshpass_with_password() {
    echo '### sshpass'
    . ~/.passwords
    qwithpassword=$(echo "$withpassword" | parallel --shellquote)
    echo OK | parallel -S "sshpass -p $qwithpassword ssh withpassword@lo:22" echo
    echo OK | parallel -S withpassword:"$withpassword"@lo:22 echo
    echo OK | parallel --onall -S withpassword:"$withpassword"@lo:22 echo
    export SSHPASS="$withpassword"
    echo OK | parallel -S withpassword:@lo:22 echo
    echo OK | parallel --onall -S withpassword:@lo:22 echo
    echo '### Crazy passwords: `date>>/tmp/trap`;(|<*&)'"'"
    > /tmp/trap
    (
	echo '# These fail. The important part is that /tmp/trap is empty'
	stdout parallel --onall -S5/user:'`date>>/tmp/trap`;'@host echo ::: A
	stdout parallel --onall -S5/user:'`date>>/tmp/trap`;(|<*&)'"'"@host echo ::: A
    ) | perl -pe 's/([a-f0-9]{100,} )+[a-f0-9]{1,}/HEX/g; s/\r/\n/g;' |
	perl -pe 's/(ssh: Could not resolve hostname host:) .*/$1/'
    echo This must stay empty:
    grep . /tmp/trap || echo OK
}

par_--ssh_ssh_in_ssh() {
    echo '### bug #61894: Pack ssh code in eval protection'
    echo Unquoted ssh should work
    hostname=$(hostname)
    (
	parallel --ssh 'ssh -A lo ssh' -S lo 'hostname;echo' ::: OK
	parallel --ssh 'eval ssh -A lo ssh' -S lo 'hostname;echo' ::: OK
	parallel --ssh 'eval ssh -A lo eval ssh' -S lo 'hostname;echo' ::: OK
	parallel --ssh 'sshpass ssh -A bash@lo eval ssh' -S csh@lo 'hostname;echo' ::: OK
    ) | perl -pe "s/$hostname/myhostname/g"
}

par_stop_if_no_hosts_left() {
    echo '### Stop if all hosts are filtered and there are no hosts left to run on'
    stdout parallel --filter-hosts -S no-such.host echo ::: 1
}

par_csh_variable_newline() {
    echo '### Can csh propagate a variable containing \n'
    export A=$(seq 3); parallel -S csh@lo --env A bash -c \''echo "$A"'\' ::: dummy
}

par_pipe_unneeded_spawn() {
    echo '### Test bug #34241: --pipe should not spawn unneeded processes'
    seq 5 | ssh csh@lo parallel -k --block 5 --pipe -j10 cat\\\;echo Block_end
}

par_files_nonall() {
    echo '### bug #40002: --files and --nonall seem not to work together:'
    # --files does not work with TMPDIR containing \n
    TMPDIR=/tmp
    parallel --files --nonall -S localhost true | tee >(parallel rm) | wc -l
}

par_joblog_nonall() {
    echo '### bug #40001: --joblog and --nonall seem not to work together:'
    parallel --joblog - --nonall -S lo,localhost true | wc -l
}

par_workdir_home() {
    echo '### bug #40132: FreeBSD: --workdir . gives warning if . == $HOME'
    cd && parallel --workdir . -S lo pwd ::: ""
}

par_z_PARALLEL_SSH_function() {
    echo '### use function as $PARALLEL_SSH'
    foossh() { echo "FOOSSH" >&2; ssh "$@"; }
    export -f foossh
    PARALLEL_SSH=foossh parallel -S 1/lo echo ::: 'Run through FOOSSH?'
}

par_ssh() {
    echo '### use --ssh'
    barssh() { echo "BARSSH" >&2; ssh "$@"; }
    export -f barssh
    parallel --ssh barssh -S 1/lo echo ::: 'Run through BARSSH?'
}

par_filename_colon() {
    echo '### test filename :'
    echo content-of-: > :
    echo : | parallel -j1 --trc {}.{.} -S parallel@lo '(echo remote-{}.{.};cat {}) > {}.{.}'
    cat :.:; rm : :.:
}

par_wd_dotdotdot() {
    echo '### Test --wd ... --cleanup which should remove the filled tmp dir'
    ssh sh@lo 'mkdir -p .parallel/tmp; find .parallel/tmp |grep uNiQuE_sTrInG.6 | parallel rm'
    stdout parallel -j9 -k --retries 3 --wd ... --cleanup -S sh@lo -v echo ">"{}.6 :::  uNiQuE_sTrInG
    find ~sh/.parallel/tmp |grep uNiQuE_sTrInG.6
}

par_wd_dashdash() {
    echo '### Test --wd --'
    stdout parallel --wd -- -S sh@lo echo OK ">"{}.7 ::: uNiQuE_sTrInG
    cat ~sh/--/uNiQuE_sTrInG.7
    stdout ssh sh@lo rm ./--/uNiQuE_sTrInG.7
}

par_wd_space() {
    echo '### Test --wd " "'
    stdout parallel --wd " " -S sh@lo echo OK ">"{}.8 ::: uNiQuE_sTrInG
    cat ~sh/" "/uNiQuE_sTrInG.8
    stdout ssh sh@lo rm ./'" "'/uNiQuE_sTrInG.8
}

par_wd_quote() {
    echo "### Test --wd \"'\""
    stdout parallel --wd "'" -S sh@lo echo OK ">"{}.9 ::: uNiQuE_sTrInG
    cat ~sh/"'"/uNiQuE_sTrInG.9
    stdout ssh sh@lo rm ./"\\'"/uNiQuE_sTrInG.9
}

par__trc_dashdash() {
    echo '### Test --trc ./--/--foo1'
    mkdir -p ./--; echo 'Content --/--foo1' > ./--/--foo1
    stdout parallel --trc {}.1 -S sh@lo '(cat {}; echo remote1) > {}.1' ::: ./--/--foo1; cat ./--/--foo1.1
    stdout parallel --trc {}.2 -S sh@lo '(cat ./{}; echo remote2) > {}.2' ::: --/--foo1; cat ./--/--foo1.2
}

par__trc_colon() {
    echo '### Test --trc ./:dir/:foo2'
    mkdir -p ./:dir; echo 'Content :dir/:foo2' > ./:dir/:foo2
    stdout parallel --trc {}.1 -S sh@lo '(cat {}; echo remote1) > {}.1' ::: ./:dir/:foo2
    cat ./:dir/:foo2.1
    stdout parallel --trc {}.2 -S sh@lo '(cat ./{}; echo remote2) > {}.2' ::: :dir/:foo2
    cat ./:dir/:foo2.2
}

par__trc_space() {
    echo '### Test --trc ./" "/" "foo3'
    mkdir -p ./" "; echo 'Content _/_foo3' > ./" "/" "foo3
    stdout parallel --trc {}.1 -S sh@lo '(cat {}; echo remote1) > {}.1' ::: ./" "/" "foo3
    cat ./" "/" "foo3.1
    stdout parallel --trc {}.2 -S sh@lo '(cat ./{}; echo remote2) > {}.2' ::: " "/" "foo3
    cat ./" "/" "foo3.2
}

par__trc_dashdashdot() {
    echo '### Test --trc ./--/./--foo4'
    mkdir -p ./--; echo 'Content --/./--foo4' > ./--/./--foo4
    stdout parallel --trc {}.1 -S sh@lo '(cat ./--foo4; echo remote{}) > --foo4.1' ::: --/./--foo4
    cat ./--/./--foo4.1
}

par__trc_colondot() {
    echo '### Test --trc ./:/./:foo5'
    mkdir -p ./:a; echo 'Content :a/./:foo5' > ./:a/./:foo5
    stdout parallel --trc {}.1 -S sh@lo '(cat ./:foo5; echo remote{}) > ./:foo5.1' ::: ./:a/./:foo5
    cat ./:a/./:foo5.1
}

par__trc_spacedot() {
    echo '### Test --trc ./" "/./" "foo6'
    mkdir -p ./" "; echo 'Content _/./_foo6' > ./" "/./" "foo6
    stdout parallel --trc {}.1 -S sh@lo '(cat ./" "foo6; echo remote{}) > ./" "foo6.1' ::: ./" "/./" "foo6
    cat ./" "/./" "foo6.1
}

par__trc_dashdashspace() {
    echo '### Test --trc "-- " "-- "'
    touch -- '-- ' ' --'; rm -f ./?--.a ./--?.a
    parallel --trc {}.a -S csh@lo,sh@lo touch ./{}.a ::: '-- ' ' --'; ls ./--?.a ./?--.a
    parallel --nonall -k -S csh@lo,sh@lo 'ls ./" "-- || echo OK'
    parallel --nonall -k -S csh@lo,sh@lo 'ls ./--" " || echo OK'
    parallel --nonall -k -S csh@lo,sh@lo 'ls ./" "--.a || echo OK'
    parallel --nonall -k -S csh@lo,sh@lo 'ls ./--" ".a || echo OK'
}

par__trc_dashdashdashspace() {
    echo '### Test --trc "/tmp/./--- /A" "/tmp/./ ---/B"'
    mkdir -p '/tmp/./--- '   '/tmp/ ---'
    touch -- '/tmp/./--- /A' '/tmp/ ---/B'
    rm -f ./---?/A.a ./?---/B.a
    parallel --trc {=s:.*/./::=}.a -S csh@lo,sh@lo touch ./{=s:.*/./::=}.a ::: '/tmp/./--- /A' '/tmp/./ ---/B'
    ls ./---?/A.a ./?---/B.a | LC_ALL=C sort
    parallel --nonall -k -S csh@lo,sh@lo 'ls ./?--- ./---? || echo OK' | LC_ALL=C sort
}

par_--onall_--transfer() {
    echo '### bug #46519: --onall ignores --transfer'
    touch bug46519.{a,b,c}; rm -f bug46519.?? bug46519.???
    parallel --onall --tf bug46519.{} --trc bug46519.{}{} --trc bug46519.{}{}{} -S csh@lo,sh@lo 'ls bug46519.{}; touch bug46519.{}{} bug46519.{}{}{}' ::: a b c
    ls bug46519.?? bug46519.???
    parallel --onall -S csh@lo,sh@lo ls bug46519.{}{} bug46519.{}{}{} ::: a b c &&
	echo Cleanup failed
}

par_z_--onall_--plus() {
    echo '### Test --plus is respected with --onall/--nonall'
    parallel -S bash@lo --onall --plus echo {host} ::: OK
    parallel -S bash@lo --nonall --plus echo {host}
}

par__remote_load() {
    echo '### Test --load remote'
    ssh parallel@lo 'seq 10 | parallel --nice 19 --timeout 15 -j0 -qN0 perl -e while\(1\)\{\ \}' &
    sleep 1
    stdout /usr/bin/time -f %e parallel -S parallel@lo --load 10 sleep ::: 1 | perl -ne '$_ > 10 and print "OK\n"'
}

par_remote_nice() {
    echo '### Test --nice remote'
    parallel --nice 5 -S lo 'ps -l $$|field 8; true' ::: a
    nice -n5 parallel -S lo 'ps -l $$|field 8; true' ::: a
}

par_hgrp_agrp_comma() {
    echo '### bug #63722: hostgroup with , breaks parser'
    stdout parallel --hgrp ::: whoami@csh@lo,tcsh@lo whoami@csh@lo,tcsh@lo | sort
}

par_hgrp_agrp() {
    echo '### Test --hgrp {hgrp} {agrp}'
    parallel --plus --hgrp -S @b+lo/bash@lo,@c+lo/csh@lo --tag 'echo hgrp={hgrp};echo agrp={agrp}' ::: A@b+c B@b C@c D@c+b@u E |
	grep -vF -f <(cat <<_
A	agrp=b+c
A	hgrp=b+bash@lo+lo
A	hgrp=b+lo+bash@lo
A	hgrp=bash@lo+b+lo
A	hgrp=bash@lo+lo+b
A	hgrp=c+csh@lo+lo
A	hgrp=c+lo+csh@lo
A	hgrp=csh@lo+c+lo
A	hgrp=csh@lo+lo+c
A	hgrp=lo+b+bash@lo
A	hgrp=lo+bash@lo+b
A	hgrp=lo+c+csh@lo
A	hgrp=lo+csh@lo+c
B	agrp=b
B	hgrp=b+bash@lo+lo
B	hgrp=b+lo+bash@lo
B	hgrp=bash@lo+b+lo
B	hgrp=bash@lo+lo+b
B	hgrp=lo+b+bash@lo
B	hgrp=lo+bash@lo+b
C	agrp=c
C	hgrp=c+csh@lo+lo
C	hgrp=c+lo+csh@lo
C	hgrp=csh@lo+c+lo
C	hgrp=csh@lo+lo+c
C	hgrp=lo+c+csh@lo
C	hgrp=lo+csh@lo+c
D	agrp=c+b@u
D	hgrp=c+csh@lo+lo
D	hgrp=c+lo+csh@lo
D	hgrp=csh@lo+c+lo
D	hgrp=csh@lo+lo+c
D	hgrp=lo+c+csh@lo
D	hgrp=lo+csh@lo+c
E	agrp=b+bash@lo+c+csh@lo+lo
E	agrp=b+bash@lo+c+lo+csh@lo
E	agrp=b+bash@lo+csh@lo+c+lo
E	agrp=b+bash@lo+csh@lo+lo+c
E	agrp=b+bash@lo+lo+c+csh@lo
E	agrp=b+bash@lo+lo+csh@lo+c
E	agrp=b+c+bash@lo+csh@lo+lo
E	agrp=b+c+bash@lo+lo+csh@lo
E	agrp=b+c+csh@lo+bash@lo+lo
E	agrp=b+c+csh@lo+lo+bash@lo
E	agrp=b+c+lo+bash@lo+csh@lo
E	agrp=b+c+lo+csh@lo+bash@lo
E	agrp=b+csh@lo+bash@lo+c+lo
E	agrp=b+csh@lo+bash@lo+lo+c
E	agrp=b+csh@lo+c+bash@lo+lo
E	agrp=b+csh@lo+c+lo+bash@lo
E	agrp=b+csh@lo+lo+bash@lo+c
E	agrp=b+csh@lo+lo+c+bash@lo
E	agrp=b+lo+bash@lo+c+csh@lo
E	agrp=b+lo+bash@lo+csh@lo+c
E	agrp=b+lo+c+bash@lo+csh@lo
E	agrp=b+lo+c+csh@lo+bash@lo
E	agrp=b+lo+csh@lo+bash@lo+c
E	agrp=b+lo+csh@lo+c+bash@lo
E	agrp=bash@lo+b+c+csh@lo+lo
E	agrp=bash@lo+b+c+lo+csh@lo
E	agrp=bash@lo+b+csh@lo+c+lo
E	agrp=bash@lo+b+csh@lo+lo+c
E	agrp=bash@lo+b+lo+c+csh@lo
E	agrp=bash@lo+b+lo+csh@lo+c
E	agrp=bash@lo+c+b+csh@lo+lo
E	agrp=bash@lo+c+b+lo+csh@lo
E	agrp=bash@lo+c+csh@lo+b+lo
E	agrp=bash@lo+c+csh@lo+lo+b
E	agrp=bash@lo+c+lo+b+csh@lo
E	agrp=bash@lo+c+lo+csh@lo+b
E	agrp=bash@lo+csh@lo+b+c+lo
E	agrp=bash@lo+csh@lo+b+lo+c
E	agrp=bash@lo+csh@lo+c+b+lo
E	agrp=bash@lo+csh@lo+c+lo+b
E	agrp=bash@lo+csh@lo+lo+b+c
E	agrp=bash@lo+csh@lo+lo+c+b
E	agrp=bash@lo+lo+b+c+csh@lo
E	agrp=bash@lo+lo+b+csh@lo+c
E	agrp=bash@lo+lo+c+b+csh@lo
E	agrp=bash@lo+lo+c+csh@lo+b
E	agrp=bash@lo+lo+csh@lo+b+c
E	agrp=bash@lo+lo+csh@lo+c+b
E	agrp=c+b+bash@lo+csh@lo+lo
E	agrp=c+b+bash@lo+lo+csh@lo
E	agrp=c+b+csh@lo+bash@lo+lo
E	agrp=c+b+csh@lo+lo+bash@lo
E	agrp=c+b+lo+bash@lo+csh@lo
E	agrp=c+b+lo+csh@lo+bash@lo
E	agrp=c+bash@lo+b+csh@lo+lo
E	agrp=c+bash@lo+b+lo+csh@lo
E	agrp=c+bash@lo+csh@lo+b+lo
E	agrp=c+bash@lo+csh@lo+lo+b
E	agrp=c+bash@lo+lo+b+csh@lo
E	agrp=c+bash@lo+lo+csh@lo+b
E	agrp=c+csh@lo+b+bash@lo+lo
E	agrp=c+csh@lo+b+lo+bash@lo
E	agrp=c+csh@lo+bash@lo+b+lo
E	agrp=c+csh@lo+bash@lo+lo+b
E	agrp=c+csh@lo+lo+b+bash@lo
E	agrp=c+csh@lo+lo+bash@lo+b
E	agrp=c+lo+b+bash@lo+csh@lo
E	agrp=c+lo+b+csh@lo+bash@lo
E	agrp=c+lo+bash@lo+b+csh@lo
E	agrp=c+lo+bash@lo+csh@lo+b
E	agrp=c+lo+csh@lo+b+bash@lo
E	agrp=c+lo+csh@lo+bash@lo+b
E	agrp=csh@lo+b+bash@lo+c+lo
E	agrp=csh@lo+b+bash@lo+lo+c
E	agrp=csh@lo+b+c+bash@lo+lo
E	agrp=csh@lo+b+c+lo+bash@lo
E	agrp=csh@lo+b+lo+bash@lo+c
E	agrp=csh@lo+b+lo+c+bash@lo
E	agrp=csh@lo+bash@lo+b+c+lo
E	agrp=csh@lo+bash@lo+b+lo+c
E	agrp=csh@lo+bash@lo+c+b+lo
E	agrp=csh@lo+bash@lo+c+lo+b
E	agrp=csh@lo+bash@lo+lo+b+c
E	agrp=csh@lo+bash@lo+lo+c+b
E	agrp=csh@lo+c+b+bash@lo+lo
E	agrp=csh@lo+c+b+lo+bash@lo
E	agrp=csh@lo+c+bash@lo+b+lo
E	agrp=csh@lo+c+bash@lo+lo+b
E	agrp=csh@lo+c+lo+b+bash@lo
E	agrp=csh@lo+c+lo+bash@lo+b
E	agrp=csh@lo+lo+b+bash@lo+c
E	agrp=csh@lo+lo+b+c+bash@lo
E	agrp=csh@lo+lo+bash@lo+b+c
E	agrp=csh@lo+lo+bash@lo+c+b
E	agrp=csh@lo+lo+c+b+bash@lo
E	agrp=csh@lo+lo+c+bash@lo+b
E	agrp=lo+b+bash@lo+c+csh@lo
E	agrp=lo+b+bash@lo+csh@lo+c
E	agrp=lo+b+c+bash@lo+csh@lo
E	agrp=lo+b+c+csh@lo+bash@lo
E	agrp=lo+b+csh@lo+bash@lo+c
E	agrp=lo+b+csh@lo+c+bash@lo
E	agrp=lo+bash@lo+b+c+csh@lo
E	agrp=lo+bash@lo+b+csh@lo+c
E	agrp=lo+bash@lo+c+b+csh@lo
E	agrp=lo+bash@lo+c+csh@lo+b
E	agrp=lo+bash@lo+csh@lo+b+c
E	agrp=lo+bash@lo+csh@lo+c+b
E	agrp=lo+c+b+bash@lo+csh@lo
E	agrp=lo+c+b+csh@lo+bash@lo
E	agrp=lo+c+bash@lo+b+csh@lo
E	agrp=lo+c+bash@lo+csh@lo+b
E	agrp=lo+c+csh@lo+b+bash@lo
E	agrp=lo+c+csh@lo+bash@lo+b
E	agrp=lo+csh@lo+b+bash@lo+c
E	agrp=lo+csh@lo+b+c+bash@lo
E	agrp=lo+csh@lo+bash@lo+b+c
E	agrp=lo+csh@lo+bash@lo+c+b
E	agrp=lo+csh@lo+c+b+bash@lo
E	agrp=lo+csh@lo+c+bash@lo+b
E	hgrp=b+bash@lo+lo
E	hgrp=b+lo+bash@lo
E	hgrp=bash@lo+b+lo
E	hgrp=bash@lo+lo+b
E	hgrp=c+csh@lo+lo
E	hgrp=c+lo+csh@lo
E	hgrp=csh@lo+c+lo
E	hgrp=csh@lo+lo+c
E	hgrp=lo+b+bash@lo
E	hgrp=lo+bash@lo+b
E	hgrp=lo+c+csh@lo
E	hgrp=lo+csh@lo+c
_
)
}

par__pipewrap() {
    echo '### pipewrap: hexwrap bootstrap delivery via ssh'
    parallel --sshlogin lo echo ::: a b c | sort
    parallel -k --sshlogin lo echo ::: 1 2 3
    MYVAR=hello parallel --nonall --env MYVAR --sshlogin lo 'echo $MYVAR'
    parallel --workdir /tmp --sshlogin lo pwd ::: dummy
}

par_pipe_ssh() {
    echo '### --pipe -S lo,: basic pipe to remote'
    seq 1000000 | parallel --pipe -k -S lo,: wc -l
}

par_pipe_tee_ssh() {
    echo '### --pipe --tee -S lo: data must reach local and remote (not 0 bytes)'
    seq 1000000 | parallel -j3 --pipe --tee -k -S lo,: 'wc {}' ::: -l -c -w
}

par_env_parallel_ssh() {
    echo '### env_parallel -S lo: must produce output (not empty)'
    . $(which env_parallel.bash)
    env_parallel -k -S lo,: echo ::: a b c
}

par_env_parallel_func_ssh() {
    echo '### env_parallel -S lo with function: function must transfer'
    . $(which env_parallel.bash)
    myfunc() { echo "func:$1"; }
    env_parallel -k -S lo,: myfunc ::: x y
}

export -f $(compgen -A function | grep par_)
compgen -A function | G "$@" par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j50% --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'

cd ..
rm -rf tmp
mkdir tmp
cd tmp
