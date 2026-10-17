#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

unset TIMEOUT
torsocks bash <<'EOF'
. `which env_parallel.bash`
env_parallel --session

host=$(parallel -j0 --halt now,success=1 ssh {} echo {} ::: kodi koditor huator fairtor 2>/dev/null)
if [ -z "$host" ] ; then
    echo Error: no android host working
else    
    echo $host >&2

    doit() {
	export PARALLEL_SSH='ssh -p2222 -o "StrictHostKeyChecking no"'
	parallel -k echo ::: Basic usage works
	parallel -k -S localhost echo ::: Remote usage works
    }

    scp /usr/local/bin/parallel $host:/data/data/com.termux/files/usr/bin
    env_parallel -S $host doit ::: a
fi
EOF
