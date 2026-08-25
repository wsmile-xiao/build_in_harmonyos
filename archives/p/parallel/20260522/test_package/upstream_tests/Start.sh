#!/bin/bash -x

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# Argument can be substring of tests (such as 'local')

export LANG=C
export LC_ALL=C
unset LC_MONETARY
SHFILE=/tmp/unittest-parallel.sh
MAX_SEC_PER_TEST=900
export TIMEOUT=$MAX_SEC_PER_TEST

run_once() {
    replace_tmpdir() {
	# Replace $TMPDIR with TMP
	perl -0 -pe 'BEGIN{ ($a,$b,$c) = (shift,shift,shift);
                            $a =~ s/'"'"'$//s; $b =~ s/'"'"'$//s; $c =~ s/'"'"'$//s; }
                     s:""+:":g;
                     s:('"'"'?)(\Q$a\E|\Q$b\E|\Q$c\E)('"'"'?)([/a-z0-9]*)('"'"'?):/TMP$4:gi;
                     s/\0/\n/g' "$TMPDIR" "$qTMPDIR" "$qqTMPDIR" |
	    perl -ne '/Use --files0 when $TMPDIR contains newline./ or print'
    }
    export qqTMPDIR=$(< /dev/null parallel -0 --shellquote --shellquote ::: "$TMPDIR")
    export qTMPDIR=$(< /dev/null parallel -0 --shellquote ::: "$TMPDIR")
    export -f replace_tmpdir
    script=$1
    base=`basename "$script" .sh`
    if diff -Naur wanted-results/"$base" actual-results/"$base" >/dev/null; then
	# There is no diff: Last time worked - no need to try again
	true skip
    else
	(
	    testsuitedir=$(pwd)
	    export testsuitedir
	    cd "$TMPDIR"
	    bash "$testsuitedir/$script" |
		perl -pe 's:'$HOME':~:g' |
		replace_tmpdir > "$testsuitedir"/actual-results/"$base"
	)
    fi
}
export -f run_once

run_test() {
    script="$1"
    base=`basename "$script" .sh`
    # Force spaces and < into TMPDIR - this will expose bugs
    # ASCII [^-,+=a-zA-Z0-9] = all special chars (175 is not supported)
    fancychars="$(perl -e 'print "\n\`touch  /tmp/tripwire\`>/tmp/tripwire;\n".
                         (pack "c*",2..42,127..174,47,176..255)."\@<?[]|~\\}{"')"
    fancychars="$(perl -e 'print "\n\`touch  /tmp/tripwire\`>/tmp/tripwire;\n".
                         (pack "c*",2..42,127..174,47,176..255)."\@<?[]|~\\}{"')"
    fancychars="$(perl -e 'print "\n\`touch  /tmp/tripwire\`>/tmp/tripwire;\n".
                         (pack "c*",127..174,47,176..255)."\@<?[]|~\\}{"')"
    fancychars="$(perl -e 'print "\n\`touch  /tmp/tripwire\`>/tmp/tripwire;\n".
                         (pack "c*",34,39,176..255)."\@<?[]|~\\}{"')"
    semiok_fancychars="$(perl -e 'print "\n\`touch  /tmp/tripwire\`>/tmp/tripwire;\n".
                         "\@<?[]|~\\}{"')"
    fancychars="$(perl -e 'print "\n\`/tmp/trip\`>/tmp/tripwire;\n".
                         (pack "c*",2..10,34,39)."\@<?[]|~\\"')"
# OK
#    fancychars="$(perl -e 'print "\n\`/tmp/trip\`>/tmp/tripwire;\n".
#                         (pack "c*",2..10,34,39)."\@<?[]|~\\"')"
    export TMPDIR=/tmp/"$base-tmp"/"$fancychars"/tmp
    export PARALLEL="--unsafe";
    rm -rf "$TMPDIR"
    mkdir -p "$TMPDIR"
    # Clean before. May be owned by other users
    sudo rm -f /tmp/*.{tmx,pac,arg,all,log,swp,loa,ssh,df,pip,tmb,chr,tms,par} ||
	printf "%s\0" /tmp/*.par | sudo parallel -0 -X rm
    rm -f /tmp/tripwire
    printf '#!/bin/bash\ntouch /tmp/tripwire' > /tmp/trip
    chmod +x /tmp/trip
    # Force running once
    echo >> actual-results/"$base"
    if [ "$TRIES" = "3" ] ; then
	# Try 2 times
	run_once $script
	run_once $script
    fi
    run_once $script
    if [ -e /tmp/tripwire ] ; then
	echo '!!!'
	echo '!!! /tmp/tripwire TRIPPED !!!'
	echo '!!! Quoting of TMPDIR failed !!!'
	echo '!!!'
	exit 1
    fi
    diff -Naur wanted-results/"$base" actual-results/"$base" ||
	(touch "$script" && echo touch "$script")
    
    # Check if it was cleaned up
    find /tmp -maxdepth 1 |
	perl -ne '/\.(tmx|pac|arg|all|log|swp|loa|ssh|df|pip|tmb|chr|tms|par)$/ and
                  ++$a and
                  print "TMP NOT CLEAN. FOUND: $_".`touch '$script'`;'
    # May be owned by other users
    sudo rm -f /tmp/*.{tmx,pac,arg,all,log,swp,loa,ssh,df,pip,tmb,chr,tms,par}
}
export -f run_test

create_monitor_script() {
    # Create a monitor script
    echo forever "'echo; pstree -lp '"$$"'; pstree -l'" $$ >/tmp/monitor
    chmod 755 /tmp/monitor
}

log_rotate() {
    # Log rotate
    mkdir -p log
    seq 10 -1 1 |
	parallel -j1 mv log/testsuite.log.{} log/testsuite.log.'{= $_++ =}'
    mv testsuite.log log/testsuite.log.1
}

create_monitor_script
log_rotate

printf "\033[48;5;78;38;5;0m     `date`     \033[00m\n"
mkdir -p actual-results
ls -t tests-to-run/*${1}*.sh | egrep -v "${2}" |
    # parallel --bar --timeout 3000 --tty -tj1 run_test | tee testsuite.log
    parallel --timeout 3000 --tty -tj1 run_test | tee testsuite.log
# If testsuite.log contains @@ then there is a diff
if grep -q '@@' testsuite.log ; then
    false
else
    # No @@'s: So everything worked: Copy the source
    rm -rf src-passing-testsuite
    cp -a ../src src-passing-testsuite
fi
printf "\033[48;5;208;38;5;0m     `date`     \033[00m\n"
