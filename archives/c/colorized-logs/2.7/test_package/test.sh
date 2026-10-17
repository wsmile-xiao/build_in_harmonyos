#!/bin/bash
# test_package consumer verification for colorized-logs 2.7.
# Simulates a business-layer user: feeds ANSI-colored log text through the
# installed ansi2txt / ansi2html / ttyrec2ansi filters and checks observable
# decoded output, exactly as a real user would on the command line.
# NOTE: output is captured into temp files (not $(...)) because command
# substitution drops NUL bytes from ttyrec binary headers (same technique as
# the upstream testsuite).
set -u

fail=0
TMPDIR=${TMPDIR:-/tmp}
stdin_f="$TMPDIR/cl-stdin.$$"
stdout_f="$TMPDIR/cl-stdout.$$"

trap 'rm -f "$stdin_f" "$stdout_f"' EXIT

# --- ansi2txt: strip ANSI color codes from log text ----------------------
printf 'foo\033[1mbar\033[0m\n' > "$stdin_f"
ansi2txt < "$stdin_f" > "$stdout_f" 2>&1
if [ "$(cat "$stdout_f")" = "foobar" ]; then
    echo "ansi2txt: OK (ANSI codes stripped)"
else
    echo "ansi2txt: FAIL got '$(cat "$stdout_f")'"
    fail=1
fi

# --- ansi2html: convert ANSI-colored text to HTML <pre> block -------------
ansi2html < "$stdin_f" > "$stdout_f" 2>&1
case "$(cat "$stdout_f")" in
    *"<pre>"*) echo "ansi2html: OK (produces HTML <pre> block)" ;;
    *) echo "ansi2html: FAIL got '$(cat "$stdout_f")'"; fail=1 ;;
esac

# --- ttyrec2ansi: replay a ttyrec byte stream ----------------------------
# ttyrec format: 12-byte header (sec, usec, len little-endian) + payload.
# Same byte sequence as the upstream testsuite case.
printf 'aaaa10\a\0\b\0\0\0foo bar\n' > "$stdin_f"
ttyrec2ansi < "$stdin_f" > "$stdout_f" 2>"$stdout_f.err"
if [ "$(cat "$stdout_f")" = "foo bar" ]; then
    echo "ttyrec2ansi: OK (replay decoded)"
else
    echo "ttyrec2ansi: FAIL got '$(cat "$stdout_f")'"
    fail=1
fi
rm -f "$stdout_f.err"

# --- pipetty: allocates a pty for the child command ----------------------
# OHOS note: `pipetty sh -c '...'` does not work (sh -c variant fails);
# use the upstream testsuite invocation form `pipetty </dev/null sh <script>`
# which allocates the pty and runs the script through the pty.
printf 'test -t 0\nprintf "isatty(0): %%d\\n" $?\ntest -t 1\nprintf "isatty(1): %%d\\n" $?\n' > "$stdin_f"
pipetty </dev/null sh "$stdin_f" > "$stdout_f" 2>&1
if [ "$(cat "$stdout_f")" = "isatty(0): 1
isatty(1): 0" ]; then
    echo "pipetty: OK (pty allocated)"
else
    echo "pipetty: FAIL got '$(cat "$stdout_f")'"
    fail=1
fi

# --- lesstty symlink present in bin --------------------------------------
if [ -x "$(command -v lesstty)" ] || [ -L "$(command -v lesstty)" ]; then
    echo "lesstty: OK (present)"
else
    echo "lesstty: FAIL (not found)"
    fail=1
fi

exit $fail
