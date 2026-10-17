#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo '### Test with old perl libs'

pwd=$(pwd)
# If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
testsuitedir=${testsuitedir:-$pwd}
cd "$testsuitedir"

# Old libraries are put into input-files/perllib
PERL5LIB=input-files/perllib:../input-files/perllib; export PERL5LIB

echo '### See if we get compile error'
PATH=input-files/perllib:../input-files/perllib:$PATH
perl32 `which parallel` ::: 'echo perl'
echo '### See if we read modules outside perllib'
echo perl |
    stdout strace -ff perl32 `which parallel` echo |
    grep open |
    grep perl |
    grep -v '\$' |
    grep -v '] read(6' |
    grep -v input-files/perllib

par_make_deb_package() {
    echo '### Test make .deb package'; 
    cd ~/privat/parallel/packager/debian
    # If the final line is there: It is OK
    stdout make | grep 'To install the GNU Parallel Debian package, run:'
}

par_make_deb_package
