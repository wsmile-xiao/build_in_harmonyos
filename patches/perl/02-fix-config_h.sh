#!/bin/sh
# fix_config_h.sh - Fix duplicate case block in config_h.SH
# 
# Bug: Original config_h.SH (from Perl 5.42.2) has a duplicate nested
# "case \$CONFIG_H in" block around line 31-33 that causes a syntax
# error when executed with sh/dash on HarmonyOS.
#
# The duplicate looks like:
#   case "$CONFIG_H" in
#   already-done) ... ;;
#   *)
#   case "$CONFIG_H" in       <-- DUPLICATE (inner)
#   already-done) ... ;;
#   *)
#   ...actual heredoc content...

set -e

FILE="$1"
if [ -z "$FILE" ]; then
    echo "Usage: $0 <config_h.SH_path>"
    exit 1
fi

if [ ! -f "$FILE" ]; then
    echo "Error: $FILE not found"
    exit 1
fi

# Use perl to remove the duplicate inner case block.
# The pattern: after the first "case \$CONFIG_H" block's *) line,
# there's an unwanted second "case \$CONFIG_H" + its already-done + *).
# We need to remove those 3 lines.

perl -i -0pe '
    # Match the duplicate pattern and remove it:
    #   case "$CONFIG_H" in        (duplicate)
    #   already-done) ... ;;        (duplicate)
    #   *)                          (duplicate - closes the dup)
    s(
        case "\$CONFIG_H" in \n
        already-done\).*? \*\) \n
        \*\)                       # <-- this is the original closing *)
        \n
        case "\$CONFIG_H" in \n    # <-- DUPLICATE START
        already-done\).*? \*\) \n  # <-- DUPLICATE MIDDLE
        \*\)                       # <-- DUPLICATE END
    )(\n)){$2}sx
' "$FILE"

echo "Fixed duplicate case block in $FILE"
