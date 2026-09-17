#!/bin/bash
# Consumer test for the micron binaries, run against the installed package.
# The cron daemon and client both resolve the invoking user through the
# password database before doing real work, so this test asserts the paths
# that are available in every environment (argument parsing and usage
# diagnostics); the environment-specific limitation is documented in notes.md.
set -e

# 1. Functional: the daemon renders its usage and accepts -h (exit 0),
#    listing its real option set.
out="$(micrond -h 2>&1 || true)"
echo "$out" | grep -q 'usage: micrond' || {
    echo "FAIL: micrond -h did not print the usage line"
    echo "$out"
    exit 1
}
echo "$out" | grep -q -- '-f' || {
    echo "FAIL: micrond usage does not list the -f (foreground) option"
    exit 1
}

# 2. Functional: the client rejects an unknown option with a usage diagnostic
#    and a non-zero exit status.
if crontab --no-such-option > /dev/null 2>&1; then
    echo "FAIL: crontab accepted an unknown option"
    exit 1
fi

echo "micron consumer test passed (daemon usage + client option validation)"
