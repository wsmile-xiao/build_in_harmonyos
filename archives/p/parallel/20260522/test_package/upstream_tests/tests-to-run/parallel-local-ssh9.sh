#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_bash_embed() {
  myscript=$(cat <<'_EOF'
    echo '--embed'
    parallel --embed | tac | perl -pe '
      /^parallel/ and not $seen++ and s{^}{
echo \${a[1]}
parset a echo ::: ParsetOK ParsetOK ParsetOK
env_parallel echo ::: env_parallel_OK
env_parallel --env myvar echo {} --env \\\$myvar ::: env_parallel
myvar=OK
parallel echo ::: parallel_OK
PATH=/usr/sbin:/usr/bin:/sbin:/bin
# Do not look for parallel in /usr/local/bin
#. \`which env_parallel.bash\`
}
    ' | tac > parallel-embed
    chmod +x parallel-embed
    ./parallel-embed
    rm parallel-embed
_EOF
  )
  ssh bash@lo "$myscript"
}

par_csh_embed() {
    echo Not implemented
}

par_fish_embed() {
    echo Not implemented
}

par_ksh_embed() {
  myscript=$(cat <<'_EOF'
    echo '--embed'
    parallel --embed | tac | perl -pe '
      /^parallel/ and not $seen++ and s{^}{
        echo \${a[1]}
        parset a echo ::: ParsetOK ParsetOK ParsetOK
        env_parallel echo ::: env_parallel_OK
        env_parallel --env myvar echo {} --env \\\$myvar ::: env_parallel
        myvar=OK
        parallel echo ::: parallel_OK
        PATH=/usr/sbin:/usr/bin:/sbin:/bin
        # Do not look for parallel in /usr/local/bin
        #. \`which env_parallel.ksh\`
      }
    ' | tac > parallel-embed
    chmod +x parallel-embed
    ./parallel-embed
    rm parallel-embed
_EOF
  )
  stdout ssh ksh@lo "$myscript" |
      # ./parallel-embed[XXX]: env_parallel[16122]: _which_PAR[15964]: perl: /usr/bin/perl: cannot exec
      perl -pe 's/env_parallel[^:]*: _which_PAR[^:]*: //'
}

par_sh_embed() {
  myscript=$(cat <<'_EOF'
    echo '--embed'
    parallel --embed | tac | perl -pe '
      /^parallel/ and not $seen++ and s{^}{
echo \$b
parset a,b,c echo ::: ParsetOK ParsetOK ParsetOK
env_parallel echo ::: env_parallel_OK
env_parallel --env myvar echo {} --env \\\$myvar ::: env_parallel
myvar=OK
parallel echo ::: parallel_OK
PATH=/usr/sbin:/usr/bin:/sbin:/bin
# Do not look for parallel in /usr/local/bin
#. \`which env_parallel.sh\`
}
    ' | tac > parallel-embed
    chmod +x parallel-embed
    ./parallel-embed
    rm parallel-embed
_EOF
  )
  ssh sh@lo "$myscript"
}

par_tcsh_embed() {
    echo Not implemented
}

par_zsh_embed() {
  myscript=$(cat <<'_EOF'
    echo '--embed'
    parallel --embed | tac | perl -pe '
      /^parallel/ and not $seen++ and s{^}{
echo \${a[1]}
parset a echo ::: ParsetOK ParsetOK ParsetOK
env_parallel echo ::: env_parallel_OK
env_parallel --env myvar echo {} --env \\\$myvar ::: env_parallel
myvar=OK
parallel echo ::: parallel_OK
PATH=/usr/sbin:/usr/bin:/sbin:/bin
# Do not look for parallel in /usr/local/bin
}
    ' | tac > parallel-embed
    chmod +x parallel-embed
    ./parallel-embed
    rm parallel-embed
_EOF
  )
  ssh zsh@lo "$myscript" 2>&1 |
      grep -v .zshenv:.:1
}

par__propagate_env() {
    echo '### bug #41805: Idea: propagate --env for parallel --number-of-cores'
    # csh complains if MANPATH is unset. Provoke this.
    unset MANPATH
    echo '** test_zsh'
    FOO=test_zsh parallel --env FOO,HOME -S zsh@lo -N0 env ::: "" |sort|egrep 'FOO|^HOME'
    echo '** test_zsh_filter'
    FOO=test_zsh_filter parallel --filter-hosts --env FOO,HOME -S zsh@lo -N0 env ::: "" |sort|egrep 'FOO|^HOME'
    echo '** test_csh'
    FOO=test_csh parallel --env FOO,HOME -S csh@lo -N0 env ::: "" |sort|egrep 'FOO|^HOME'
    echo '** test_csh_filter'
    FOO=test_csh_filter parallel --filter-hosts --env FOO,HOME -S csh@lo -N0 env ::: "" |sort|egrep 'FOO|^HOME'
    echo '** bug #41805 done'
}

