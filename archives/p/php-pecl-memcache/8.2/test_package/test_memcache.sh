#!/bin/sh
# Test script for php-pecl-memcache extension
# This script loads the memcache extension with PHP and verifies it's loaded
#
# Usage: test_memcache.sh <php_binary> <memcache_so_path>

set -euo pipefail

PHP_BIN="${1:-php}"
MEMCACHE_SO="${2:-memcache.so}"

# Check if the extension file exists
if [ ! -f "$MEMCACHE_SO" ]; then
    echo "FAIL: memcache.so not found at $MEMCACHE_SO"
    exit 1
fi

# Load the extension with PHP and verify it's registered
"$PHP_BIN" -d "extension=$MEMCACHE_SO" -r "exit(extension_loaded('memcache') ? 0 : 1);"
RESULT=$?

if [ $RESULT -eq 0 ]; then
    echo "PASS: memcache extension loaded successfully"
    exit 0
else
    echo "FAIL: memcache extension not loaded by PHP"
    exit 1
fi
