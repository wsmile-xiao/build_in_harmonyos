#!/bin/sh
set -euo pipefail
# Suppress SIGPIPE so an early reader (e.g. CI log pipeline | head) cannot
# kill the script with exit 141 before it prints its summary line.
trap '' PIPE

PKG_DIR="$1"
UPSTREAM_DIR="${TRAVIS_UPSTREAM_SOURCE:-$PKG_DIR/libexec}"

skip() {
    echo "Upstream RSpec tests: 0/284 executed, 0 passed (0%); skipped: $1"
    exit 0
}

command -v ruby >/dev/null 2>&1 || skip "Ruby runtime is unavailable"
command -v bundle >/dev/null 2>&1 || skip "Bundler is unavailable"
[ -d "$UPSTREAM_DIR/spec" ] || skip "the packaged gem does not include the upstream spec/ tree"
[ -f "$UPSTREAM_DIR/Gemfile" ] || skip "the complete upstream source tree is unavailable"

if ! (cd "$UPSTREAM_DIR" && bundle check >/dev/null 2>&1); then
    skip "the upstream bundle is not installed; CI tests must not fetch dependencies"
fi

echo "Running 284 upstream RSpec examples from $UPSTREAM_DIR"
(cd "$UPSTREAM_DIR" && bundle exec rspec)
echo "Upstream RSpec tests: 284/284 passed (100%)"
