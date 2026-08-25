#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# SSH only allowed to localhost/lo

par_trailing_space_sshlogin() {
    echo '### trailing space in sshlogin'
    echo 'sshlogin trailing space' |
	parallel  --sshlogin "ssh -l parallel localhost " echo
}

par_special_char_trc() {
    echo '### Special char file and dir transfer return and cleanup'
    srcdir=/dev/shm/par_special_char_trc
    wd="$srcdir"_wd
    mkdir "$srcdir"
    cd "$srcdir"
    mkdir -p d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
    echo local OK > d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/f"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
    ssh parallel@lo rm -rf "$wd"/d'*'/
    mytouch() {
	cat d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/f"`perl -e 'print pack("c*",1..9,11..46,48..255)'`" \
	    > d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/g"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
	echo remote OK >> d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/g"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
    }
    export -f mytouch
    parallel --env mytouch -Sparallel@lo --wd "$wd" --transfer --return {=s:/f:/g:=} mytouch \
	     ::: d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/f"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
    cat d"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"/g"`perl -e 'print pack("c*",1..9,11..46,48..255)'`"
    rm -rf "$srcdir"
    # TODO Should be changed to --return '{=s:/f:/g:=}' and tested with csh - is error code kept?
}

par_rpl_perlexpr_not_used_in_command() {
    echo '### Uniq {=perlexpr=} in return - not used in command'
    cd /tmp
    rm -f /tmp/parallel_perlexpr.2Parallel_PerlexPr
    echo local > parallel_perlexpr
    parallel -Sparallel@lo --trc {=s/pr/pr.2/=}{=s/p/P/g=} echo remote OK '>' {}.2{=s/p/P/g=} ::: parallel_perlexpr
    cat /tmp/parallel_perlexpr.2Parallel_PerlexPr
    rm -f /tmp/parallel_perlexpr.2Parallel_PerlexPr /tmp/parallel_perlexpr

}

par_remote_function_nice() {
    echo '### functions and --nice'
    myfunc() {
	echo OK $*
    }
    export -f myfunc
    parallel --nice 10 --env myfunc -S parallel@lo myfunc ::: func
}

par_rplstr_return() {
    echo '### bug #45906: {= in header =}'
    rm -f returnfile45906
    parallel --rpl '{G} $_=lc($_)' -S parallel@lo --return {G} --cleanup echo {G} '>' {G} ::: RETURNFILE45906
    ls returnfile45906
}

par_nonall_should_not_block() {
    echo "### bug #47608: parallel --nonall -S lo 'echo ::: ' blocks"
    parallel --nonall -S lo 'echo ::: '
}

par_export_functions_csh() {
    echo '### exported function to csh but with PARALLEL_SHELL=bash'
    doit() { echo "$1"; }
    export -f doit
    stdout parallel --env doit -S csh@lo doit ::: not_OK
    PARALLEL_SHELL=bash parallel --env doit -S csh@lo doit ::: OK
}


par_progress_text_max_jobs_to_run() {
    echo '### bug #49404: "Max jobs to run" does not equal the number of jobs specified when using GNU Parallel on remote server?'
    echo should give 10 running jobs
    stdout parallel -S 16/lo --progress true ::: {1..10} | grep /.16
}

par_hgrp_rpl() {
    echo '### Implement {hgrp} replacement string'
    parallel -k --plus --hgrp -S @b/bash@lo -S @c/csh@lo 'echo {sshlogin} {hgrp}' ::: b@b c@c |
	grep -v -F -f <(cat <<EOF
bash@lo bash@lo+b
bash@lo b+bash@lo
csh@lo c+csh@lo
csh@lo csh@lo+c
EOF
			)
}

par_header_in_return() {
    echo '### bug #45907: --header : + --return {header}'
    rm -f returnfile45907
    parallel --header : -S parallel@lo --return {G} --cleanup echo {G} '>' {G} ::: G returnfile45907
    ls returnfile45907
    rm -f returnfile45907
}

par_trc_with_space() {
    echo '### Test --trc with space added in filename'
    cd
    mkdir -p tmp
    echo original > 'tmp/parallel space file'
    echo 'tmp/parallel space file' | stdout parallel --trc "{} more space" -S parallel@lo cat {} ">{}\\ more\\ space"
    cat 'tmp/parallel space file more space'
    rm 'tmp/parallel space file' 'tmp/parallel space file more space'
}

par_trc_with_special_chars() {
    echo '### Test --trc with >|< added in filename'
    cd
    mkdir -p tmp
    echo original > 'tmp/parallel space file2'
    echo 'tmp/parallel space file2' | stdout parallel --trc "{} >|<" -S parallel@lo cat {} ">{}\\ \\>\\|\\<"
    cat 'tmp/parallel space file2 >|<'
    rm 'tmp/parallel space file2' 'tmp/parallel space file2 >|<'
}

par_return_with_fixedstring() {
    echo '### Test --return with fixed string (Gave undef warnings)'
    touch a
    echo a | stdout parallel --return b -S parallel@lo echo ">b" && echo OK
    rm a b
}

par_quoting_for_onall() {
    echo '### bug #35427: quoting of {2} broken for --onall'
    echo foo: /bin/ls | parallel --colsep ' ' -S lo --onall ls {2}
}

par_hostgroup_only_on_args() {
    echo '### Auto add hostgroup if given on on argument'
    parallel --hostgroup ::: whoami@sh@lo
}

export -f $(compgen -A function | grep par_)
# Tested with -j1..8
# -j6 was fastest
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
compgen -A function | G par_ "$@" | sort | parallel --delay 0.1 -j2 --tag -k '{} 2>&1'
