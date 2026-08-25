# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Jobs that depend on the hardware
# (e.g number of CPU threads, terminal type)

par_10000_m_X() {
    echo '### Test -m with 10000 args'
    seq 10100 | perl -pe 's/$/.gif/' |
        parallel -j1 -km echo a{}b{.}c{.} |
        parallel -k --pipe --tee ::: md5sum 'perl -pe "s/(.*)/length \$1/e"' |
	perl -pe 's/^(\d)\d\d\d\d/${1}9999/'
}

par_maxlinelen_X_I() {
    echo "### Test max line length -X -I"

    seq 1 60000 | parallel -I :: -kX -j1 echo a::b::c | LC_ALL=C sort >/tmp/114-b$$;
    md5sum </tmp/114-b$$;
    export CHAR=$(cat /tmp/114-b$$ | wc -c);
    export LINES=$(cat /tmp/114-b$$ | wc -l);
    echo "Chars per line ($CHAR/$LINES): "$(echo "$CHAR/$LINES" | bc);
    rm /tmp/114-b$$
}

par_maxlinelen_m_I() {
    echo "### Test max line length -m -I"

    seq 1 60000 | parallel -I :: -km -j1 echo a::b::c | LC_ALL=C sort >/tmp/114-a$$;
    md5sum </tmp/114-a$$;
    export CHAR=$(cat /tmp/114-a$$ | wc -c);
    export LINES=$(cat /tmp/114-a$$ | wc -l);
    echo "Chars per line ($CHAR/$LINES): "$(echo "$CHAR/$LINES" | bc);
    rm /tmp/114-a$$
}

par_lines_over_130k() {
    echo '### Test of xargs -m command lines > 130k'; 
    seq 1 60000 | parallel -m -j1 echo a{}b{}c | tee >(wc >/tmp/awc$$) >(sort | md5sum) >/tmp/a$$
    wait
    CHAR=$(cat /tmp/a$$ | wc -c)
    LINES=$(cat /tmp/a$$ | wc -l)
    echo "Chars per line:" $(echo "$CHAR/$LINES" | bc)
    cat /tmp/awc$$
    rm /tmp/a$$ /tmp/awc$$

    echo '### Test of xargs -X command lines > 130k'; 
    seq 1 60000 | parallel -X -j1 echo a{}b{}c | tee >(wc >/tmp/bwc$$) >(sort | (sleep 1; md5sum)) >/tmp/b$$; 
    wait; 
    CHAR=$(cat /tmp/b$$ | wc -c); 
    LINES=$(cat /tmp/b$$ | wc -l); 
    echo "Chars per line:" $(echo "$CHAR/$LINES" | bc); 
    cat /tmp/bwc$$; 
    rm /tmp/b$$ /tmp/bwc$$

    echo '### Test of xargs -m command lines > 130k'; 
    seq 1 60000 | parallel -k -j1 -m echo | md5sum
}
 
par_xargs_bug_39787() {
    echo '### bug #39787: --xargs broken'
    perl -e 'for(1..30000){print "$_\n"}' |
	parallel --xargs -k echo |
	perl -ne 'print length $_,"\n"'
}

par_colour_failed() {
    echo '--colour-failed --colour'
    (
	parallel --colour-failed -kv 'seq {1};exit {2}' ::: 1 2 ::: 0 1 2
	parallel --colour --colour-failed -kv 'seq {1};exit {2}' ::: 1 2 ::: 0 1 2
    ) |
	# Ignore ^O, ^[(B
	perl -pe 's/\017$//; s/.\(B//g;'
}

par_ctagstring() {
    echo '### --ctag --ctagstring should be different from --tag --tagstring'
    echo tag/ctag 8 37
    parallel --tag echo ::: 1 ::: a| wc -c
    parallel --ctag echo ::: 1 ::: a | wc -c
    echo tagstring/ctagstring 10 39
    parallel --tagstring 'I{1}\tB{2}' echo ::: 1 ::: a | wc -c
    parallel --ctagstring 'I{1}\tB{2}' echo ::: 1 ::: a | wc -c
}

