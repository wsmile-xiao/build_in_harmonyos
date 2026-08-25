#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

unset run_test
unset run_once

# SSH only allowed to localhost/lo

par_sshloginfile() {
    echo '### --slf with mIxEd cAsE'
    tmp=$(mktemp)
    (
	echo 2/bash@LO
	echo 3/parallel@Lo:22
	echo 4/ksh@lO:ssh
    ) > "$tmp"
    seq 9 | parallel --slf "$tmp" 'whoami;sleep 1;echo' | sort
    rm -f "$tmp"
}

par__test_different_rsync_versions() {
    echo '### different versions of rsync need fixups'
    echo '### no output is good'
    doit() {
	full=$1
	short=$2
	rm -f 'a`b`c\<d\$e\{#\}g\"h\ i'$short 'a`b`c\<d\$e\{#\}g\"h\ i'$short.out
	touch 'a`b`c\<d\$e\{#\}g\"h\ i'$short
	TMPDIR=/tmp tmp=$(mktemp -d)
	(
	    echo '#!/bin/bash'
	    echo $full' "$@"'
	) > "$tmp"/rsync
	chmod +x "$tmp"/rsync
	PATH="$tmp":"$PATH"
	# Test basic rsync
	if stdout rsync "$tmp"/rsync sh@lo:rsync.$short >/dev/null ; then
	   echo Basic use works: $2
	   stdout parallel -j50% --trc {}.out -S sh@lo cp {} {}.out ::: 'a`b`c\<d\$e\{#\}g\"h\ i'$short
	   stdout rm 'a`b`c\<d\$e\{#\}g\"h\ i'$short 'a`b`c\<d\$e\{#\}g\"h\ i'$short.out
	else
	    echo Basic use failed - not tested: $short
	fi
	rm -rf "$tmp"
    }
    export -f doit
    stdout parallel --tagstring {/} -k doit {} {/} ::: /usr/local/bin/rsync-v*
}

par_--nonall_results() {
    echo '### --results --onall'
    tmp="$TMPDIR"/onall
    mkdir -p "$tmp"
    parallel --results "$tmp"/noslash --onall -Scsh@lo,sh@lo ::: id pwd
    parallel --results "$tmp"/slash/ --onall -Scsh@lo,sh@lo ::: id pwd
    parallel --results "$tmp"/rplslash/{}/ --onall -Scsh@lo,sh@lo ::: id pwd
    parallel --results "$tmp"/rplnoslash/{} --onall -Scsh@lo,sh@lo ::: id pwd
    parallel --results "$tmp"/rpl1slash/{1}/ --onall -Scsh@lo,sh@lo ::: id pwd
    parallel --results "$tmp"/rpl1noslash/{1} --onall -Scsh@lo,sh@lo ::: id pwd
    find "$tmp" -print0 | replace_tmpdir | sort
    rm -r "$tmp"
    echo '### --results --nonall'
    tmp="$TMPDIR"/nonall
    mkdir -p "$tmp"
    parallel --results "$tmp"/noslash --nonall -Scsh@lo,sh@lo pwd
    parallel --results "$tmp"/slash/ --nonall -Scsh@lo,sh@lo pwd
    parallel --results "$tmp"/rplslash/{}/ --nonall -Scsh@lo,sh@lo pwd
    parallel --results "$tmp"/rplnoslash/{} --nonall -Scsh@lo,sh@lo pwd
    parallel --results "$tmp"/rpl1slash/{1}/ --nonall -Scsh@lo,sh@lo pwd
    parallel --results "$tmp"/rpl1noslash/{1} --nonall -Scsh@lo,sh@lo pwd
    find "$tmp" -print0 | replace_tmpdir | sort
    rm -r "$tmp"
}

par_warn_when_exporting_func() {
    echo 'bug #40137: SHELL not bash: Warning when exporting funcs'
    myrun() {
	. <(printf 'myfunc() {\necho Function run: $1\n}')
	export -f myfunc
	echo "Run function in $1"
	PARALLEL_SHELL=$1 parallel -j50% --env myfunc -S lo myfunc ::: OK
    }
    export -f myrun
    parallel -k --tag myrun ::: /bin/{sh,bash} /usr/bin/{csh,dash,ksh,tcsh,zsh}
}

