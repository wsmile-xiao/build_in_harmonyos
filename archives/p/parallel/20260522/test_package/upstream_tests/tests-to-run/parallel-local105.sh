#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

TMP=/run/shm/parallel_local105
rm -rf $TMP 2>/dev/null
mkdir -p $TMP
pwd=$(pwd)
# If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
testsuitedir=${testsuitedir:-$pwd}
tar -C $TMP -xf "$testsuitedir"/input-files/random_dirs_with_newline.tar.bz2
cd $TMP/random_dirs_with_newline

# tests if special dir names causes problems
find . -type d -print0 | perl -0 -pe 's:^./::' | parallel -0 -v touch -- {}/abc-{}-{} 2>&1 \
 | perl -e 'print sort (<>)' | md5sum
echo -n 'There are ' 
find . -type d -print0 | perl -0 -ne '$a++;END{print $a}'
echo -n ' dirs with '
find . -type f -print0 | perl -0 -ne '$a++;END{print $a}'
echo ' files'
echo 'Removing files'
find . -type d -print0 |  perl -0 -pe 's:^./::' | parallel -0 -v rm -- {}/abc-{}-{} 2>&1 \
 | perl -e 'print sort (<>)' | md5sum
echo -n 'There are ' 
find . -type d -print0 | perl -0 -ne '$a++;END{print $a}'
echo -n ' dirs with '
find . -type f -print0 | perl -0 -ne '$a++;END{print $a}'
echo ' files'
echo 'Removing dirs'
find . -type d -print0 |  perl -0 -pe 's:^./::' | parallel -0 -v rmdir -- {} 2>&1 \
 | perl -e 'print sort (<>)' | md5sum
echo -n 'There are ' 
find . -type d -print0 | perl -0 -ne '$a++;END{print $a}'
echo -n ' dirs with '
find . -type f -print0 | perl -0 -ne '$a++;END{print $a}'
echo ' files'

cd ..
rm -rf $TMP