par_ll_color_long_line() {
    echo '### --latest-line --color with lines longer than terminal width'
    COLUMNS=30 parallel --delay 0.3 --color --tagstring '{=$_.="x"x$_=}' \
	   --ll 'echo {}00000 | sed -e "s/$/' {1..100} /'"' ::: {01..30} |
	perl -ne 's/\017$//;
                  s/.\(B//g;
	     	  s/.\[A//g;
		  /.\[K .{4}\[m/ and next;
                  /\S/ && print'| sort -u
}

par_ll_long_line() {
    echo '### --latest-line with lines longer than terminal width'
    COLUMNS=30 parallel --delay 0.3 --tagstring '{=$_.="x"x$_=}' \
	   --ll 'echo {}00000 | sed -e "s/$/' {1..100} /'"' ::: {01..30} |
	perl -ne 's/.\[A//g;
		  /.\[K .{4}\[m/ and next;
		  /x\s*$/ and next;
                  /\S/ && print'| sort -u
}

par_ll_no_newline() {
    echo 'bug #64030: parallel --ll echo -n ::: foo'
    parallel --ll echo -n ::: two lines | sort
    parallel --ll echo -n '>&2' ::: two lines | sort
    parallel --linebuffer 'echo -n last {}' ::: line
    stdout parallel --linebuffer 'echo -n last {} >&2' ::: line
    echo
}

parGONE__environment_too_big_dash() {
  myscript=$(cat <<'_EOF'
    echo 'bug #50815: env_parallel should warn if the environment is too big'
    len_var=60
    len_var_remote=43+80+50+50+50+500
    len_var_quote=31
    len_var_quote_remote=21+80+50+50+50+500
    len_fun=1
    len_fun_remote=1
    len_fun_quote=1
    len_fun_quote_remote=1
    
    . env_parallel.dash;

    repeat() {
      # Repeat input string n*1000 times
      perl -e 'print ((shift)x(eval "1000*(".shift.")"))' "$@"
    }
    short() {
      # De-repeat input
      perl -pe 's/(["x]+)/length($1)/e'
    }

    bigvar=$(repeat x $len_var)
    env_parallel echo 'x$bigvar' ::: OK_bigvar | short
    bigvar=$(repeat x $len_var_remote)
    env_parallel -S lo echo 'x$bigvar' ::: OK_bigvar_remote | short

    bigvar=$(repeat \" $len_var_quote)
    env_parallel echo 'x$bigvar' ::: OK_bigvar_quote | short
    bigvar=$(repeat \" $len_var_quote_remote)
    env_parallel -S lo echo 'x$bigvar' ::: OK_bigvar_quote_remote | short

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat x $len_fun)"'"; };'
    env_parallel echo ::: OK_bigfunc
    eval 'bigfunc() { a="'"$(repeat x $len_fun_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_remote

    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote)"'"; };'
    env_parallel echo ::: OK_bigfunc_quote
    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_quote_remote
    bigfunc() { true; }

    echo Rest should fail - functions not supported in ash

    bigvar=$(repeat x $len_var+10)
    env_parallel echo ::: fail_bigvar
    bigvar=$(repeat x $len_var_remote+10)
    env_parallel -S lo echo ::: fail_bigvar_remote

    bigvar=$(repeat \" $len_var_quote+10)
    env_parallel echo ::: fail_bigvar_quote
    bigvar=$(repeat \" $len_var_quote_remote+10)
    env_parallel -S lo echo ::: fail_bigvar_quote_remote

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat x $len_fun+10)"'"; };'
    env_parallel echo ::: fail_bigfunc-not-supported
    eval 'bigfunc() { a="'"$(repeat x $len_fun_remote+10)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_remote-not-supported

    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote+10)"'"; };'
    env_parallel echo ::: fail_bigfunc_quote-not-supported
    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote_remote+10)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_quote_remote-not-supported

    bigfunc() { true; }
_EOF
  )
  stdout ssh dash@lo "$myscript" | perl -pe 's/(\d)\d\d\d\d/${1}XXXX/g'
}

par__environment_too_big_dash() {
  myscript=$(cat <<'_EOF'
    echo 'bug #50815: env_parallel should warn if the environment is too big'
    len_var=60
    len_var_remote=43+85
    len_var_quote=31
    len_var_quote_remote=21+35
    len_fun=1
    len_fun_remote=1
    len_fun_quote=1
    len_fun_quote_remote=1
    
    . `which env_parallel.dash`;

    repeat() {
      # Repeat input string n*1000 times
      perl -e 'print ((shift)x(eval "1000*(".shift.")"))' "$@"
    }

    bigvar=$(repeat x $len_var)
    env_parallel echo ::: OK_bigvar
    bigvar=$(repeat x $len_var_remote)
    env_parallel -S lo echo ::: OK_bigvar_remote

    bigvar=$(repeat \" $len_var_quote)
    env_parallel echo ::: OK_bigvar_quote
    bigvar=$(repeat \" $len_var_quote_remote)
    env_parallel -S lo echo ::: OK_bigvar_quote_remote

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat x $len_fun)"'"; };'
    env_parallel echo ::: OK_bigfunc-not-supported
    eval 'bigfunc() { a="'"$(repeat x $len_fun_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_remote-not-supported

    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote)"'"; };'
    env_parallel echo ::: OK_bigfunc_quote-not-supported
    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_quote_remote-not-supported
    bigfunc() { true; }

    echo Rest should fail - functions not supported in dash

    bigvar=$(repeat x $len_var+10)
    env_parallel echo ::: fail_bigvar
    bigvar=$(repeat x $len_var_remote+10)
    env_parallel -S lo echo ::: fail_bigvar_remote

    bigvar=$(repeat \" $len_var_quote+10)
    env_parallel echo ::: fail_bigvar_quote
    bigvar=$(repeat \" $len_var_quote_remote+10)
    env_parallel -S lo echo ::: fail_bigvar_quote_remote

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat x $len_fun+10)"'"; };'
    env_parallel echo ::: fail_bigfunc-not-supported
    eval 'bigfunc() { a="'"$(repeat x $len_fun_remote+10)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_remote-not-supported

    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote+10)"'"; };'
    env_parallel echo ::: fail_bigfunc_quote-not-supported
    eval 'bigfunc() { a="'"$(repeat \" $len_fun_quote_remote+10)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_quote_remote-not-supported

    bigfunc() { true; }
