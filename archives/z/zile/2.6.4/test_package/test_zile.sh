#!/bin/sh
# Consumer test for GNU zile 2.6.4 — asserts real tool behaviour.
#
# zile is a curses fullscreen editor: the batch lisp assertion needs a
# terminfo database (provided by the ncurses package, exported as
# TERMINFO by the caller) because OHOS ships none.
set -e
BIN="$1"
TERM_ROOT="$2"
WORK="$3"
if [ -z "$BIN" ] || [ ! -x "$BIN/zile" ]; then
    echo "usage: test_zile.sh <package-bindir> <ncurses-package-root> <tmpdir>" >&2
    exit 2
fi
[ -n "$WORK" ] || { echo "usage: empty tmpdir argument" >&2; exit 2; }
rm -rf "$WORK/rt"; mkdir -p "$WORK/rt"
export TERM=xterm
if [ -d "$TERM_ROOT/share/terminfo" ]; then
    export TERMINFO="$TERM_ROOT/share/terminfo"
fi

# 1. version banner identifies the tool
"$BIN/zile" --version | grep -q "GNU Zile 2.6.4" || {
    echo "FAIL: unexpected --version output" >&2; exit 1; }

# 2. usage output
"$BIN/zile" --help 2>&1 | grep -q "Usage:" || {
    echo "FAIL: unexpected --help output" >&2; exit 1; }

# 3. batch lisp evaluation: edit a file through the built-in interpreter
#    and assert the saved result (same mechanism as upstream tests/*.el)
printf 'hello\n' > "$WORK/rt/file.txt"
cat > "$WORK/rt/consumer.el" <<'EL'
(end-of-line)
(insert " zile")
(save-buffer)
(save-buffers-kill-emacs)
EL
"$BIN/zile" --no-init-file "$WORK/rt/file.txt" --load "$WORK/rt/consumer.el" >/dev/null 2>&1
printf 'hello zile\n' > "$WORK/rt/expected.txt"
cmp -s "$WORK/rt/file.txt" "$WORK/rt/expected.txt" || {
    echo "FAIL: batch lisp edit did not produce expected content" >&2; exit 1; }

echo "zile 2.6.4 consumer test: OK (version/usage/batch-lisp-edit assertions)"
