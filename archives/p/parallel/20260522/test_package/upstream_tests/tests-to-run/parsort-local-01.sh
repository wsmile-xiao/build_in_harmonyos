#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

par_whitespace_delimiter() {
    echo 'bug #59779: parsort does not work with white characters as delimiters'
    doit() {
	del="$1"
	tmp=$(mktemp)
	(
	    printf "a%s8%se\n" "$del" "$del"
	    printf "b%s7%sf\n" "$del" "$del"
	    printf "c%s3%sg\n" "$del" "$del"
	    printf "d%s5%sh\n" "$del" "$del"
        ) > "$tmp"
	parsort -t "$del" -k2 "$tmp"
    }
    doit ','
    doit ' '
    tab="$(printf '\t')"
    doit "$tab"
}

export -f $(compgen -A function | grep par_)
compgen -A function | grep par_ | LC_ALL=C sort |
    parallel --timeout 1000% -j6 --tag -k --joblog /tmp/jl-`basename $0` '{} 2>&1' |
    perl -pe 's:/usr/bin:/bin:g'

	
