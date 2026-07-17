#!/usr/bin/env sh
# test_package/test.sh — zsh-autopair basic file existence check
set -eu
: "${ZSH_AUTOPAIR_PLUGIN:?ZSH_AUTOPAIR_PLUGIN is required}"
test -f "$ZSH_AUTOPAIR_PLUGIN"