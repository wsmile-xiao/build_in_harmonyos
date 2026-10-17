#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_space() {
    echo '### Test --env  - https://savannah.gnu.org/bugs/?37351'
    export TWOSPACES='  2  spaces  '
    export THREESPACES=" >  My brother's 12\" records  < "
    echo a"$TWOSPACES"b 1
    stdout parallel --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S csh@localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1
    stdout parallel -S tcsh@localhost --env TWOSPACES echo 'a"$TWOSPACES"b' ::: 1

    echo a"$TWOSPACES"b a"$THREESPACES"b 2
    stdout parallel --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S csh@localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2
    stdout parallel -S tcsh@localhost --env TWOSPACES --env THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 2

    echo a"$TWOSPACES"b a"$THREESPACES"b 3
    stdout parallel --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S csh@localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
    stdout parallel -S tcsh@localhost --env TWOSPACES,THREESPACES echo 'a"$TWOSPACES"b' 'a"$THREESPACES"b' ::: 3
}

par_space_quote() {
    export MIN="  \'\""
    echo a"$MIN"b 4
    stdout parallel --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S localhost --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S csh@localhost --env MIN echo 'a"$MIN"b' ::: 4
    stdout parallel -S tcsh@localhost --env MIN echo 'a"$MIN"b' ::: 4
}

par_special_char() {
    export SPC="'"'   * ? >o  <i*? ][\!#¤%=( ) | }'
    echo a"$SPC"b 5
    LANG=C stdout parallel --env SPC echo 'a"$SPC"b' ::: 5
    LANG=C stdout parallel -S localhost --env SPC echo 'a"$SPC"b' ::: 5
    # \ misses due to quoting incompatiblilty between bash and csh
    LANG=C stdout parallel -S csh@localhost --env SPC echo 'a"$SPC"b' ::: 5
    LANG=C stdout parallel -S tcsh@localhost --env SPC echo 'a"$SPC"b' ::: 5
}

test_chr_on_sshlogin() {
    # test_chr_on_sshlogin 10,92 2/:,2/lo
    # test_chr_on_sshlogin 10,92 2/tcsh@lo,2/csh@lo
    chr="$1"
    sshlogin="$2"
    onall="$3"
    perl -e 'for('$chr') { printf "%c%c %c%d\0",$_,$_,$_,$_ }' |
	stdout parallel -j4 -k -I // --arg-sep _ -0 V=// V2=V2=// LANG=C parallel -k -j1 $onall -S $sshlogin --env V,V2,LANG echo \''"{}$V$V2"'\' ::: {#} {#} {#} {#} |
	sort |
	uniq -c |
	grep -av '   4 '|
	grep -av xauth |
	grep -av X11
}
export -f test_chr_on_sshlogin

par_env_newline_backslash_bash() {
    echo '### Test --env for \n and \\ - single and double (bash only) - no output is good'
    test_chr_on_sshlogin 10,92 2/:,2/lo ''
}

par_env_newline_backslash_csh() {
    echo '### Test --env for \n and \\ - single and double (*csh only) - no output is good but csh fails'
    test_chr_on_sshlogin 10,92  2/csh@lo '' | perl -pe "s/'(.)'/\$1/g"
    test_chr_on_sshlogin 10,92 2/tcsh@lo '' | perl -pe "s/'(.)'/\$1/g"
}

par_env_newline_backslash_onall_bash() {
    echo '### Test --env for \n and \\ - single and double --onall (bash only) - no output is good'
    test_chr_on_sshlogin 10,92 :,lo --onall |
	grep -v "Unmatched '\"'"
}

par_env_newline_backslash_onall_csh() {
    echo '### Test --env for \n and \\ - single and double --onall (*csh only) - no output is good but csh fails'
    test_chr_on_sshlogin 10,92 2/tcsh@lo,2/csh@lo --onall
}

par_env_160() {
    echo '### Test --env for \160 - which kills csh - single and double - no output is good'
    test_chr_on_sshlogin 160 :,1/lo,1/tcsh@lo |
	grep -v '   3 '
}

par_env_160_onall() {
    echo '### Test --env for \160  - which kills csh - single and double --onall - no output is good'
    test_chr_on_sshlogin 160 :,1/lo,1/tcsh@lo --onall |
	grep -a -v '   3 '
}

export -f $(compgen -A function | grep par_)
#compgen -A function | grep par_ | sort | parallel --delay $D -j$P --tag -k '{} 2>&1'
compgen -A function | grep par_ | sort |
    parallel --joblog /tmp/jl-`basename $0` --retries 3 -j2 --tag -k '{} 2>&1'
