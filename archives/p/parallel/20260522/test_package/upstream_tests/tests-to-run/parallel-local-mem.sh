#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

# On a 64G machine this uses 24G RAM + 5 min

make stopvm >/dev/null 2>/dev/null
TMPDIR=${TMPDIR:-/tmp}
mkdir -p $TMPDIR
# Jobs that eat more than 2 GB RAM

echo "dir $testsuitedir"
[ -e "$testsuitedir" ] && cd "$testsuitedir"
gendata() {
    # Generate a lot of text data fast
    yes "`seq 3000`" | head -c $1
}
export -f gendata

perl5.14parallel() {
    # Run GNU Parallel under perl 5.14 which does not support 64-bit very well
    # Remove setpgrp_func because 5.14 may use another func
    rm -f ~/.parallel/tmp/sshlogin/*/setpgrp_func
    PATH=input-files/perl-v5.14.2:$PATH
    PERL5LIB=input-files/perl-v5.14.2/lib input-files/perl-v5.14.2/perl `which parallel` "$@"
    rm -f ~/.parallel/tmp/sshlogin/*/setpgrp_func
}
export -f perl5.14parallel

par_2gb_records_N() {
    echo '### bug #44358: 2 GB records cause problems for -N'
    echo '5 GB version: Eats 12.5 GB RAM + 4 GB Swap'
    (gendata 5000MB; echo FOO;
     gendata 3000MB; echo FOO;
     gendata 1000MB;) |
	perl5.14parallel --pipe --recend FOO -N2 --block 1g -k LANG=c wc -c

    echo '2 GB version: eats 10 GB'
    (gendata 2300MB; echo FOO;
     gendata 2300MB; echo FOO;
     gendata 1000MB;) |
	perl5.14parallel --pipe --recend FOO -N2 --block 1g -k LANG=c wc -c

    echo '### -L >4GB';
    echo 'Eats 12.5 GB RAM + 6 GB Swap';
    (head -c 5000MB /dev/zero; echo FOO;
     head -c 3000MB /dev/zero; echo FOO;
     head -c 1000MB /dev/zero;) |
	parallel --pipe  -L2 --block 1g -k LANG=c wc -c
}

par_2gb_record_reading() {
    echo '### Trouble reading a record > 2 GB for certain versions of Perl (substr($a,0,2G+1)="fails")'
    echo '### perl -e $buf=("x"x(2**31))."x"; substr($buf,0,2**31+1)=""; print length $buf'
    echo 'Eats 4 GB'
    perl -e '$buf=("x"x(2**31))."x"; substr($buf,0,2**31+1)=""; print ((length $buf)."\n")'

    echo 'Eats 4.7 GB'
    (gendata 2300MB; echo ged) |
	perl5.14parallel -k --block 2G --pipe --recend ged md5sum
    echo 'Eats 4.7 GB'
    (gendata 2300MB; echo ged) |
	perl5.14parallel -k --block 2G --pipe --recend ged cat | wc -c
}

export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | sort |
    parallel -j1 --tag -k --joblog +/tmp/jl-`basename $0` '{} 2>&1'
