#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_sshlogin_parsing() {
    echo '### Generate sshlogins to test parsing'
    sudo $(which sshd) -p 22222

    gen_sshlogin() {
	grp=grp1+grp2
	ncpu=4
	ssh=/usr/bin/ssh
	user=parallel
	userpass=withpassword
	pass="$withpassword"
	host=lo
	port=22222
	# no pass
	parallel -k echo \
		 {1}{2}{3}{4}{5}{=1'$_ = ($arg[4]||$arg[5]) ? "\@" : ""' =}$host{6} \
		 ::: '' @$grp/ ::: '' $ncpu/ ::: '' $ssh' ' \
		 ::: '' $user ::: '' ::: '' :$port
	# pass
	parallel -k echo \
		 {1}{2}{3}{4}{5}{=1'$_ = ($arg[4]||$arg[5]) ? "\@" : ""' =}$host{6} \
		 ::: '' @$grp/ ::: '' $ncpu/ ::: '' $ssh' ' \
		 ::: '' $userpass ::: :"$pass" ::: '' :$port
    }

    doit() {
	if parallel -S "$1" {} '$SSH_CLIENT|field 3;whoami' ::: echo ; then
	    : echo OK
	else
	    echo Fail
	fi
    }
    export -f doit
    
    gen_sshlogin | parallel --tag --timeout 20 -k doit
}

par_--tmux_different_shells() {
    echo '### Test tmux works on different shells'
    short_TMPDIR() {
	# TMPDIR must be short for -M                                                         
	export TMPDIR=/tmp/ssh/'                                                              
`touch /tmp/tripwire`
'
	TMPDIR=/tmp
	mkdir -p "$TMPDIR"
    }
    short_TMPDIR
    (
	stdout parallel -Scsh@lo,tcsh@lo,parallel@lo,zsh@lo --tmux echo ::: 1 2 3 4; echo exit:0=$?
	stdout parallel -Scsh@lo,tcsh@lo,parallel@lo,zsh@lo --tmux false ::: 1 2 3 4; echo exit:4=$?

	export PARTMUX='parallel -Scsh@lo,tcsh@lo,parallel@lo,zsh@lo --tmux '; 
	stdout ssh zsh@lo      "$PARTMUX" 'true  ::: 1 2 3 4; echo exit:0=$status' 
	stdout ssh zsh@lo      "$PARTMUX" 'false ::: 1 2 3 4; echo exit:4=$status' 
	stdout ssh parallel@lo "$PARTMUX" 'true  ::: 1 2 3 4; echo exit:0=$?'      
	stdout ssh parallel@lo "$PARTMUX" 'false ::: 1 2 3 4; echo exit:4=$?'      
	stdout ssh tcsh@lo     "$PARTMUX" 'true  ::: 1 2 3 4; echo exit:0=$status' 
	stdout ssh tcsh@lo     "$PARTMUX" 'false ::: 1 2 3 4; echo exit:4=$status' 
	echo "# command is currently too long for csh. Maybe it can be fixed?"; 
	stdout ssh csh@lo      "$PARTMUX" 'true  ::: 1 2 3 4; echo exit:0=$status'
	stdout ssh csh@lo      "$PARTMUX" 'false ::: 1 2 3 4; echo exit:4=$status'
    ) | replace_tmpdir | perl -pe 's/tms...../tmsXXXXX/g'
}


export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 1000% -j50% --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g;'
