#!/bin/sh
# test_package consumer test for klibc-nfsmount 2.0.14 (nfsmount).
#
# Upstream has NO test suite (usr/kinit/nfsmount contains no test program;
# dummypmap_test.c is dead code — no main(), excluded by the Kbuild FIXME).
# Real NFS mounts additionally require a live NFS server + kernel nfs
# module (unavailable on OHOS). R51 inventory & actual-runs: 0 upstream tests.
#
# Therefore the consumer verification exercises the binary's deterministic
# offline code paths — each must exit non-zero with the expected message:
#   1. no arguments        -> "need a path"            (main.c usage guard)
#   2. unknown option      -> "invalid option"         (getopt switch default)
#   3. bad -o sub-option   -> "bad option '<x>'"       (mount options parser)
#   4. missing mountpoint  -> stat perror + exit 1     (mountpoint stat guard)
# These cover the argument/option parsing layers that run before any network
# I/O, proving the tool is executable and linked against the system libc.
export PATH="$PATH:/system/bin"

echo "--- klibc-nfsmount consumer verification ---"

fail() { echo "FAIL: $1"; exit 1; }

# 1. no arguments -> usage error, exit 1
out1=$(nfsmount 2>&1)
rc1=$?
[ "$rc1" != "0" ] || fail "no-args run unexpectedly exited 0"
echo "$out1" | grep -q "need a path" || fail "no-args: unexpected output [$out1]"
echo "PASS 1: no-args -> 'need a path' (exit $rc1)"

# 2. unknown option -> "invalid option", exit 1
out2=$(nfsmount -Z 127.0.0.1:/export /mnt 2>&1)
rc2=$?
[ "$rc2" != "0" ] || fail "invalid-option run unexpectedly exited 0"
echo "$out2" | grep -q "invalid option" || fail "invalid-option: unexpected output [$out2]"
echo "PASS 2: invalid option -> 'invalid option' (exit $rc2)"

# 3. bad mount -o sub-option -> "bad option", exit 1
out3=$(nfsmount -o notanoption 127.0.0.1:/export /mnt 2>&1)
rc3=$?
[ "$rc3" != "0" ] || fail "bad -o sub-option run unexpectedly exited 0"
echo "$out3" | grep -q "bad option 'notanoption'" || fail "bad -o: unexpected output [$out3]"
echo "PASS 3: bad -o sub-option -> \"bad option 'notanoption'\" (exit $rc3)"

# 4. nonexistent mountpoint -> stat failure, exit 1
out4=$(nfsmount 127.0.0.1:/export /nonexistent-nfsmount-mp-$$ 2>&1)
rc4=$?
[ "$rc4" != "0" ] || fail "missing-mountpoint run unexpectedly exited 0"
echo "$out4" | grep -q "No such file or directory" || fail "missing-mountpoint: unexpected output [$out4]"
echo "PASS 4: missing mountpoint -> stat perror (exit $rc4)"

echo "test klibc-nfsmount 2.0.14: 4/4 checks PASS"
exit 0