_EOF
  )
  stdout ssh dash@lo "$myscript" | perl -pe 's/(\d)\d\d\d\d/${1}XXXX/g'
}

par__environment_too_big_zsh() {
    myscript=$(cat <<'_EOF'
    echo 'bug #50815: env_parallel should warn if the environment is too big'

    # Zsh's default env is often too big. Remove all _* functions.
    print -l ${(k)functions}|grep ^_ | while read a; do unset -f "$a"; done

    . `which env_parallel.zsh`;

    len_var=16
    len_var_remote=$len_var-6+90
    len_var_quote=$len_var
    len_var_quote_remote=$len_var+85
    len_fun=18
    len_fun_remote=$len_fun+70
    len_fun_quote=$len_fun
    len_fun_quote_remote=$len_fun-8+90

    repeat_() {
      # Repeat input string n*1000 times
      perl -e 'print ((shift)x(eval "1000*(".shift.")"))' "$@"
    }

    bigvar=$(repeat_ x $len_var)
    env_parallel echo ::: OK_bigvar
    bigvar=$(repeat_ x $len_var_remote)
    env_parallel -S lo echo ::: OK_bigvar_remote

    bigvar=$(repeat_ \" $len_var_quote)
    env_parallel echo ::: OK_bigvar_quote
    bigvar=$(repeat_ \" $len_var_quote_remote)
    env_parallel -S lo echo ::: OK_bigvar_quote_remote

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat_ x $len_fun)"'"; };'
    env_parallel echo ::: OK_bigfunc
    eval 'bigfunc() { a="'"$(repeat_ x $len_fun_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_remote

    eval 'bigfunc() { a="'"$(repeat_ \" $len_fun_quote)"'"; };'
    env_parallel echo ::: OK_bigfunc_quote
    eval 'bigfunc() { a="'"$(repeat_ \" $len_fun_quote_remote)"'"; };'
    env_parallel -S lo echo ::: OK_bigfunc_quote_remote
    bigfunc() { true; }

    echo Rest should fail

    # Add 10 or 100. It differs a bit from system to system
    bigvar=$(repeat_ x $len_var+20)
    env_parallel echo ::: fail_bigvar
    bigvar=$(repeat_ x $len_var_remote+10)
    env_parallel -S lo echo ::: fail_bigvar_remote

    bigvar=$(repeat_ \" $len_var_quote+20)
    env_parallel echo ::: fail_bigvar_quote
    bigvar=$(repeat_ \" $len_var_quote_remote+20)
    env_parallel -S lo echo ::: fail_bigvar_quote_remote

    bigvar=u
    eval 'bigfunc() { a="'"$(repeat_ x $len_fun+20)"'"; };'
    env_parallel echo ::: fail_bigfunc
    eval 'bigfunc() { a="'"$(repeat_ x $len_fun_remote+20)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_remote

    eval 'bigfunc() { a="'"$(repeat_ \" $len_fun_quote+20)"'"; };'
    env_parallel echo ::: fail_bigfunc_quote
    eval 'bigfunc() { a="'"$(repeat_ \" $len_fun_quote_remote+10)"'"; };'
    env_parallel -S lo echo ::: fail_bigfunc_quote_remote

    bigfunc() { true; }
_EOF
  )
    stdout ssh zsh@lo "$myscript" | perl -pe 's/(\d)\d\d\d\d/${1}XXXX/g'
}

par_progress() {
    (
	parallel --progress --use-sockets-instead-of-threads  true ::: a b c
	parallel --progress --use-cores-instead-of-threads    true ::: a b c
	parallel --progress --use-cpus-instead-of-cores       true ::: a b c
    ) 2>&1 | perl -pe 's/.*\r//; s/\d.\ds/9.9s/'
}

par__sockets_cores_threads() {
    echo '### Test --number-of-sockets/cores/threads'
    unset PARALLEL_CPUINFO
    unset PARALLEL_LSCPU
    parallel --number-of-sockets
    parallel --number-of-cores
    parallel --number-of-threads
    parallel --number-of-cpus

    echo '### Test --use-sockets-instead-of-threads'
    (seq 1 4 |
	 stdout parallel --use-sockets-instead-of-threads -j100% sleep) &&
	echo sockets done &
    (seq 1 4 | stdout parallel -j100% sleep) && echo threads done &
    wait
    echo 'Threads should complete first on machines with less than 8 sockets'
}

export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 10000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
