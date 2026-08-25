#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Tests for --fast mode: jobs bundled into shell-script chunks piped to a
# child parallel --pipe instance.  Each test should complete in well under 10s.

par_fast_basic() {
    echo '### --fast basic output'
    parallel --fast echo ::: a b c | sort
}

par_fast_exitcode_failures() {
    echo '### --fast --halt never: exit code equals number of failed jobs'
    parallel --fast --halt never -j4 'test {} -gt 3' ::: 1 2 3 4 5
    echo "exit=$?"
}

par_fast_exitcode_cap() {
    echo '### --fast --halt never: exit code capped at 101'
    parallel --fast --halt never -j4 'exit 1' ::: $(seq 200)
    echo "exit=$?"
}

par_fast_no_blocksize_warnings() {
    echo '### --fast: no blocksize warnings with 100k jobs'
    seq 100000 | parallel --fast echo 2>&1 1>/dev/null | grep -c 'longer than'
}

par_fast_nohalt_exitcode() {
    echo '### --fast without --halt: exit 0 even when jobs fail'
    parallel --fast -j4 'exit 1' ::: 1 2 3
    echo "exit=$?"
}

par_fast_halt_tag() {
    echo '### --fast --halt never --tag: tagged output with exit tracking'
    parallel --fast --halt never --tag 'echo {} ; test {} != b' ::: a b c | sort
    echo "exit=${PIPESTATUS[0]}"
}

par_fast_large() {
    echo '### --fast handles 1000 jobs'
    parallel --fast echo ::: $(seq 1000) | wc -l
}

par_fast_tag() {
    echo '### --fast --tag prefixes each line'
    parallel --fast --tag echo ::: a b c | sort
}

par_fast_tagstring() {
    echo '### --fast --tagstring'
    parallel --fast --tagstring 'T{}' echo ::: a b c | sort
}

par_fast_group() {
    echo '### --fast --group: output of each job appears together (no interleaving)'
    # -j1 forces sequential chunks so order is deterministic
    parallel --fast -j1 'echo start {}; echo end {}' ::: 1 2 3
}

par_fast_ungroup() {
    echo '### --fast --ungroup works without error'
    parallel --fast --ungroup echo ::: a b c | sort
    echo "exit=$?"
}

par_fast_jobslot() {
    echo '### --fast: $PARALLEL_JOBSLOT is set in chunk environment'
    # All jobs in a chunk share the chunk slot number (1..N).
    # With 4 jobs and -j2, we get up to 2 distinct slot values.
    parallel --fast -j2 'echo slot=$PARALLEL_JOBSLOT' ::: 1 2 3 4 | sort -u
}

