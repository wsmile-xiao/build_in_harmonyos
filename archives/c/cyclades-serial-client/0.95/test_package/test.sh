#!/bin/sh
cyclades-ser-cli -h >/dev/null 2>&1
rc=$?
test "$rc" -eq 2
