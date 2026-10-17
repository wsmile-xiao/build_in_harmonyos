#!/bin/sh

test "$#" -eq 5 || exit 10
test "$1" = "job-123" || exit 11
test "$2" = "currentUser" || exit 12
test "$3" = "document-title" || exit 13
test "$4" = "1" || exit 14
test "$5" = "media=a4" || exit 15

printf 'CUPS_EXEC_FALLBACK_ASSERTIONS=6/6 argv0=%s\n' "$0"
