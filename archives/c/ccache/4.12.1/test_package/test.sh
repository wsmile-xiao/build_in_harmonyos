#!/bin/sh
# test.sh — smoke test for ccache binary
# Runs ccache --version to verify the installed binary works correctly.
set -e

ccache --version
