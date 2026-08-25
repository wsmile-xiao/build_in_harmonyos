#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

SERVER1=parallel-server1
SSHUSER1=vagrant
SSHLOGIN1=$SSHUSER1@$SERVER1

mkdir -p tmp
cd tmp
pwd=$(pwd)
# If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
testsuitedir=${testsuitedir:-$pwd}

tar xjf "$testsuitedir"/input-files/testdir.tar.bz2
#rsync -Ha --delete input-files/testdir/ tmp/
#cd tmp

SERVER2=parallel@parallel-server2

echo $SSHLOGIN1 >~/.parallel/sshloginfile

echo '### Test --wd newtempdir/newdir/tmp/ with space dirs'; 
  ssh $SSHLOGIN1 rm -rf newtempdir; 
  stdout parallel -j9 -k --wd newtempdir/newdir/tmp/ --basefile 1-col.txt --trc {}.6 -S .. -v echo ">"{}.6 ::: './ ab/c"d/ef g' ' ab/c"d/efg' ./b/bar ./b/foo "./ ab /c' d/ ef\"g" ./2-col.txt './a b/cd / ef/efg'; 
  find . -name '*.6' | LC_ALL=C sort

echo '### Test --wd /tmp/newtempdir/newdir/tmp/ with space dirs'; 
  ssh $SSHLOGIN1 rm -rf /tmp/newtempdir; 
  stdout parallel -j9 -k --wd /tmp/newtempdir/newdir/tmp/ --basefile 1-col.txt --trc {}.7 -S .. -v echo ">"{}.7 ::: './ ab/c"d/ef g' ' ab/c"d/efg' ./b/bar ./b/foo "./ ab /c' d/ ef\"g" ./2-col.txt './a b/cd / ef/efg'; 
  find . -name '*.7' | LC_ALL=C sort

echo '### Test --workdir ...'
parallel -j9 -k --workdir ... --trc {}.1 -S .. echo ">"{}.1 ::: 2-col.txt
find . -name '*.1' | LC_ALL=C sort

echo '### Test --wd ...'
parallel -k --wd ... --trc {}.2 -S .. -v echo ">"{}.2 ::: 2-col.txt
find . -name '*.2' | LC_ALL=C sort

echo '### Test --wd ... with space dirs'
stdout parallel -j9 -k --wd ... --trc {}.3 -S .. -v echo ">"{}.3 ::: './ ab/c"d/ef g' ' ab/c"d/efg' ./b/bar ./b/foo "./ ab /c' d/ ef\"g" ./2-col.txt './a b/cd / ef/efg'
# A few rmdir errors are OK as we have multiple files in the same dirs
find . -name '*.3' | LC_ALL=C sort

echo '### Test --wd tmpdir'
parallel -j9 -k --wd tmpdir --basefile 1-col.txt --trc {}.4 -S .. -v echo ">"{}.4 ::: 2-col.txt
find . -name '*.4' | LC_ALL=C sort

echo '### Test --wd /tmp/ with space dirs'
stdout parallel -k -j9 --wd /tmp/ --basefile 1-col.txt --trc {}.5 -S .. -v echo ">"{}.5 ::: './ ab/c"d/ef g' ' ab/c"d/efg' ./b/bar ./b/foo "./ ab /c' d/ ef\"g" ./2-col.txt './a b/cd / ef/efg'
# A few rmdir errors are OK as we have multiple files in the same dirs
find . -name '*.5' | LC_ALL=C sort

cd ..
rm -rf tmp
