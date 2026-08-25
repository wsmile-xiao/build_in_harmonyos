#!/bin/bash

# SPDX-FileCopyrightText: 2025-2025 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo "### These tests requires VirtualBox running with the following images"
echo 'vagrant@openindiana'

SERVER1=openindiana
SSHUSER1=vagrant
export SSHLOGIN1=$SSHUSER1@$SERVER1
# server with shellshock hardened bash
SERVER2=172.27.27.1
SSHUSER2=parallel
export SSHLOGIN2=$SSHUSER2@$SERVER2

cd_vagrant() {
    # Try different "cd"s as the script may be started from another dir
    cd $testsuitedir/vagrant/openindiana/openindiana/ 2>/dev/null
    cd testsuite/vagrant/openindiana/openindiana/ 2>/dev/null
    cd vagrant/openindiana/openindiana/ 2>/dev/null
    cd ../vagrant/openindiana/openindiana/ 2>/dev/null
}

start_openindiana() {
    stdout ping -w 1 -c 1 openindiana >/dev/null || (
	cd_vagrant
	stdout vagrant up >/dev/null &
	(sleep 10; stdout vagrant up >/dev/null ) &
    )
}

stop_openindiana() {
    stdout ping -w 1 -c 1 openindiana >/dev/null && (
	cd_vagrant
	stdout vagrant suspend >/dev/null &
	(sleep 10; stdout vagrant suspend >/dev/null ) &
    )
}
start_openindiana

(
    pwd=$(pwd)
    # If not run in dir parallel/testsuite: set testsuitedir to path of testsuite
    testsuitedir=${testsuitedir:-$pwd}
    cd $testsuitedir
    # Copy binaries to server
    cd testsuite/ 2>/dev/null
    cd ..
    ssh $SSHLOGIN1 'mkdir -p .parallel bin; touch .parallel/will-cite'
    scp -q src/{parallel,sem,sql,niceload,env_parallel*} $SSHLOGIN1:bin/
    if ssh $SSHLOGIN1 '. .bashrc; 'parallel ::: true ; then
	true
    else
	ssh $SSHLOGIN1 'echo PATH=\$PATH:\$HOME/bin >> .bashrc'
    fi
    
    ssh $SSHLOGIN1 '[ -e .ssh/id_rsa.pub ] || ssh-keygen -t rsa -P "" -f .ssh/id_rsa'
    # Allow login from centos3 to $SSHLOGIN2 (that is shellshock hardened)
    ssh $SSHLOGIN1 cat .ssh/id_rsa.pub | ssh $SSHLOGIN2 'cat >>.ssh/authorized_keys'
    ssh $SSHLOGIN1 'cat .ssh/id_rsa.pub >>.ssh/authorized_keys; chmod 600 .ssh/authorized_keys'
    ssh $SSHLOGIN1 'ssh -o StrictHostKeyChecking=no localhost true; ssh -o StrictHostKeyChecking=no '$SSHLOGIN2' true;'
) &

. env_parallel.bash
env_parallel --session

par_sockets_cores_threads() {
    . .bashrc
    uname -a
    parallel --minversion 20250123 >/dev/null && echo Version OK
    parallel --number-of-sockets
    parallel --number-of-cores
    parallel --number-of-threads
    parallel --number-of-cpus
}

#   As the copied environment is written in Bash dialect
#   we get 'shopt'-errors and 'declare'-errors.
#   We can safely ignore those.
export LC_ALL=C
export TMPDIR=/tmp
unset DISPLAY
env_parallel --env par_sockets_cores_threads --env LC_ALL --env SSHLOGIN2 \
	     -vj9 -k --joblog /tmp/jl-`basename $0` --retries 3 \
	     -S $SSHLOGIN1 --tag '{} 2>&1' \
	     ::: $(compgen -A function | grep par_ | sort) \
	     2> >(grep -Ev 'shopt: not found|declare: not found|No xauth data')
ssh $SSHLOGIN1 '. .bashrc; 'parallel echo {}: ssh $SSHLOGIN1 parallel ::: OK

#stop_openindiana