par_fast_replacements() {
    echo '### --fast replacement strings work'
    parallel --fast echo {.} {/} {//} ::: /tmp/foo.txt
}

# === FULLY SUPPORTED ===

par_fast_compress() {
    echo '### --fast --compress'
    parallel --compress echo ::: a b c | sort
    parallel --fast --compress echo ::: a b c | sort
    seq 230 | parallel --fast --compress echo | sort -n | tail -3
}

par_fast_dryrun() {
    echo '### --fast --dry-run: no execution'
    tmpdir=$(mktemp -d)
    parallel --dry-run "touch $tmpdir/{}" ::: a b c >/dev/null 2>&1
    [ -z "$(ls -A "$tmpdir")" ] && echo "no files created"
    rm -rf "$tmpdir"
    tmpdir=$(mktemp -d)
    parallel --fast --dry-run "touch $tmpdir/{}" ::: a b c >/dev/null
    [ -z "$(ls -A "$tmpdir")" ] && echo "no files created"
    rm -rf "$tmpdir"
    tmpdir=$(mktemp -d)
    seq 230 | parallel --fast --dry-run "touch $tmpdir/{}" >/dev/null
    [ -z "$(ls -A "$tmpdir")" ] && echo "no files created"
    rm -rf "$tmpdir"
}

par_fast_dryrun_commands() {
    echo '### --fast --dry-run: commands in output'
    parallel --dry-run echo ::: a b c 2>&1 | grep -a '^echo' | sort
    parallel --fast --dry-run echo ::: a b c 2>/dev/null | grep -a '^echo' | sort
    seq 230 | parallel --fast --dry-run echo 2>/dev/null | grep -ca '^echo'
}

par_fast_jobs() {
    echo '### --fast --jobs/-j'
    parallel --jobs 2 echo ::: a b c d | sort
    parallel --fast --jobs 2 echo ::: a b c d | sort
    seq 230 | parallel --fast --jobs 2 echo | sort -n | tail -3
}

par_fast_keeporder() {
    echo '### --fast --keep-order'
    seq 5 | parallel --keep-order echo
    seq 5 | parallel --fast --keep-order echo
    seq 230 | parallel --fast --keep-order echo | diff - <(seq 230) && echo "ordered"
}

par_fast_nice() {
    echo '### --fast --nice'
    parallel --nice 10 'sh -c nice' ::: a | sort -nu
    parallel --fast --nice 10 'sh -c nice' ::: a | sort -nu
    seq 230 | parallel --fast --nice 10 'sh -c nice' | sort -nu
}

par_fast_tag() {
    echo '### --fast --tag'
    parallel --tag echo ::: a b c | sort
    parallel --fast --tag echo ::: a b c | sort
    seq 230 | parallel --fast --tag echo | sort -k2 -n | tail -3
}

par_fast_tagstring_fixed() {
    echo '### --fast --tagstring fixed string'
    parallel --tagstring 'TAG' echo ::: a b c | sort
    parallel --fast --tagstring 'TAG' echo ::: a b c | sort
    seq 230 | parallel --fast --tagstring 'TAG' echo | sort -k2 -n | tail -3
}

par_fast_tagstring_replacement() {
    echo '### --fast --tagstring with replacement'
    parallel --tagstring 'T{}' echo ::: a b c | sort
    parallel --fast --tagstring 'T{}' echo ::: a b c | sort
    seq 230 | parallel --fast --tagstring 'T{}' echo | sort -k2 -n | tail -3
}

par_fast_ungroup() {
    echo '### --fast --ungroup'
    parallel --ungroup echo ::: a b c | sort
    parallel --fast --ungroup echo ::: a b c | sort
    seq 230 | parallel --fast --ungroup echo | sort -n | tail -3
    echo "exit=$?"
}

# === SUPPORTED BUT SLOWER (replacement strings) ===

par_fast_replacement_dot() {
    echo '### --fast {.}'
    parallel echo {.} ::: foo.txt bar.py baz | sort
    parallel --fast echo {.} ::: foo.txt bar.py baz | sort
    seq 230 | sed 's/$/.txt/' | parallel --fast echo {.} | sort -n | tail -3
}

par_fast_replacement_slash() {
    echo '### --fast {/}'
    parallel echo {/} ::: /tmp/foo.txt /var/bar.py | sort
    parallel --fast echo {/} ::: /tmp/foo.txt /var/bar.py | sort
    seq 230 | sed 's|^|/tmp/|;s/$/.txt/' | parallel --fast echo {/} | sort -t. -k1 -n | tail -3
}

par_fast_replacement_slashslash() {
    echo '### --fast {//}'
    parallel echo {//} ::: /tmp/foo.txt /var/bar.py | sort
    parallel --fast echo {//} ::: /tmp/foo.txt /var/bar.py | sort
    seq 230 | awk '{print "/dir" $1 "/f.txt"}' | parallel --fast echo {//} | sort -V | tail -3
}

par_fast_replacement_dotslash() {
    echo '### --fast {/.}'
    parallel echo {/.} ::: /tmp/foo.txt /var/bar.py | sort
    parallel --fast echo {/.} ::: /tmp/foo.txt /var/bar.py | sort
    seq 230 | sed 's|^|/tmp/|;s/$/.txt/' | parallel --fast echo {/.} | sort -n | tail -3
}

par_fast_replacement_seqno() {
    echo '### --fast {#}'
    parallel -j1 'echo {#}' ::: a b c
    parallel --fast -j1 'echo {#}' ::: a b c
    seq 230 | parallel --fast -j1 'echo {#}' | tail -3
}

par_fast_replacement_slot() {
    echo '### --fast {%}'
    # {%} must equal $PARALLEL_JOBSLOT and both slots (1 and 2) must appear.
    # Small inputs all go into one chunk so slot is non-deterministic;
    # 230 inputs span multiple chunks and deterministically use both slots.
    parallel -j2 'echo {%}=$PARALLEL_JOBSLOT' ::: a b c d | sort -u
    seq 2300 | parallel --fast -j2 'echo {%}=$PARALLEL_JOBSLOT' | sort -u
}

par_fast_replacement_n() {
    echo '### --fast {n} with colsep'
    printf 'a:1\nb:2\nc:3\n' | parallel --colsep ':' 'echo {1}-{2}' | sort -n | tail
    printf 'a:1\nb:2\nc:3\n' | parallel --fast --colsep ':' 'echo {1}-{2}' | sort -n | tail
    seq 230 | awk '{print $1 ":" $1}' | parallel --fast --colsep ':' 'echo {1}-{2}' | sort -n | tail
}

par_fast_tagstring_dot() {
    echo '### --fast --tagstring with {.}'
    parallel --tagstring '{.}' echo ::: foo.txt bar.py | sort -n | tail
    parallel --fast --tagstring '{.}' echo ::: foo.txt bar.py | sort -n | tail
    seq 230 | sed 's/$/.txt/' | parallel --fast --tagstring '{.}' echo  | sort -n | tail
}

# === SUPPORTED BUT SLOWER (input sources) ===

par_fast_multisource() {
    echo '### --fast multiple :::'
    parallel echo ::: a b ::: 1 2 | sort | tail
    parallel --fast echo ::: a b ::: 1 2 | sort | tail
    parallel --fast echo ::: $(seq 23) ::: $(seq 10) | sort | tail
}

par_fast_argfile() {
    echo '### --fast -a/--arg-file'
    printf 'x\ny\nz\n' > /tmp/par_fast_argfile.txt
    parallel -a /tmp/par_fast_argfile.txt echo | sort
    parallel --fast -a /tmp/par_fast_argfile.txt echo | sort
    rm -f /tmp/par_fast_argfile.txt
    seq 230 > /tmp/par_fast_argfile_large.txt
    parallel --fast -a /tmp/par_fast_argfile_large.txt echo | sort -n | tail -3
    rm -f /tmp/par_fast_argfile_large.txt
}

par_fast_inline_argfile() {
    echo '### --fast ::::'
    printf 'a\nb\nc\n' > /tmp/par_fast_inline.txt
    parallel echo :::: /tmp/par_fast_inline.txt | sort
    parallel --fast echo :::: /tmp/par_fast_inline.txt | sort
    seq 230 > /tmp/par_fast_inline_large.txt
    parallel --fast echo :::: /tmp/par_fast_inline_large.txt | sort -n | tail -3
    rm -f /tmp/par_fast_inline.txt /tmp/par_fast_inline_large.txt
}

par_fast_null() {
    echo '### --fast -0/--null'
    printf 'a\0b\0c' | parallel -0 echo | sort
    printf 'a\0b\0c' | parallel --fast -0 echo | sort
    printf '%s\0' $(seq 230) | parallel --fast -0 echo | sort -n | tail -3
}

par_fast_delimiter() {
    echo '### --fast -d/--delimiter'
    printf 'a:b:c' | parallel -d: echo | sort
    printf 'a:b:c' | parallel --fast -d: echo | sort
    seq 230 | paste -sd: | tr -d '\n' | parallel --fast -d: echo | sort -n | tail -3
}

par_fast_colsep() {
    echo '### --fast --colsep'
    printf 'a 1\nb 2\nc 3\n' | parallel --colsep ' ' 'echo {1}={2}' | sort
    printf 'a 1\nb 2\nc 3\n' | parallel --fast --colsep ' ' 'echo {1}={2}' | sort
    seq 230 | awk '{print $1 " " $1}' | parallel --fast --colsep ' ' 'echo {1}={2}' | sort -t= -k1 -n | tail -3
}

par_fast_csv() {
    echo '### --fast --csv'
    printf '"a","1"\n"b","2"\n"c","3"\n' | parallel --csv 'echo {1}-{2}' | sort
    printf '"a","1"\n"b","2"\n"c","3"\n' | parallel --fast --csv 'echo {1}-{2}' | sort
    seq 230 | awk '{printf "\"%s\",\"%s\"\n",$1,$1}' | parallel --fast --csv 'echo {1}-{2}' | sort -t- -k1 -n | tail -3
}

par_fast_link() {
    echo '### --fast :::+'
    parallel echo ::: a b c :::+ 1 2 3 | sort
    parallel --fast echo ::: a b c :::+ 1 2 3 | sort
    parallel --fast echo ::: $(seq 230) :::+ $(seq 230) | sort -n | tail -3
}

par_fast_N2() {
    echo '### --fast -N2'
    seq 6 | parallel -N2 'echo {1}+{2}' | sort
    seq 6 | parallel --fast -N2 'echo {1}+{2}' | sort
    seq 460 | parallel --fast -N2 'echo {1}+{2}' | sort -t+ -k1 -n | tail -3
}

par_fast_m() {
    echo '### --fast -m'
    seq 4 | parallel -m -j1 echo
    seq 4 | parallel --fast -m -j1 echo
    seq 230 | parallel --fast -m -j1 echo | tr ' ' '\n' | sort -n | tail -3
}

par_fast_X() {
    echo '### --fast -X'
    seq 4 | parallel -X -j1 echo
    seq 4 | parallel --fast -X -j1 echo
    seq 230 | parallel --fast -X -j1 echo | tr ' ' '\n' | sort -n | tail -3
}

par_fast_filter() {
    echo '### --fast --filter'
    parallel --filter '{} < 4' echo ::: 1 2 3 4 5 | sort
    parallel --fast --filter '{} < 4' echo ::: 1 2 3 4 5 | sort
    seq 230 | parallel --fast --filter '{} <= 115' echo | sort -n | tail -3
}

par_fast_trim() {
    echo '### --fast --trim rl'
    printf '  a  \n  b  \n  c  \n' | parallel --trim rl echo | sort
    printf '  a  \n  b  \n  c  \n' | parallel --fast --trim rl echo | sort
    seq 230 | awk '{printf "  %s  \n", $1}' | parallel --fast --trim rl echo | sort -n | tail -3
}

# === SUPPORTED WITH DIFFERENT SEMANTICS ===

par_fast_halt_semantics() {
    echo '### --fast --halt never exit code'
    parallel --halt never 'exit {}' ::: 0 1 2
    echo "exit=$?"
    parallel --fast --halt never 'exit {}' ::: 0 1 2
    echo "exit=$?"
    seq 230 | parallel --fast --halt never '[ {} -le 220 ]'
    echo "exit=$?"
}

par_fast_timeout() {
    echo '### --fast --timeout: applies per chunk'
    parallel --timeout 3 sleep ::: 1 2 4 5
    echo "exit=$?"
    # TODO Broken - should kill after 3 sec
    parallel --fast --timeout 3 sleep ::: 1 2 4 5
    echo "exit=$?"
    # TODO Broken
    seq 230 | parallel --fast --timeout 3 sleep
    echo "exit=$?"
}

par_fast_bar() {
    echo '### --fast --bar/--eta/--progress: counts chunks not individual jobs'
    parallel --bar echo ::: a b c 2>/dev/null | sort
    # Broken - does nothing
    parallel --fast --bar echo ::: a b c 2>/dev/null | sort
    seq 230 | parallel --fast --bar echo 2>/dev/null | sort -n | tail -3
}

par_fast_joblog() {
    echo '### --fast --joblog header'
    jl=$(mktemp)
    parallel --joblog "$jl" echo ::: a b c >/dev/null
    wc -l < "$jl"
    rm -f "$jl"
    jl=$(mktemp)
    parallel --fast --joblog "$jl" echo ::: a b c >/dev/null
    wc -l < "$jl"
    rm -f "$jl"
    jl=$(mktemp)
    seq 230 | parallel --fast --joblog "$jl" echo >/dev/null
    wc -l < "$jl"
    rm -f "$jl"
}

par_fast_delay() {
    echo '### --fast --delay: applied per chunk not per job'
    parallel --delay 1 echo ::: a b c
    # TODO Broken - does nothing
    parallel --fast --delay 1 echo ::: a b c
    seq 230 | parallel --fast --delay 1 echo
}

par_fast_env() {
    echo '### --fast --env'
    export FAST_VAR=hello
    parallel --env FAST_VAR 'echo $FAST_VAR-{}' ::: a b c | sort
    parallel --fast --env FAST_VAR 'echo $FAST_VAR-{}' ::: a b c | sort
    seq 230 | parallel --fast --env FAST_VAR 'echo $FAST_VAR-{}' | grep hello | wc -l
}

par_fast_retries() {
    echo '### --fast --retries'
    parallel --retries 2 --halt never 'exit {}' ::: 1
    echo "exit>0=$([ $? -gt 0 ] && echo yes || echo no)"
    # TODO - Broken does nothing
    parallel --fast --retries 2 --halt never 'exit {}' ::: 1
    echo "exit>0=$([ $? -gt 0 ] && echo yes || echo no)"
    seq 10 | parallel --fast --retries 2 --halt never 'exit {}'
    echo "exit>0=$([ $? -gt 0 ] && echo yes || echo no)"
}

par_fast_load() {
    echo '### --fast --load/--limit/--memfree/--noswap: retries whole chunk'
    parallel --load 200% echo ::: a b c | sort
    # TODO - Broken does nothing
    parallel --fast --load 200% echo ::: a b c | sort
    seq 230 | parallel --fast --load 200% echo | sort -n | tail -3
}

par_fast_perl_expr() {
    echo '### --fast {= perl =}'
    parallel 'echo {= $_ = uc($_) =}' ::: hello world | sort
    parallel --fast 'echo {= $_ = uc($_) =}' ::: hello world | sort
    seq 230 | parallel --fast 'echo {= $_ = $_ * 2 =}' | sort -n | tail -3
}


export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1'
