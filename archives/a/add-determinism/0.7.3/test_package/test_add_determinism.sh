#!/bin/sh
set -eu

ADD_DET="$1"
LINKDUPES="$2"

VERSION_OUTPUT="$("$ADD_DET" --version)"
echo "$VERSION_OUTPUT"
echo "$VERSION_OUTPUT" | grep -F "0.7.3"

ADD_HELP="$("$ADD_DET" --help)"
echo "$ADD_HELP"
echo "$ADD_HELP" | grep -F "Usage"

LINK_HELP="$("$LINKDUPES" --help)"
echo "$LINK_HELP"
echo "$LINK_HELP" | grep -F "Usage"
