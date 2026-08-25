#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Run parts from parallel-local-ssh7.sh that fail often
# I think there is a race condition in fish

par__man_fish() {
    echo '### fish'
    myscript=$(cat <<'_EOF'
    echo "### From man env_parallel"

    env_parallel --session
    alias myecho='echo aliases with \= \& \" \!'" \'"
    myecho work
    env_parallel myecho ::: work
    env_parallel -S server myecho ::: work
    env_parallel --env myecho myecho ::: work
    env_parallel --env myecho -S server myecho ::: work

    # multiline aliases does not work in fish

    function myfunc
      echo functions 'with  = & " !'" '" $argv;
    end
    myfunc work
    env_parallel myfunc ::: work
    env_parallel -S server myfunc ::: work
    env_parallel --env myfunc myfunc ::: work
    env_parallel --env myfunc -S server myfunc ::: work

    set myvar 'variables with  = & " !'" '"
    echo "$myvar" work
    env_parallel echo '$myvar' ::: work
    env_parallel -S server echo '$myvar' ::: work
    env_parallel --env myvar echo '$myvar' ::: work
    env_parallel --env myvar -S server echo '$myvar' ::: work

    set multivar 'multiline
    variables with  = & " !'" '"
    echo "$multivar" work
    env_parallel echo '"$multivar"' ::: work
    env_parallel -S server echo '"$multivar"' ::: work
    env_parallel --env multivar echo '"$multivar"' ::: work
    env_parallel --env multivar -S server echo '"$multivar"' ::: work

    set myarray arrays 'with  = & " !'" '" work, too
    echo $myarray[1] $myarray[2] $myarray[3] $myarray[4]
    echo "# these 4 fail often. Race condition?"
    env_parallel -k echo '$myarray[{}]' ::: 1 2 3 4
    env_parallel -k -S server echo '$myarray[{}]' ::: 1 2 3 4
    env_parallel -k --env myarray echo '$myarray[{}]' ::: 1 2 3 4
    env_parallel -k --env myarray -S server echo '$myarray[{}]' ::: 1 2 3 4
    env_parallel --argsep --- env_parallel -k echo ::: multi level --- env_parallel

    env_parallel ::: true false true false
    echo exit value $status should be 2

    env_parallel --no-such-option >/dev/null
    echo exit value $status should be 255 `sleep 1`
_EOF
	    )
    ssh fish@lo "$myscript"
    #| LC_ALL=C sort
}

par_--env_underscore_fish() {
    echo '### fish'
    myscript=$(cat <<'_EOF'
    echo "Fish is broken"
    echo "### Testing of --env _"

    source (which env_parallel.fish)
    true > ~/.parallel/ignored_vars;

    alias not_copied_alias="echo BAD"
    function not_copied_func
      echo BAD
    end
    set not_copied_var "BAD";
    set not_copied_array BAD BAD BAD;
#    env_parallel --record-env;
    env_parallel --session;
    alias myecho="echo \$myvar aliases";
    function myfunc
      myecho $myarray functions $argv
    end
    set myvar "variables in";
    set myarray and arrays in;

    echo Test copying;
    env_parallel myfunc ::: work;
    env_parallel -S server myfunc ::: work;
    env_parallel --env myfunc,myvar,myarray,myecho myfunc ::: work;
    env_parallel --env myfunc,myvar,myarray,myecho -S server myfunc ::: work;
    env_parallel --env _ myfunc ::: work;
    env_parallel --env _ -S server myfunc ::: work;

#    echo Test ignoring;
#    env_parallel --env _ -S server not_copied_alias ::: error=OK;
#    env_parallel --env _ -S server not_copied_func ::: error=OK;
#    env_parallel --env _ -S server echo \$not_copied_var ::: error=OK;
#    env_parallel --env _ -S server echo \$not_copied_array ::: error=OK;
#
#    echo Test single ignoring;
#    echo myvar > ~/.parallel/ignored_vars;
#    env_parallel --env _ myfunc ::: work;
#    sleep 0.1
#    env_parallel --env _ -S server myfunc ::: work;
#    sleep 0.1
#    echo myarray >> ~/.parallel/ignored_vars;
#    env_parallel --env _ myfunc ::: work;
#    env_parallel --env _ -S server myfunc ::: work;
#    echo myecho >> ~/.parallel/ignored_vars;
#    env_parallel --env _ myfunc ::: work;
#    echo "OK if   ^^^^^^^^^^^^^^^^^ no myecho" >&2;
#    env_parallel --env _ -S server myfunc ::: work;
#    echo "OK if   ^^^^^^^^^^^^^^^^^ no myecho" >&2;
#    echo myfunc >> ~/.parallel/ignored_vars;
#    env_parallel --env _ myfunc ::: work;
#    echo "OK if   ^^^^^^^^^^^^^^^^^ no myfunc" >&2;
#    env_parallel --env _ -S server myfunc ::: work;
#    echo "OK if   ^^^^^^^^^^^^^^^^^ no myfunc" >&2;
_EOF
	    )
    # Old versions of fish sometimes throw up bugs all over,
    # but seem to work OK otherwise. So ignore these errors.
    stdout ssh fish@lo "$myscript" |
	perl -ne '/^\^|fish:|fish\(/ and next; print' |
	perl -pe 's/^[ ~^]+$//g'
}