par_env_parallel_big_env() {
    echo '### bug #54128: command too long when exporting big env'
    . env_parallel.bash
    env_parallel --session
    a=`rand | perl -pe 's/\0//g'| head -c 10000`
    env_parallel -Slo echo ::: OK 2>&1
    a=`rand | perl -pe 's/\0//g'| head -c 50000`
    env_parallel -Slo echo THIS SHOULD ::: FAIL 2>/dev/null || echo OK
}

par_no_route_to_host() {
    echo '### no route to host with | and -j0 causes inf loop'
    # Broken in parallel-20121122 .. parallel-20181022
    # parallel-20181022 -j0 -S 185.75.195.218 echo ::: {1..11}
    via_parallel() {
	seq 11 | stdout parallel -j0 -S $1 echo
    }
    export -f via_parallel
    raw() {
	stdout ssh $1 echo
    }
    export -f raw

    # Random hosts
    findhosts() {
	ip='$(($RANDOM%256)).$(($RANDOM%256)).$(($RANDOM%256)).$(($RANDOM%256))'
	seq 10000 | parallel -N0 echo $ip | grep -v ^127
    }

    # See if the hosts fail fast
    filterhosts() {
	stdout parallel --timeout 2 -j5 ssh -o PasswordAuthentication=no {} echo |
	    perl -ne 's/ssh:.* host (\d+\.\d+\.\d+\.\d+) .* No route .*/$1/ and print; $|=1'
    }

    (
	# Cache a list of hosts that fail fast with 'No route'
	# Filter the list 5 times to make sure to get good hosts
	export -f findhosts
	export -f filterhosts
	# Run this in the background
	nice nohup bash -c 'findhosts |
	    filterhosts | filterhosts | filterhosts |
	    filterhosts | filterhosts | head > /tmp/filtered.$$
	mv /tmp/filtered.$$ /tmp/filtered.hosts
	' &
    ) &
    (
	# We just need one of each to complete
	stdout parallel --halt now,done=1 -j0 raw :::: /tmp/filtered.hosts
	stdout parallel --halt now,done=1 -j0 via_parallel :::: /tmp/filtered.hosts
    ) | perl -pe 's/(\d+\.\d+\.\d+\.\d+)/i.p.n.r/' | puniq
}

par_PARALLEL_SSHLOGIN_SSHHOST() {
    echo '### bug #56554: Introduce $PARALLEL_SSHLOGIN $PARALLEL_SSHHOST'
    (echo lo; echo zsh@lo; echo /usr/bin/ssh csh@lo; echo 1/sh@lo;
     echo 1//usr/bin/ssh tcsh@lo) |
	parallel -k --tag --nonall -S - 'whoami;echo $PARALLEL_SSHLOGIN $PARALLEL_SSHHOST' |
	LANG=C sort
}

par_filter_hosts_parallel_not_installed() {
    echo 'bug #62672: Triggered a bug with --filter-host'
    parallel -S nopathbash@lo --filter-hosts echo ::: OK
    parallel --nonall -S nopathbash@lo --filter-hosts echo OK
}

par__d_filter_hosts() {
    echo '### --filter-hosts and -0'
    echo '### https://lists.gnu.org/archive/html/parallel/2022-07/msg00002.html'
    printf 'OKa OKb ' | parallel -k -d ' ' --filter-hosts -S lo echo
    printf 'OKa1OKb1' | parallel -k -d 1 --filter-hosts -S lo echo
    printf 'OKa0OKb0' | parallel -k -d 0 --filter-hosts -S lo echo
    printf 'OKa\0OKb\0' | parallel -k -d '\0' --filter-hosts -S lo echo
    printf 'OKa\0OKb\0' | parallel -k -0 --filter-hosts -S lo echo
}

par__sshlogin_range() {
    echo '### --sshlogin with ranges'
    echo '### Jobs fail, but the important is the name of the hosts'
    doit() {
	stdout parallel --dr "$@" echo ::: 1 | sort
    }
    cluster() {
	doit -S a[00-12].nx-dom,b[2,3,5,7-11]c[1,4,6].nx-dom
    }
    devprod() {
	doit -S{prod,dev}[000-010,098-101].nx-dom
    }
    ipaddr() {
	doit -Sip'2[49-51].0.[9-11].1[09-11]'
    }
    export -f doit cluster devprod ipaddr
    parallel -k ::: cluster devprod ipaddr

}

export -f $(compgen -A function | grep par_)
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
#compgen -A function | grep par_ | sort |
compgen -A function | G par_ "$@" | LANG=C sort |
#    parallel --joblog /tmp/jl-`basename $0` --delay $D -j$P --tag -k '{} 2>&1'
    parallel --joblog /tmp/jl-`basename $0` --timeout 100 --delay 0.1 -j200% --tag -k '{} 2>&1' |
    perl -pe 's/line \d\d\d+:/line XXX:/' |
    perl -pe 's/\[\d\d\d+\]:/[XXX]:/'
