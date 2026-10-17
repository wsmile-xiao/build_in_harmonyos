#!/bin/bash

# SPDX-FileCopyrightText: 2021-2026 Ole Tange, http://ole.tange.dk and Free Software and Foundation, Inc.
#
# SPDX-License-Identifier: GPL-3.0-or-later

echo "### These tests requires VirtualBox running with the following images"
echo 'vagrant@centos3'

# add this to .ssh/config
#   Host centos3
#     HostKeyAlgorithms +ssh-rsa,ssh-dss
#     PubkeyAcceptedAlgorithms +ssh-dss
#     user vagrant

# add this to: /etc/ssh/sshd_config on 172.27.27.1
#   KexAlgorithms +diffie-hellman-group1-sha1,curve25519-sha256@libssh.org,ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,diffie-hellman-group-exchange-sha256,diffie-hellman-group14-sha1
#   Ciphers +3des-cbc,aes128-cbc,aes192-cbc,aes256-cbc,aes128-ctr,aes192-ctr,aes256-ctr,aes128-gcm@openssh.com,aes256-gcm@openssh.com,chacha20-poly1305@openssh.com
#   HostKeyAlgorithms +ssh-rsa
# and:
#   systemctl restart sshd

SERVER1=centos3
SSHUSER1=vagrant
SSHLOGIN1=$SSHUSER1@$SERVER1
# server with shellshock hardened bash
SERVER2=172.27.27.1
SSHUSER2=parallel
export SSHLOGIN2=$SSHUSER2@$SERVER2

start_centos3() {
    timeout 10 ssh $SSHLOGIN1 echo ssh $SSHLOGIN1 OK || (
	# Vagrant does not set the IP addr
	# cd to the centos3 dir with the Vagrantfile
	# Try different "cd"s as the script may be started from another dir
	cd $testsuitedir/vagrant/FritsHoogland/centos3/ 2>/dev/null
	cd testsuite/vagrant/FritsHoogland/centos3/ 2>/dev/null
	cd vagrant/FritsHoogland/centos3/ 2>/dev/null
	cd ../vagrant/FritsHoogland/centos3/ 2>/dev/null
	vagrantssh() {
	    port=$(perl -ne '/#/ and next; /config.vm.network.*host:\s*(\d+)/ and print $1' Vagrantfile)
	    timeout 100 w4it-for-port-open localhost $port &&
	    timeout 100 ssh -oKexAlgorithms=+diffie-hellman-group1-sha1 \
		-oHostKeyAlgorithms=+ssh-rsa,ssh-dss \
		-oPubkeyAcceptedAlgorithms=+ssh-dss -p$port vagrant@localhost "$@" |
		# Ignore empty ^M line
		grep ..
	}
	stdout vagrant up >/dev/null &
	(sleep 10; stdout vagrant up >/dev/null ) &
	vagrantssh 'sudo /sbin/ifconfig eth1 172.27.27.3; echo centos3: added 172.27.27.3 >&2'
	timeout 10 ssh $SSHLOGIN1 echo ssh $SSHLOGIN1 OK
    )
}
start_centos3 || exit 1

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
    if ssh $SSHLOGIN1 parallel ::: true ; then
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

par_--ssh_lsh() {
    echo '### --ssh lsh'
    # lsh: Protocol error: No common key exchange method.
    #
    # $ lsh --list-algorithms
    # Supported hostkey algorithms: ssh-dss, spki, none
    #
    # $ nmap --script ssh2-enum-algos -sV -p 22 lo
    # |   server_host_key_algorithms: (4)
    # |       rsa-sha2-512
    # |       rsa-sha2-256
    # |       ecdsa-sha2-nistp256
    # |       ssh-ed25519
    # |
    #
    server=centos3
    user=vagrant
    sshlogin=$user@$server
    parallel --ssh lsh -S $sshlogin echo ::: OK
    echo OK | parallel --ssh lsh --pipe -S $sshlogin cat
    parallel --ssh lsh -S $sshlogin echo ::: OK
    echo OK | parallel --ssh lsh --pipe -S $sshlogin cat
    # Todo:
    # * rsync/--trc
    # * csh@lo
}

export -f $(compgen -A function | grep par_)
compgen -A function | G par_ "$@" | sort |
    parallel --timeout 100 -j75% --joblog /tmp/jl-`basename $0` -j3 --tag -k --delay 0.1 --retries 3 '{} 2>&1'

unset $(compgen -A function | grep par_)

. env_parallel.bash
env_parallel --session

par_shellshock_bug() {
    bash -c 'echo bug \#43358: shellshock breaks exporting functions using --env name;
      echo Non-shellshock-hardened to non-shellshock-hardened;
      funky() { echo OK: Function $1; };
      export -f funky;
      PARALLEL_SHELL=bash parallel --env funky -S localhost funky ::: non-shellshock-hardened'

    bash -c 'echo bug \#43358: shellshock breaks exporting functions using --env name;
      echo Non-shellshock-hardened to shellshock-hardened;
      funky() { echo OK: Function $1; };
      export -f funky;
      PARALLEL_SHELL=bash parallel --env funky -S '$SSHLOGIN2' funky ::: shellshock-hardened'
}

#   As the copied environment is written in Bash dialect
#   we get 'shopt'-errors and 'declare'-errors.
#   We can safely ignore those.
export LC_ALL=C
export TMPDIR=/tmp
unset DISPLAY
env_parallel --env par_shellshock_bug --env LC_ALL --env SSHLOGIN2 \
	     -vj9 -k --joblog /tmp/jl-`basename $0` --retries 3 \
	     -S $SSHLOGIN1 --tag '{} 2>&1' \
	     ::: $(compgen -A function | grep par_ | sort) \
	     2> >(grep -Ev 'shopt: not found|declare: not found|No xauth data')
ssh $SSHLOGIN1 parallel echo {}: ssh $SSHLOGIN1 parallel ::: OK
