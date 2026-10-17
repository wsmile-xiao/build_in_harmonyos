#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Simple jobs that never fails
# Each should be taking 1-3s and be possible to run in parallel
# I.e.: No race conditions, no logins

par_--pipe--block-2() {
    echo '### --block -2'
    yes `seq 100` | head -c 100M | parallel -j 5 --block -2 -k --pipe wc
}

par_keep_order_make_job_1_output_fast() {
    echo '# EXAMPLE: Keep order, but make job 1 output fast'
    doit() {
      echo "$@" ERR >&2
      echo "$@" out
      sleep 0.$1
      echo "$@" ERR >&2
      echo "$@" out
    }
    export -f doit
    parallel -k -u doit {= 'seq() > 1 and $opt::ungroup = 0' =} ::: 9 1 2 3
}

par_citation_no_config_dir() {
    echo '### bug #64329: parallel --citation will loop forever unless the config dir exists'
    t=$(mktemp -d)
    echo "This should only ask once"
    echo will cite | HOME="$t" stdout parallel --citation |
    	grep "Type: 'will cite' and press enter."
    rm -r "$t"
}

par_tagstring() {
    echo '### Test --tagstring'
    parallel -j1 -X -v --tagstring a{}b echo  ::: 3 4
    parallel -j1 -k -v --tagstring a{}b echo  ::: 3 4
    parallel -j1 -k -v --tagstring a{}b echo job{#} ::: 3 4
    parallel -j1 -k -v --tagstring ajob{#}b echo job{#} ::: 3 4
}

par__quote_bugs() {
    echo '### Bug did not quote'
    echo '>' | parallel -v echo
    parallel -v echo ::: '>'
    (echo '>'; echo  2) | parallel -j1 -vX echo
    parallel -X -j1 echo ::: '>' 2

    echo '### Must not quote'; 
    echo 'echo | wc -l' | parallel -v
    parallel -v ::: 'echo | wc -l'
    echo 'echo a b c | wc -w' | parallel -v
    parallel -kv ::: 'echo a b c | wc -w' 'echo a b | wc -w'
}

par_keep_order() {
    echo '### Bug made 4 5 go before 1 2 3'
    parallel -k ::: "sleep 1; echo 1" "echo 2" "echo 3" "echo 4" "echo 5"

    echo '### Bug made 3 go before 1 2'
    parallel -kj 1 ::: "sleep 1; echo 1" "echo 2" "echo 3"
}

par__arg_sep() {
    echo '### Test basic --arg-sep'
    parallel -k echo ::: a b

    echo '### Run commands using --arg-sep'
    parallel -kv ::: 'echo a' 'echo b'

    echo '### Change --arg-sep'
    parallel --arg-sep ::: -kv ::: 'echo a' 'echo b'
    parallel --arg-sep .--- -kv .--- 'echo a' 'echo b'
    parallel --argsep ::: -kv ::: 'echo a' 'echo b'
    parallel --argsep .--- -kv .--- 'echo a' 'echo b'

    echo '### Test stdin goes to first command only'
    echo via cat | parallel --arg-sep .--- -kv .--- 'cat' 'echo b'
    echo via cat | parallel -kv ::: 'cat' 'echo b'
}

par_retired() {
    echo '### Test retired'
    stdout parallel -B foo
    stdout parallel -g
    stdout parallel -H 1
    stdout parallel -T
    stdout parallel -U foo
    stdout parallel -W foo
    stdout parallel -Y
}

par_file_rpl() {
    echo '### file as replacement string'
    TMPDIR=/tmp/parallel-local-1s/"  "/bar
    mkdir -p "$TMPDIR"
    tmp="$(mktemp)"
    (
	echo content1
	echo content2
	echo File name "$tmp"
    ) > "$tmp"
    (
	echo '# {filename}'
	parallel -k --header 0 echo {"$tmp"} :::: "$tmp"

	echo '# Conflict: both {filename} and {/regexp/rpl}'
	parallel -k --plus echo {"$tmp"} :::: "$tmp"
	echo '# --header 0 --plus'
	parallel -k --header 0 --plus echo {"$tmp"} :::: "$tmp"
	tmpd="$(mktemp -d)"
	cd "$tmpd"

	echo '# Conflict: both {filename} and {n}'
	seq 1 > 1
	seq 2 > 2
	seq 3 > 3
	parallel -k echo {1} :::: 3 2 1
	parallel -k --header 0 echo {1} :::: 3 2 1
	
	echo '# Conflict: both {filename} and {=expr=}'
	seq 3 > =chop=
	parallel -k echo  {=chop=} ::: =chop=
	parallel -k --header 0 echo  {=chop=} ::: =chop=
	rm -rf "$tmpd"
    ) | replace_tmpdir | perl -pe 's/tmp\.\w+/tmp.XXXXXX/g'
    rm "$tmp"
}

par_commandline_with_newline() {
    echo 'bug #51299: --retry-failed with command with newline'
    echo 'The format must remain the same'
    (
	parallel --jl - 'false "command
with
newlines"' ::: a b | sort

	echo resume
	parallel --resume --jl - 'false "command
with
newlines"' ::: a b c | sort

	echo resume-failed
	parallel --resume-failed --jl - 'false "command
with
newlines"' ::: a b c d | sort

	echo retry-failed
	parallel --retry-failed --jl - 'false "command
with
newlines"' ::: a b c d e | sort
    ) | perl -pe 's/\0/<null>/g;s/\d+/./g'
}

par_compute_command_len() {
    echo "### Computing length of command line"
    seq 1 2 | parallel -k -N2 echo {1} {2}
    parallel --xapply -k -a <(seq 11 12) -a <(seq 1 3) echo
    parallel -k -C %+ echo '"{1}_{3}_{2}_{4}"' ::: 'a% c %%b' 'a%c% b %d'
    parallel -k -C %+ echo {4} ::: 'a% c %%b'
}

par_skip_first_line() {
    tmp="$(mktemp)"
    (echo `seq 10000`;echo MyHeader; seq 10) |
	parallel -k --skip-first-line --pipe --block 10 --header '1' cat
    (echo `seq 10000`;echo MyHeader; seq 10) > "$tmp"
    parallel -k --skip-first-line --pipepart -a "$tmp" --block 10 --header '1' cat
}

par_long_input() {
    echo '### Long input lines should not fail if they are not used'
    longline_tsv() {
	perl -e '$a = "X"x3000000;
	  map { print join "\t", $_, $a, "$_/$a.$a", "$a/$_.$a", "$a/$a.$_\n" }
          (a..c)'
    }
    longline_tsv |
	parallel --colsep '\t' echo {1} {3//} {4/.} '{=5 s/.*\.// =}'
    longline_tsv |
	parallel --colsep '\t' echo {-5} {-3//} {-2/.} '{=-1 s/.*\.// =}'
}

par_recend_recstart_hash() {
    echo "### bug #59843: --regexp --recstart '#' fails"
    (echo '#rec1'; echo 'bar'; echo '#rec2') |
	parallel -k --regexp --pipe -N1 --recstart '#' wc
    (echo ' rec1'; echo 'bar'; echo ' rec2') |
	parallel -k --regexp --pipe -N1 --recstart ' ' wc
    (echo 'rec2';  echo 'bar#';echo 'rec2' ) |
	parallel -k --regexp --pipe -N1 --recend '#' wc
    (echo 'rec2';  echo 'bar ';echo 'rec2' ) |
	parallel -k --regexp --pipe -N1 --recend ' ' wc
}

par_sqlandworker_uninstalled_dbd() {
    echo '### bug #56096: dbi-csv no such column'
    mkdir -p /tmp/parallel-bug-56096
    sudo mv /usr/share/perl5/DBD/CSV.pm /usr/share/perl5/DBD/CSV.pm.gone
    parallel --sqlandworker csv:///%2Ftmp%2Fparallel-bug-56096/mytable echo ::: must_fail
    sudo cp /usr/share/perl5/DBD/CSV.pm.gone /usr/share/perl5/DBD/CSV.pm
    parallel --sqlandworker csv:///%2Ftmp%2Fparallel-bug-56096/mytable echo ::: works
}

par_results_compress() {
    tmpdir="$(mktemp)"
    rm -r "$tmpdir"
    parallel --results "$tmpdir" --compress echo ::: 1
    cat "$tmpdir"/*/*/stdout | pzstd -qdc

    rm -r "$tmpdir"
    parallel --results "$tmpdir" echo ::: 1
    cat "$tmpdir"/*/*/stdout

    rm -r "$tmpdir"
    parallel --results "$tmpdir" --compress echo ::: '  ' /
    cat "$tmpdir"/*/*/stdout | pzstd -qdc
    
    rm -r "$tmpdir"
    parallel --results "$tmpdir" echo ::: '  ' /
    cat "$tmpdir"/*/*/stdout

    rm -r "$tmpdir"
}

par_open_files_blocks() {
    echo 'bug #38439: "open files" with --files --pipe blocks after a while'
    ulimit -n 28
    yes "`seq 3000`" |
	head -c 20M |
	stdout parallel -j10 --pipe -k echo {#} of 21 |
	grep -v 'No more file handles.' |
	grep -v 'Only enough file handles to run .* jobs in parallel.' |
	grep -v 'Raising ulimit -n or /etc/security/limits.conf' |
	grep -v 'Try running .parallel -j0 -N .* --pipe parallel -j0.' |
	grep -v 'or increasing .ulimit -n. .try: ulimit -n .ulimit -Hn..' |
	grep -v 'or increasing .nofile. in /etc/security/limits.conf' |
	grep -v 'or increasing /proc/sys/fs/file-max'
}

par_pipe_unneeded_procs() {
    echo 'bug #34241: --pipe should not spawn unneeded processes - part 2'
    tmp="$(mktemp -d)"
    cd "$tmp"
    seq 500 | parallel --tmpdir . -j10 --pipe --block 1k --files wc >/dev/null
    ls *.par | wc -l; rm *.par
    seq 500 | parallel --tmpdir . -j10 --pipe --block 1k --files --dry-run wc >/dev/null
    echo No .par should exist
    stdout ls *.par
    cd ..
    rm -r "$tmp"
}

par_interactive() {
    echo '### Test -p --interactive'
    cat >/tmp/parallel-script-for-expect <<_EOF
#!/bin/bash

seq 1 3 | parallel -k -p "sleep 0.1; echo opt-p"
seq 1 3 | parallel -k --interactive "sleep 0.1; echo opt--interactive"
_EOF
    chmod 755 /tmp/parallel-script-for-expect

    (
	expect -b - <<_EOF
spawn /tmp/parallel-script-for-expect
expect "echo opt-p 1"
send "y\n"
expect "echo opt-p 2"
send "n\n"
expect "echo opt-p 3"
send "y\n"
expect "opt-p 1"
expect "opt-p 3"
expect "echo opt--interactive 1"
send "y\n"
expect "echo opt--interactive 2"
send "n\n"
#expect "opt--interactive 1"
expect "echo opt--interactive 3"
send "y\n"
expect "opt--interactive 3"
send "\n"
_EOF
	echo
    ) | perl -ne 's/\r//g;/\S/ and print' |
	# Race will cause the order to change
	LC_ALL=C sort
}

par__replacement_rename() {
    echo "### Test --basenamereplace"
    parallel -j1 -k -X --basenamereplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --basenamereplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b

    echo "### Test --bnr"
    parallel -j1 -k -X --bnr FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --bnr FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b

    echo "### Test --extensionreplace"
    parallel -j1 -k -X --extensionreplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --extensionreplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b

    echo "### Test --er"
    parallel -j1 -k -X --er FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --er FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b

    echo "### Test --basenameextensionreplace"
    parallel -j1 -k -X --basenameextensionreplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --basenameextensionreplace FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b

    echo "### Test --bner"
    parallel -j1 -k -X --bner FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
    parallel -k --bner FOO echo FOO ::: /a/b.c a/b.c b.c /a/b a/b b
}

par_replacement_strings() {
    echo "### Test {/}"
    parallel -j1 -k -X echo {/} ::: /a/b.c a/b.c b.c /a/b a/b b
    
    echo "### Test {/.}"
    parallel -j1 -k -X echo {/.} ::: /a/b.c a/b.c b.c /a/b a/b b
    
    echo "### Test {#/.}"
    parallel -j1 -k -X echo {2/.} ::: /a/number1.c a/number2.c number3.c /a/number4 a/number5 number6
    
    echo "### Test {#/}"
    parallel -j1 -k -X echo {2/} ::: /a/number1.c a/number2.c number3.c /a/number4 a/number5 number6
    
    echo "### Test {#.}"
    parallel -j1 -k -X echo {2.} ::: /a/number1.c a/number2.c number3.c /a/number4 a/number5 number6
}

par_bug34241() {
    echo "### bug #34241: --pipe should not spawn unneeded processes"
    echo | parallel -r -j2 -N1 --pipe md5sum -c && echo OK
}

par_test_gt_quoting() {
    echo '### Test of quoting of > bug'
    echo '>/dev/null' | parallel echo

    echo '### Test of quoting of > bug if line continuation'
    (echo '> '; echo '> '; echo '>') | parallel --max-lines 3 echo
}

par_trailing_space_line_continuation() {
    echo '### Test of trailing space continuation'
    (echo foo; echo '';echo 'ole ';echo bar;echo quux) | xargs -r -L2 echo
    (echo foo; echo '';echo 'ole ';echo bar;echo quux) | parallel -kr -L2 echo
    parallel -kr -L2 echo ::: foo '' 'ole ' bar quux

    echo '### Test of trailing space continuation with -E eof'
    (echo foo; echo '';echo 'ole ';echo bar;echo quux) | xargs -r -L2 -E bar echo
    (echo foo; echo '';echo 'ole ';echo bar;echo quux) | parallel -kr -L2 -E bar echo
    parallel -kr -L2 -E bar echo ::: foo '' 'ole ' bar quux
}

par__mix_triple_colon_with_quad_colon() {
    echo '### Test :::: mixed with :::'
    echo '### Test :::: < ::: :::'
    parallel -k echo {1} {2} {3} :::: <(seq 6 7) ::: 4 5 ::: 1 2 3
    
    echo '### Test :::: <  < :::: <'
    parallel -k echo {1} {2} {3} :::: <(seq 6 7) <(seq 4 5) :::: <(seq 1 3)
    
    echo '### Test -a ::::  < :::: <'
    parallel -k -a <(seq 6 7) echo {1} {2} {3} :::: <(seq 4 5) :::: <(seq 1 3)
    
    echo '### Test -a -a :::'
    parallel -k -a <(seq 6 7) -a <(seq 4 5) echo {1} {2} {3} ::: 1 2 3
    
    echo '### Test -a - -a :::'
    seq 6 7 | parallel -k -a - -a <(seq 4 5) echo {1} {2} {3} ::: 1 2 3
    
    echo '### Test :::: < - :::'
    seq 4 5 | parallel -k echo {1} {2} {3} :::: <(seq 6 7) - ::: 1 2 3
}

par_test_E() {
    echo '### Test -E'
    seq 1 100 | parallel -k -E 5 echo :::: - ::: 2 3 4 5 6 7 8 9 10 :::: <(seq 3 11)
    
    echo '### Test -E one empty'
    seq 1 100 | parallel -k -E 3 echo :::: - ::: 2 3 4 5 6 7 8 9 10 :::: <(seq 3 11)
    
    echo '### Test -E 2 empty'
    seq 1 100 | parallel -k -E 3 echo :::: - ::: 3 4 5 6 7 8 9 10 :::: <(seq 3 11)
    
    echo '### Test -E all empty'
    seq 3 100 | parallel -k -E 3 echo :::: - ::: 3 4 5 6 7 8 9 10 :::: <(seq 3 11)
}

par_test_job_number() {
    echo '### Test {#}'
    seq 1 10 | parallel -k echo {#}
}

par_jobslot_jobnumber_pipe() {
    echo '### Test bug #43376: {%} and {#} with --pipe'
    echo foo | parallel -q --pipe -k echo {#}
    echo foo | parallel --pipe -k echo {%}
    echo foo | parallel -q --pipe -k echo {%}
    echo foo | parallel --pipe -k echo {#}
}

par_replacement_string_as_part_of_command() {
    echo '### {} as part of the command'
    echo p /bin/ls | parallel l{= s/p/s/ =}
    echo /bin/ls-p | parallel --colsep '-' l{=2 s/p/s/ =} {1}
    echo s /bin/ls | parallel l{}
    echo /bin/ls | parallel ls {}
    echo ls /bin/ls | parallel {}
    echo ls /bin/ls | parallel
}

par_test_m_X() {
    echo '### Test -m vs -X'
    (echo foo;echo bar;echo joe.gif) | parallel -j1 -km echo 1{}2{.}3 A{.}B{.}C
    (echo foo;echo bar;echo joe.gif) | parallel -j1 -kX echo 1{}2{.}3 A{.}B{.}C
    seq 1 6 | parallel -k printf '{}.gif\\n' | parallel -j1 -km echo a{}b{.}c{.}
    seq 1 6 | parallel -k printf '{}.gif\\n' | parallel -j1 -kX echo a{}b{.}c{.}

    echo '### Test -q {.}'
    echo a | parallel -qX echo  "'"{.}"' "
    echo a | parallel -qX echo  "'{.}'"
}

par_testquote() {
    testquote() {
	printf '"#&/\n()*=?'"'" |
	    PARALLEL_SHELL="$1" parallel -0 echo
    }
    export -f testquote
    # "sash script" does not work
    # "sash -f script" does, but is currently not supported by GNU Parallel
    parallel --tag -k testquote ::: bash csh dash fdsh fish fizsh ksh ksh93 mksh posh rbash rc rzsh "sash -f" sh static-sh tcsh yash zsh
    # "fdsh" is currently not supported by GNU Parallel:
    #        It gives ioctl(): Interrupted system call
    parallel --tag -k testquote ::: fdsh
}

par_basic_halt() {
    cpuburn=$(mktemp)
    cpuburn2=$(mktemp)
    (echo '#!/usr/bin/perl'
     echo "eval{setpriority(0,0,9)}; while(1){}") > "$cpuburn"
    chmod 700 "$cpuburn"
    cp -a "$cpuburn" "$cpuburn2"
    qcpuburn=$(parallel -0 --shellquote ::: "$cpuburn")
    qcpuburn2=$(parallel -0 --shellquote ::: "$cpuburn2")
    
    parallel -0 -j4 --halt 2 ::: 'sleep 1' "$qcpuburn" false;
    killall $(basename "$cpuburn") 2>/dev/null &&
	echo ERROR: cpuburn should already have been killed
    parallel -0 -j4 --halt -2 ::: 'sleep 1' "$qcpuburn2" true;
    killall $(basename "$cpuburn2") 2>/dev/null &&
	echo ERROR: cpuburn2 should already have been killed
    rm "$cpuburn" "$cpuburn2"

    parallel --halt error echo ::: should not print
    parallel --halt soon echo ::: should not print
    parallel --halt now echo ::: should not print
}

par_bug37042() {
    echo '### bug #37042: -J foo is taken from the whole command line - not just the part before the command'
    echo '--tagstring foo' > ~/.parallel/bug_37042_profile; 
    parallel -J bug_37042_profile echo ::: tag_with_foo; 
    parallel --tagstring a -J bug_37042_profile echo ::: tag_with_a; 
    parallel --tagstring a echo -J bug_37042_profile ::: print_-J_bug_37042_profile
    
    echo '### Bug introduce by fixing bug #37042'
    parallel --xapply -a <(printf 'abc') --colsep '\t' echo {1}
}

par_header() {
    echo "### Test --header with -N"
    (echo h1; echo h2; echo 1a;echo 1b; echo 2a;echo 2b; echo 3a) |
	parallel -j1 --pipe -N2 -k --header '.*\n.*\n' echo Start\;cat \; echo Stop
    
    echo "### Test --header with --block 1k"
    (echo h1; echo h2; perl -e '$a="x"x110;for(1..22){print $_,$a,"\n"}') |
	parallel -j1 --pipe -k --block 1k --header '.*\n.*\n' echo Start\;cat \; echo Stop

    echo "### Test --header with multiple :::"
    parallel --header : echo {a} {b} {1} {2} ::: b b1 ::: a a2
}

par_profiles_with_space() {
    echo '### bug #42902: profiles containing arguments with space'
    orig_parallel=$PARALLEL
    echo "--rpl 'FULLPATH chomp(\$_=\"/bin/bash=\".\`readlink -f \$_\`);' " > ~/.parallel/FULLPATH; 
    parallel -JFULLPATH echo FULLPATH ::: $0
    PARALLEL="$orig_parallel --rpl 'FULLPATH chomp(\$_=\"/bin/bash=\".\`readlink -f \$_\`);' -v" parallel  echo FULLPATH ::: "$0"
    PARALLEL="$orig_parallel --rpl 'FULLPATH chomp(\$_=\"/bin/bash=\".\`readlink -f \$_\`);' perl -e \'print \\\"@ARGV\\\n\\\"\' " parallel With script in \\\$PARALLEL FULLPATH ::: . |
	replace_tmpdir |
	perl -pe 's:parallel./:parallel/:'
}

par_pxz_complains() {
    echo 'bug #44250: pxz pre-2020 complains File format not recognized but decompresses anyway'

    # The first line dumps core if run from make file. Why?!
    stdout parallel --compress --compress-program pixz ls /{} ::: OK-if-missing-file
    stdout parallel --compress --compress-program pixz --decompress-program 'pixz -d' ls /{}  ::: OK-if-missing-file
    stdout parallel --compress --compress-program pixz --decompress-program 'pixz -d' true ::: OK-if-no-output
    stdout parallel --compress --compress-program pixz true ::: OK-if-no-output
}

par_result() {
    echo "### Test --results"
    mkdir -p /tmp/parallel_results_test
    parallel -k --results /tmp/parallel_results_test/testA echo {1} {2} ::: I II ::: III IIII
    cat /tmp/parallel_results_test/testA/*/*/*/*/stdout | LC_ALL=C sort
    ls /tmp/parallel_results_test/testA/*/*/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testA*

    echo "### Test --res"
    mkdir -p /tmp/parallel_results_test
    parallel -k --res /tmp/parallel_results_test/testD echo {1} {2} ::: I II ::: III IIII
    cat /tmp/parallel_results_test/testD/*/*/*/*/stdout | LC_ALL=C sort
    ls /tmp/parallel_results_test/testD/*/*/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testD*

    echo "### Test --result"
    mkdir -p /tmp/parallel_results_test
    parallel -k --result /tmp/parallel_results_test/testE echo {1} {2} ::: I II ::: III IIII
    cat /tmp/parallel_results_test/testE/*/*/*/*/stdout | LC_ALL=C sort
    ls /tmp/parallel_results_test/testE/*/*/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testE*

    echo "### Test --results --header :"
    mkdir -p /tmp/parallel_results_test
    parallel -k --header : --results /tmp/parallel_results_test/testB echo {1} {2} ::: a I II ::: b III IIII
    cat /tmp/parallel_results_test/testB/*/*/*/*/stdout | LC_ALL=C sort
    ls /tmp/parallel_results_test/testB/*/*/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testB*

    echo "### Test --results --header : named - a/b swapped"
    mkdir -p /tmp/parallel_results_test
    parallel -k --header : --results /tmp/parallel_results_test/testC echo {a} {b} ::: b III IIII ::: a I II
    cat /tmp/parallel_results_test/testC/*/*/*/*/stdout | LC_ALL=C sort
    ls /tmp/parallel_results_test/testC/*/*/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testC*

    echo "### Test --results --header : piped"
    mkdir -p /tmp/parallel_results_test
    (echo Col; perl -e 'print "backslash\\tab\tslash/null\0eof\n"') | parallel  --header : --result /tmp/parallel_results_test/testF true
    cat /tmp/parallel_results_test/testF/*/*/*/*/stdout | LC_ALL=C sort
    find /tmp/parallel_results_test/testF/*/*/* | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testF*

    echo "### Test --results --header : piped - non-existing column header"
    mkdir -p /tmp/parallel_results_test
    (printf "Col1\t\n"; printf "v1\tv2\tv3\n"; perl -e 'print "backslash\\tab\tslash/null\0eof\n"') |
	parallel --header : --result /tmp/parallel_results_test/testG true
    cat /tmp/parallel_results_test/testG/*/*/*/*/stdout | LC_ALL=C sort
    find /tmp/parallel_results_test/testG/ | LC_ALL=C sort
    rm -rf /tmp/parallel_results_test/testG*
}

par_result_replace() {
    echo '### bug #49983: --results with {1}'
    parallel --results /tmp/par_{}_49983 -k echo ::: foo bar baz
    cat /tmp/par_*_49983
    find /tmp/par_*_49983 | LC_ALL=C sort
    rm -rf /tmp/par_*_49983

    parallel --results /tmp/par_{}_49983 -k echo ::: foo bar baz ::: A B C
    cat /tmp/par_*_49983
    find /tmp/par_*_49983 | LC_ALL=C sort
    rm -rf /tmp/par_*_49983

    parallel --results /tmp/par_{1}-{2}_49983 -k echo ::: foo bar baz ::: A B C
    cat /tmp/par_*_49983
    find /tmp/par_*_49983 | LC_ALL=C sort
    rm -rf /tmp/par_*_49983

    parallel --results /tmp/par__49983 -k echo ::: foo bar baz ::: A B C
    cat /tmp/par_*_49983/*/*/*/*/stdout
    find /tmp/par_*_49983 | LC_ALL=C sort
    rm -rf /tmp/par_*_49983

    parallel --results /tmp/par__49983 --header : -k echo ::: foo bar baz ::: A B C
    cat /tmp/par_*_49983/*/*/*/*/stdout
    find /tmp/par_*_49983 | LC_ALL=C sort
    rm -rf /tmp/par_*_49983

    parallel --results /tmp/par__49983-{}/ --header : -k echo ::: foo bar baz ::: A B C
    cat /tmp/par_*_49983*/stdout
    find /tmp/par_*_49983-* | LC_ALL=C sort
    rm -rf /tmp/par_*_49983-*
}

par_incomplete_linebuffer() {
    echo 'bug #51337: --lb does not kill jobs at sigpipe'
    cat > /tmp/parallel--lb-test <<'_EOF'
#!/usr/bin/perl

while(1){ print ++$t,"\n"}
_EOF
    chmod +x /tmp/parallel--lb-test

    parallel --lb /tmp/parallel--lb-test ::: 1 | head
    # Should be empty
    ps aux | grep parallel[-]-lb-test
}

par_header_parens() {
    echo 'bug #49538: --header and {= =}'

    parallel --header : echo '{=v2=}{=v1 $_=Q($_)=}' ::: v1 K ::: v2 O
    parallel --header : echo '{2}{=1 $_=Q($_)=}' ::: v2 K ::: v1 O
    parallel --header : echo {var/.} ::: var sub/dir/file.ext
    parallel --header : echo {var//} ::: var sub/dir/file.ext
    parallel --header : echo {var/.} ::: var sub/dir/file.ext
    parallel --header : echo {var/} ::: var sub/dir/file.ext
    parallel --header : echo {var.} ::: var sub/dir/file.ext
}

par__pipe_compress_blocks() {
    echo "### bug #41482: --pipe --compress blocks at different -j/seq combinations"
    seq 1 | parallel -k -j2 --compress -N1 -L1 --pipe cat
    echo echo 1-4 + 1-4
    seq 4 | parallel -k -j3 --compress -N1 -L1 -vv echo
    echo 4 times wc to stderr to stdout
    (seq 4 | parallel -k -j3 --compress -N1 -L1 --pipe wc '>&2') 2>&1 >/dev/null
    echo 1 2 3 4
    seq 4 | parallel -k -j3 --compress echo
    echo 1 2 3 4
    seq 4 | parallel -k -j1 --compress echo
    echo 1 2
    seq 2 | parallel -k -j1 --compress echo
    echo 1 2 3
    seq 3 | parallel -k -j2 --compress -N1 -L1 --pipe cat
}

par_too_long_line_X() {
    echo 'bug #54869: Long lines break'
    seq 3850 |
	parallel -Xj1 'echo {} {} {} {} {} {} {} {} {} {} {} {} {} {} | wc' |
	perl -pe 's/(\d)\d\d\d\d/${1}9999/g'
}

par_null_resume() {
    echo '### --null --resume --jl'
    log=/tmp/null-resume-$$.log

    true > "$log"
    printf "%s\n" a b c | parallel --resume -k --jl $log echo
    printf "%s\n" a b c | parallel --resume -k --jl $log echo
    true > "$log"
    printf "%s\0" A B C | parallel --null --resume -k --jl $log echo
    printf "%s\0" A B C | parallel --null --resume -k --jl $log echo
    rm "$log"
}

par_pipepart_block() {
    echo '### --pipepart --block -# (# < 0)'

    seq 1000 > /run/shm/parallel$$
    parallel -j2 -k --pipepart echo {#} :::: /run/shm/parallel$$
    parallel -j2 -k --block -1 --pipepart echo {#}-2 :::: /run/shm/parallel$$
    parallel -j2 -k --block -2 --pipepart echo {#}-4 :::: /run/shm/parallel$$
    parallel -j2 -k --block -10 --pipepart echo {#}-20 :::: /run/shm/parallel$$
    rm /run/shm/parallel$$
}

par_block_negative_prefix() {
    tmp="$(mktemp)"
    seq 100000 > "$tmp"
    echo '### This should generate 10*2 jobs'
    parallel -j2 -a "$tmp" --pipepart --block -0.01k -k md5sum | wc
    rm "$tmp"
}

par_bug45691() {
    echo 'bug #45691: Accessing multiple arguments in {= =}'
    # OK:
    parallel echo {= '$arg[1] eq 2 and $job->skip()' =} ::: {1..5}
    # Failed due to --keep-order because printing is looking for job 2
    parallel --keep-order echo {= '$arg[1] eq 2 and $job->skip()' =} ::: {1..5}
}

par_filter_no_halt() {
    echo '### --filter + --halt: filtered jobs must not trigger halt failure'
    parallel --halt soon,fail=1 --filter '(-e "{}")' echo ::: /tmp/recent-noexist /tmp/recent-noexist2
    echo "exit:$?"
}

par_filter_no_retries() {
    echo '### --filter + --retries: filtered jobs must not trigger retries'
    parallel -u --retries 3 --filter '{} % 2' 'echo ran {};false' ::: 1 2 3
    echo "exit:$?"
}

par_skip_in_expr() {
    echo '### skip() in {= =} with --keep-order: must print a c (not just a)'
    parallel -k echo {= '$_ eq "b" and $job->skip()' =} ::: a b c
}

par_skip_no_halt() {
    echo '### skip() must not count as failure for --halt'
    parallel -k --halt soon,fail=1 echo '{= $job->skip() =}' ::: a b c
    echo "exit:0=$?"
    parallel -k --halt soon,fail=1 exit '{= $job->skip() =}' ::: 1 2 3
    echo "exit:0=$?"
}

export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | LC_ALL=C sort |
    parallel --timeout 1000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g;'
