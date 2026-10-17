#!/bin/sh
# test_server_starter.sh — Conan L1 test for perl-server-starter
# Tests that Server::Starter module loads and start_server works.
# PERL5LIB is set by runenv_info from package_info().
set -e
set -o pipefail

# Test 1: Server::Starter module loads and version is correct
perl -MServer::Starter -e 'die "VERSION mismatch" unless $Server::Starter::VERSION eq "0.35"; print "Test 1 PASS: Server::Starter loaded, version 0.35\n"'

# Test 2: Server::Starter::Guard module loads
perl -MServer::Starter::Guard -e 'print "Test 2 PASS: Server::Starter::Guard loaded\n"'

# Test 3: start_server --version works
if start_server --version 2>&1 | grep -q "0.35"; then
    echo "Test 3 PASS: start_server --version returns 0.35"
else
    echo "Test 3 FAIL: start_server --version did not return 0.35"
    exit 1
fi

# Test 4: Exported functions are defined
perl -MServer::Starter -e '
    for my $fn (qw(start_server restart_server stop_server server_ports)) {
        die "$fn not defined" unless defined &{"Server::Starter::$fn"};
    }
    print "Test 4 PASS: all exported functions defined\n"
'

echo "ALL TESTS COMPLETED"
