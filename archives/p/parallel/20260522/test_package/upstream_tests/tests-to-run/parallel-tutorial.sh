#!/bin/bash
# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

cleanup() {
    find {"$TMPDIR",/var/tmp,/tmp}/{fif,tms,par[^a]}* -mmin -10 -print0 2>/dev/null |
	parallel -0 rm 2>/dev/null
}

cleanup
touch ~/.parallel/will-cite
echo '### test parallel_tutorial'

unset DISPLAY
TMPDIR=/tmp/parllel-tutorial
mkdir -p "$TMPDIR"
cd "$TMPDIR"
pwd=$(pwd)
# If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
testsuitedir=${testsuitedir:-$pwd}
srcdir=$(echo "$testsuitedir" | perl -pe 's=$ENV{HOME}==')
export SERVER1=parallel@lo
export SERVER2=csh@lo
export PARALLEL=-k
perl -ne '$/="\n\n"; /^Output/../^[^O=]\S/ and next; /^  / and print;' "$testsuitedir"/../src/parallel_tutorial.pod |
    egrep -v 'curl|tty|parallel_tutorial|interactive|example.(com|net)' |
    egrep -v 'shellquote|works|num128|--filter-hosts|--tmux|my_id' |
    perl -pe 's/username@//;s/user@//;
              s/zenity/zenity --timeout=15/;
              s:/usr/bin/time:/usr/bin/time -f %e:;
              s:ignored_vars:ignored_vars|sort:;
              # Remove \n to join all joblogs into the previous block
              s:cat /tmp/log\n:cat /tmp/log;:;
              # Remove import (python code)
              s:import.*::;
              # When parallelized: Sleep to make sure the abc-files are made
              /%head1/ and $_.="sleep .3\n\n"x10;
' |
    stdout parallel --joblog /tmp/jl-`basename $0` -j6 -vd'\n\n' |
    replace_tmpdir |
    perl -pe '$|=1;
              # --pipe --roundrobin wc
              s: \d{6}  \d{6} \d{7}: 999999  999999 9999999:;
              # --tmux
              s:(/TMP|/tmp)(/tms).....:$1$2XXXXX:;
              # --files
              s:(/TMP/par).....(\....):$1XXXXX$2:;
              # --eta --progress
              s/ETA.*//g; s/local:.*//g;
              # Sat Apr  4 11:55:40 CEST 2015
              s/... ... .. ..:..:.. \D+ ..../DATE OUTPUT/;
              # Timestamp from --joblog
              s/\d{10}.\d{3}\s+..\d+/TIMESTAMP\t9.999/g;
              # Version
              s/20[0-3]\d{5}/VERSION/g;
              # [123] [abc] [ABC]
              s/^[123] [abc] [ABC]$/123 abc ABC/g;
              # Remote script
              s/(PARALLEL_PID\D+)\d+/${1}000000/g;
              # sql timing
              s/,[a-z0-9]*,\d+.\d+,\d+.\d+/,:,000000000.000,0.000/g;
              # /usr/bin/time -f %e
              s/^(\d+)\.\d+$/$1/;
              # --workdir ...
              s:parallel/tmp/[a-z0-9]+-\d+-1:TMPWORKDIR:g;
	      # .../privat/parallel2/
	      s='$srcdir'==;
              # + cat ... | (Bash outputs these in random order)
              s/\+ cat.*\n//;
              # + echo ... | (Bash outputs these in random order)
              s/\+ echo.*\n//;
              # + wc ... (Bash outputs these in random order)
              s/\+ wc.*\n//;
              # + command_X | (Bash outputs these in random order)
              s/.*command_[ABC].*\n//;
              # Due to multiple jobs "Second started" often ends up wrong
              s/Second started\n//;
              s/The second finished\n//;
              # Due to multiple jobs "tried 2" often ends up wrong
              s/tried 2\n//;
              # Due to order is often mixed up
              s/echo \d; exit \d\n/echo X; exit X\n/;
              # Race condition causes outdir to sometime exist
              s/(std(out|err)|seq): Permission denied/$1: No such file or directory/;
              # Race condition
              s/^4-(middle|end)\n//;
              # Race condition
	      s/^parallel: This job failed:\n//;
	      s/^echo .; exit .\n//;
              # Base 64 string with quotes
              s:['"'"'"\\+/a-z.0-9=]{50,}(\s['"'"'"\\+/a-z.0-9=]*)*:BASE64:ig;
              # Timings are often off
              s/^(\d)$/9/;
              s/^(\d\d)$/99/;
	      # Remove variable names - they vary
	      s/^[A-Z][A-Z0-9_]*\s$//;
	      # Fails often due to race
	      s/cat: input_file: No such file or directory\n//;
	      s{rsync: .* link_stat ".*/home/parallel/input_file.out" .*\n}{};
	      s{rsync error: some files/attrs were not transferred .*\n}{};
	      s{Give up after 2 secs\n}{};
	      s{parallel: Warning: Semaphore timed out. Exiting.\n}{};
	      s{parallel: Starting no more jobs. Waiting for 1 jobs to finish.}{};
	      s{.* GtkDialog .*\n}{};
	      s{tried 1}{};
	      s/^\s*\n//;
	      s/^Second done\n//;
	      # Changed citation
	      s/Tange, O. .* GNU Parallel .*//;
	      s:https.//doi.org/10.5281/.*::;
	      s/.software.tange_.*//;
	      s/title.*= .*Parallel .*//;
	      s/month.*= .*//;
	      s/doi.*=.*//;
	      s/url.*= .*doi.org.*//;
	      s/.Feel free to use .nocite.*//;
	      # tmpdir and files
	      s:/tmp/parallel-tutorial-tmpdir/par-job-\S+:script:g;
	      s:/tmp/par-job-\S+:script:g;
	      s:par......par:tempfile:g;
	      s:^tempfile\n::g;
	      #+(zenity:2012805): Gtk-WARNING **: 02:25:32.662: cannot open display:
	      #+(zenity:3135184): Gtk-WARNING **: 20:03:27.525: Failed to open display
	      s,.zenity.*open display.*\n,,;
	      # --progress => 1:local / 4 / 4
	      s,1:local / . / .,1:local / 9 / 9,;
	      # bash: -c: line 1: .set a="tempfile"; if( { test -d "$a" } ) echo "$a is a dir"
	      s{.*bash: .*set a=".*".*test -d.*is a dir.*\n}{};
	      # /usr/bin/bash: -c: line 1: syntax error near unexpected token .)
	      # /usr/bin/bash: -c: line 5: syntax error: unexpected end of file
	      s{.*bash: -c: line .*\n}{};
	      # This is input_file
	      s{^This is input_file.*\n}{};
	      # Different env
	      s{mysqlrootpass\n}{};
	      # Single number after zenity
	      s{^\d+\n}{}
	      ' | uniq

echo "### 3+3 .par files (from --files), 1 .tms-file from tmux attach"
find {"$TMPDIR",/var/tmp}/{fif,tms,par[^a]}* -mmin -10 -type f -print0 2>/dev/null |
    parallel -0 grep . | sort
cleanup
