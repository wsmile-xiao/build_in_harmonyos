#!/bin/sh
set -eu

version=$(h2o -v 2>&1)
printf '%s\n' "$version" | grep -F "2.2.6"