par_exporting_in_zsh() {
    echo '### zsh'
    
    echo 'env in zsh'
    echo 'Normal variable export'
    export B=\'"  Var with quote"
    PARALLEL_SHELL=/usr/bin/zsh parallel --env B echo '$B' ::: OK

    echo 'Function export as variable'
    export myfuncvar="() { echo myfuncvar as var \$*; }"
    PARALLEL_SHELL=/usr/bin/zsh parallel --env myfuncvar myfuncvar ::: OK

    echo 'Function export as function'
    myfunc() { echo myfunc ran $*; }
    export -f myfunc
    PARALLEL_SHELL=/usr/bin/zsh parallel --env myfunc myfunc ::: OK

    ssh zsh@lo 'fun="() { echo function from zsh to zsh \$*; }"; 
              export fun; 
              parallel --env fun fun ::: OK'

    ssh zsh@lo 'fun="() { echo function from zsh to bash \$*; }"; 
              export fun; 
              parallel -S parallel@lo --env fun fun ::: OK'
}

par_bigvar_csh() {
    echo '### csh'
    echo "3 big vars run remotely - length(base64) > 1000"
    stdout ssh csh@lo 'setenv A `seq 200|xargs`; 
                     setenv B `seq 200 -1 1|xargs`; 
                     setenv C `seq 300 -2 1|xargs`; 
                     parallel -Scsh@lo --env A,B,C -k echo \$\{\}\|wc ::: A B C'
    echo '### csh2'
    echo "3 big vars run locally"
    stdout ssh csh@lo 'setenv A `seq 200|xargs`; 
                     setenv B `seq 200 -1 1|xargs`; 
                     setenv C `seq 300 -2 1|xargs`; 
                     parallel --env A,B,C -k echo \$\{\}\|wc ::: A B C'
}

par_bigvar_rc() {
    echo '### rc'
    echo "3 big vars run remotely - length(base64) > 1000"
    stdout ssh rc@lo 'A=`{seq 200}; 
                    B=`{seq 200 -1 1}; 
                    C=`{seq 300 -2 1}; 
                    parallel -Src@lo --env A,B,C -k echo '"'"'${}|wc'"'"' ::: A B C'

    echo '### rc2'
    echo "3 big vars run locally"
    stdout ssh rc@lo 'A=`{seq 200}; 
                    B=`{seq 200 -1 1}; 
                    C=`{seq 300 -2 1}; 
                    parallel --env A,B,C -k echo '"'"'${}|wc'"'"' ::: A B C'
}

par__--tmux_length() {
    echo '### tmux examples that earlier blocked'
    echo 'Runtime 14 seconds on non-loaded machine'
    short_TMPDIR() {
	# TMPDIR must be short for -M                                                         
	export TMPDIR=/tmp/ssh/'                                                              
`touch /tmp/tripwire`                                                                     
'
	TMPDIR=/tmp
	mkdir -p "$TMPDIR"
    }
    short_TMPDIR
    export PARALLEL="--unsafe --timeout 30 --tmux"
    (
	stdout parallel -Sparallel@lo echo ::: \\\\\\\"\\\\\\\"\\\;\@
        stdout parallel -Sparallel@lo echo ::: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

	echo '### These blocked due to length'
	stdout parallel -Slo      echo ::: \\\\\\\"\\\\\\\"\\\;\@
	stdout parallel -Scsh@lo  echo ::: \\\\\\\"\\\\\\\"\\\;\@
	stdout parallel -Stcsh@lo echo ::: \\\\\\\"\\\\\\\"\\\;\@
	stdout parallel -Szsh@lo  echo ::: \\\\\\\"\\\\\\\"\\\;\@
	stdout parallel -Scsh@lo  echo ::: 111111111111111111111111111111111111111111111111111111111
     ) | replace_tmpdir |
	perl -pe 's:tms.....:tmsXXXXX:'
}

par__transfer_return_multiple_inputs() {
    echo '### bug #43746: --transfer and --return of multiple inputs {1} and {2}'
    echo '### and:'
    echo '### bug #44371: --trc with csh complains'
    cd /tmp; echo file1 output line 1 > file1; echo file2 output line 3 > file2
    parallel -Scsh@lo --transferfile {1} --transferfile {2} --trc {1}.a --trc {2}.b \
	     '(cat {1}; echo A {1} output line 2) > {1}.a; (cat {2};echo B {2} output line 4) > {2}.b' ::: file1 ::: file2
    cat file1.a file2.b
    rm /tmp/file1 /tmp/file2 /tmp/file1.a /tmp/file2.b
}

par_z_csh_nice() {
    echo '### bug #44143: csh and nice'
    parallel --nice 1 -S csh@lo setenv B {}\; echo '$B' ::: OK
}

par_z_multiple_hosts_repeat_arg() {
    echo '### bug #45575: -m and multiple hosts repeats first args'
    seq 1 3 | parallel -X -S 2/lo,2/: -k echo 
}

export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 1000% -j50% --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g;'
