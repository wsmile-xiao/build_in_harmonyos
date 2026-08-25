#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

TMP=/run/shm/parallel_$$

pwd=$(pwd)
# If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
testsuitedir=${testsuitedir:-$pwd}
mkdir -p $TMP
cd $TMP/
tar xjf "$testsuitedir"/input-files/testdir.tar.bz2

echo echo test of cat pipe sh | parallel -j 50 2>&1
find . -name '*.jpg' | parallel -j +0 convert -geometry 120 {} {//}/thumb_{/}

ls | parallel ls | LC_ALL=C sort
ls | parallel echo ls | LC_ALL=C sort
ls | parallel -j 1 echo ls | LC_ALL=C sort
find -type f | parallel diff {} a/foo ">"{}.diff | LC_ALL=C sort
ls | parallel -v --group "ls {}|wc;echo {}" | LC_ALL=C sort
echo '### Check that we can have more input than max procs (-j 0) - touch'
perl -e 'print map {"more_than_5000-$_\n" } (4000..9999)' | parallel -vj 0 touch | LC_ALL=C sort | tail
echo '### rm'
perl -e 'print map {"more_than_5000-$_\n" } (4000..9900)' | parallel -j 0 rm | LC_ALL=C sort
cat <<'EOF' | sed -e 's/;$/; /;s/$SERVER1/'$SERVER1'/;s/$SERVER2/'$SERVER2'/' | stdout parallel -vj0 -k --joblog /tmp/jl-`basename $0` -L1 | egrep -v 'parallel: Warning: (Starting|Consider|Only|Try)'
ls | parallel -j500 'sleep 1; find {} -type f | perl -ne "END{print $..\" "{=$_=pQ($_)=}"\n\"}"' | LC_ALL=C sort
ls | parallel --group -j500 'sleep 1; find {} -type f | perl -ne "END{print $..\" "{=$_=pQ($_)=}"\n\"}"' | LC_ALL=C sort
find . -type f | parallel --group  "perl -ne '/^\\S+\\s+\\S+$/ and print \$ARGV,\"\\n\"'" | LC_ALL=C sort
find . -type f | parallel -v --group "perl -ne '/^\\S+\\s+\\S+$/ and print \$ARGV,\"\\n\"'" | LC_ALL=C sort
find . -type f | parallel -q --group  perl -ne '/^\S+\s+\S+$/ and print $ARGV,"\n"' | LC_ALL=C sort
find . -type f | parallel -qv --group perl -ne '/^\S+\s+\S+$/ and print $ARGV,"\n"' | LC_ALL=C sort
EOF

cd - >/dev/null
rm -rf $TMP/