par_funky_fish() {
    myscript=$(cat <<'_EOF'
    env_parallel --session
    set myvar "myvar  works"
    setenv myenvvar "myenvvar  works"

    set funky (perl -e "print pack \"c*\", 1..255")
    # 10 and 30 cause problems
    setenv funkyenv (perl -e "print pack \"c*\", 1..9,11..29,31..255")

    set myarray "" array_val2 3 "" 5 "  space  6  "

    # Assoc arrays do not exist
    #typeset -A assocarr
    #assocarr[a]=assoc_val_a
    #assocarr[b]=assoc_val_b
    alias alias_echo="echo 3 arg";

    function func_echo
      echo $argv;
      echo "$myvar"
      echo "$myenvvar"
      echo "$myarray[6]"
    # Assoc arrays do not exist in fish
    #  echo ${assocarr[a]}
      echo
      echo
      echo
      echo Funky-"$funky"-funky
      echo Funkyenv-"$funkyenv"-funkyenv
      echo
      echo
      echo
    end

    env_parallel alias_echo ::: alias_works
    env_parallel func_echo ::: function_works
    env_parallel -S fish@lo alias_echo ::: alias_works_over_ssh
    env_parallel -S fish@lo func_echo ::: function_works_over_ssh
    echo
    echo "$funky" | parallel --shellquote
_EOF
	    )
    ssh fish@lo "$myscript"
}

par_env_parallel_fish() {
    myscript=$(cat <<'_EOF'
    echo 'bug #50435: Remote fifo broke in 20150522'
    # Due to $PARALLEL_TMP being transferred
    env_parallel --session
    set OK OK
    echo data from stdin | env_parallel --pipe -S lo --fifo 'cat {}; and echo $OK'
    echo data from stdin | env_parallel --pipe -S lo --cat 'cat {}; and echo $OK'
    echo OK: 0==$status
    echo '### Test failing command with --cat'
    echo data from stdin | env_parallel --pipe -S lo --cat 'cat {}; false'
    echo OK: 1==$status
    echo data from stdin | parallel --pipe -S lo --cat 'cat {}; false'
    echo OK: 1==$status
_EOF
	    )
    ssh fish@lo "$myscript"
}

par_env_parallel_--session_fish() {
    myscript=$(cat <<'_EOF'
    . (which env_parallel.fish)

    echo '### Test env_parallel --session'

    alias aliasbefore='echo before'
    set varbefore 'before'
    function funcbefore
      echo 'before' "$argv"
    end
    set arraybefore array before
    env_parallel --session
    # stuff defined
    env_parallel aliasbefore ::: must_fail
    env_parallel -S lo aliasbefore ::: must_fail
    env_parallel funcbefore ::: must_fail
    env_parallel -S lo funcbefore ::: must_fail
    env_parallel echo '$varbefore' ::: no_before
    env_parallel -S lo echo '$varbefore' ::: no_before
    env_parallel echo '$arraybefore' ::: no_before
    env_parallel -S lo echo '$arraybefore' ::: no_before
    alias aliasafter='echo after'
    set varafter 'after'
    function funcafter
      echo 'after' "$argv"
    end
    set arrayafter array after
    env_parallel aliasafter ::: aliasafter_OK
    env_parallel -S lo aliasafter ::: aliasafter_OK
    env_parallel funcafter ::: funcafter_OK
    env_parallel -S lo funcafter ::: funcafter_OK
    env_parallel echo '$varafter' ::: varafter_OK
    env_parallel -S lo echo '$varafter' ::: varafter_OK
    env_parallel echo '$arrayafter' ::: arrayafter_OK
    env_parallel -S lo echo '$arrayafter' ::: arrayafter_OK
    set -e PARALLEL_IGNORED_NAMES
_EOF
	    )
    ssh fish@lo "$myscript" 2>&1 |
	perl -pe 's/^[ ~^]+$//g'
}

export -f $(compgen -A function | grep par_)

clean_output() {
    perl -pe 's/line \d\d+/line 99/g;
              s/\d+ >= \d+/999 >= 999/;
              s/sh:? \d?\d\d:/sh: 999:/;
              s/:\d?\d\d:/:999:/;
              s/sh\[\d+\]/sh[999]/;
	      s/.*(tange|zenodo).*//i;
	      s:/usr/bin:/bin:g;
	      s:/tmp/par-job-\d+_.....\[\d+\]:script[9]:g;
	      s!/tmp/par-job-\d+_.....!script!g;
    	      s/script: \d\d+/script: 99/g;
	      '
}

compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --joblog /tmp/jl-`basename $0` -j1 --retries 2 --tag -k '{} 2>&1' |
    clean_output
