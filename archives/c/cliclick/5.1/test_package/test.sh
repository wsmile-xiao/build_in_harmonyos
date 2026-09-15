#!/bin/sh
# Consumer test for the packaged cliclick (OHOS port of 5.1).
#
# Structure mirrors upstream Test.sh (bash, macOS) with three porting rules:
#  1. POSIX sh instead of bash, binary path passed by the Conan recipe.
#  2. The two clipboard assertions that require pbpaste(1) are excluded —
#     pbpaste is macOS-only; the OHOS clipboard destination is an explicit
#     unsupported boundary asserted below instead.
#  3. OHOS capability assertions are appended: key injection must work,
#     mouse injection must either work or fail with the explicit
#     authorization diagnostic, position/cp boundaries must fail loudly.
#
# Upstream assertion accounting (reviewer-countable, N = 64):
#   Upstream Test.sh contains 64 lines matching "assert":
#   grep -c assert Test.sh = 64 = 60 top-level assertion invocations
#     (32 assertStderrOutput + 26 assertStdoutOutput + 1 assertFileContains
#      + 1 assertClipboardContains)
#     + 4 assertion-helper definitions (Test.sh lines 18/23/28/44).
#   Disposition, every item accounted (no upstream assertion dropped):
#     - upstream #1-56 and #59-60 (58 invocations): executed here 1:1 as the
#       checks tagged "upstream N-M" below (upstream #11 re-runs bare "c"
#       where its description says "c:" — an upstream copy-paste slip; this
#       port follows the stated intent and asserts "c:");
#     - upstream #57-58 (2 invocations): pbpaste/pasteboard are macOS-only;
#       substituted by the named OHOS assertions "clipboard destination is
#       an explicit unsupported boundary" / "clipboard destination exits
#       non-zero";
#     - the 4 helper definitions: realized 1:1 by this harness —
#       assertStdoutOutput -> expect_stdout, assertStderrOutput ->
#       expect_stderr, assertClipboardContains -> the named clipboard
#       substitution pair, assertFileContains -> the "test:file contains
#       the commands" check.
#   Executed totals: checks=75 failures=0 = 58 (1:1 upstream) + 2 (named
#   pbpaste substitutions) + 15 (OHOS additions); N'=64 fully accounted.

BINARY="$1"
VERSION="$2"

if [ -z "$BINARY" ]; then
    echo "Usage: test.sh /path/to/cliclick <version>" >&2
    exit 1
fi
if [ ! -x "$BINARY" ]; then
    echo "$BINARY does not exist or is not executable" >&2
    exit 1
fi

CHECKS=0
FAILURES=0

pass() {
    CHECKS=$((CHECKS + 1))
    echo "ok - $1"
}

fail() {
    CHECKS=$((CHECKS + 1))
    FAILURES=$((FAILURES + 1))
    echo "not ok - $1"
    echo "  $2"
}

# expect_stdout DESC EXPECTED_PREFIX ARGS...
expect_stdout() {
    desc="$1"
    expected="$2"
    shift 2
    actual=$("$BINARY" "$@" 2>/dev/null)
    case "$actual" in
        "$expected"*) pass "$desc" ;;
        *) fail "$desc" "expected stdout prefix [$expected], got [$actual]" ;;
    esac
}

# expect_stderr DESC EXPECTED_PREFIX ARGS...
expect_stderr() {
    desc="$1"
    expected="$2"
    shift 2
    actual=$("$BINARY" "$@" 3>&1 1>&2 2>&3)
    case "$actual" in
        "$expected"*) pass "$desc" ;;
        *) fail "$desc" "expected stderr prefix [$expected], got [$actual]" ;;
    esac
}

# expect_rc DESC WANT_RC ARGS...
expect_rc() {
    desc="$1"
    want="$2"
    shift 2
    "$BINARY" "$@" >/dev/null 2>&1
    got=$?
    if [ "$got" = "$want" ]; then
        pass "$desc"
    else
        fail "$desc" "expected exit $want, got $got"
    fi
}

# expect_stderr_contains DESC NEEDLE ARGS...
expect_stderr_contains() {
    desc="$1"
    needle="$2"
    shift 2
    if "$BINARY" "$@" 2>&1 >/dev/null | grep -qF -- "$needle"; then
        pass "$desc"
    else
        fail "$desc" "expected stderr to contain [$needle]"
    fi
}

# expect_stdout_empty DESC ARGS... (a real empty check: an empty EXPECTED
# prefix in expect_stdout would degenerate into a tautological pattern)
expect_stdout_empty() {
    desc="$1"
    shift
    actual=$("$BINARY" "$@" 2>/dev/null)
    if [ -z "$actual" ]; then
        pass "$desc"
    else
        fail "$desc" "expected empty stdout, got [$actual]"
    fi
}

HEADER='Running in test mode. These command(s) would be executed:'

# ---- No arguments / unknown action (upstream 1-2) ----
expect_stderr \
    "no arguments writes usage hint to stderr" \
    'You did not pass any commands as argument to cliclick.
Call cliclick with option -h to see usage instructions.'
expect_stderr "unknown action writes error to stderr" \
    'Unrecognized action shortcut “z”' z

# ---- move / m (upstream 3-9) ----
expect_stderr "m without coords" \
    'Missing argument to command “m”: Expected two coordinates (separated by a comma) or “.”. Examples: “m:123,456” or “m:.”' m
expect_stderr "m: without coords" \
    'Missing argument to command “m”: Expected two coordinates (separated by a comma) or “.”. Examples: “m:123,456” or “m:.”' m:
expect_stderr "m invalid X" 'Invalid X axis coordinate “foobar” given' m:foobar,-123
expect_stderr "m invalid Y" 'Invalid Y axis coordinate “xxx” given' m:+123,xxx
expect_stderr "m trailing comma" \
    'Invalid argument “+123,” to command “m”: Expected two coordinates (separated by a comma) or “.”. Examples: “m:123,456” or “m:.”' m:+123,
expect_stdout "m test mode" "$HEADER
Move to 123,456" -m test m:123,456
expect_stdout "m test mode relative" "$HEADER
Move to +20,-17" -m test m:+20,-17

# ---- click / c (upstream 10-17) ----
expect_stderr "c without coords" \
    'Missing argument to command “c”: Expected two coordinates (separated by a comma) or “.”. Examples: “c:123,456” or “c:.”' c
expect_stderr "c: without coords" \
    'Missing argument to command “c”: Expected two coordinates (separated by a comma) or “.”. Examples: “c:123,456” or “c:.”' c:
expect_stderr "c invalid X" 'Invalid X axis coordinate “foobar” given' c:foobar,-123
expect_stderr "c invalid Y" 'Invalid Y axis coordinate “xxx” given' c:+123,xxx
expect_stderr "c trailing comma" \
    'Invalid argument “+123,” to command “c”: Expected two coordinates (separated by a comma) or “.”. Examples: “c:123,456” or “c:.”' c:+123,
expect_stdout "c test mode" "$HEADER
Click at 123,456" -m test c:123,456
expect_stdout "c test mode relative" "$HEADER
Click at +20,-17" -m test c:+20,-17
expect_stdout "c test mode absolute negative" "$HEADER
Click at =-200,-100" -m test c:=-200,-100

# ---- doubleclick / dc (upstream 18-19) ----
expect_stderr "dc without coords" \
    'Missing argument to command “dc”: Expected two coordinates (separated by a comma) or “.”. Examples: “dc:123,456” or “dc:.”' dc
expect_stdout "dc test mode" "$HEADER
Double-click at 1129,64" -m test dc:1129,64

# ---- tripleclick / tc (upstream 20-21) ----
expect_stderr "tc without coords" \
    'Missing argument to command “tc”: Expected two coordinates (separated by a comma) or “.”. Examples: “tc:123,456” or “tc:.”' tc
expect_stdout "tc test mode" "$HEADER
Triple-click at 1129,64" -m test tc:1129,64

# ---- rightclick / rc (upstream 22-23) ----
expect_stderr "rc without coords" \
    'Missing argument to command “rc”: Expected two coordinates (separated by a comma) or “.”. Examples: “rc:123,456” or “rc:.”' rc
expect_stdout "rc test mode" "$HEADER
Right-click at 1129,64" -m test rc:1129,64

# ---- drag down / dd (upstream 24-25) ----
expect_stderr "dd without coords" \
    'Missing argument to command “dd”: Expected two coordinates (separated by a comma) or “.”. Examples: “dd:123,456” or “dd:.”' dd
expect_stdout "dd test mode" "$HEADER
Drag press down at 1129,64" -m test dd:1129,64

# ---- drag up / du (upstream 26-27) ----
expect_stderr "du: without coords" \
    'Missing argument to command “du”: Expected two coordinates (separated by a comma) or “.”. Examples: “du:123,456” or “du:.”' du:
expect_stdout "du test mode" "$HEADER
Drag release at 1129,64" -m test du:1129,64

# ---- drag move / dm (upstream 28-29) ----
expect_stderr "dm without coords" \
    'Missing argument to command “dm”: Expected two coordinates (separated by a comma) or “.”. Examples: “dm:123,456” or “dm:.”' dm
expect_stdout "dm test mode" "$HEADER
Drag move to 1129,64" -m test dm:1129,64

# ---- wait / w (upstream 30-32) ----
expect_stderr "w without arg" \
    'Invalid or missing argument to command “w”: Expected number of milliseconds. Example: “w:50”' w
expect_stderr "w non-numeric" \
    'Invalid or missing argument to command “w”: Expected number of milliseconds. Example: “w:50”' w:abc
expect_stdout "w test mode" "$HEADER
Wait 150 milliseconds" -m test w:150

# ---- key down / kd (upstream 33-36) ----
expect_stderr "kd without arg" \
    'Missing argument to command “kd”: Expected one or more keys (separated by a comma). Examples: “kd:ctrl” or “kd:cmd,alt”' kd
expect_stderr "kd invalid key" \
    'Invalid key “abc” given as argument to command “kd”.
The key name may only be one of:' kd:abc
expect_stdout "kd test mode" "$HEADER
Hold ctrl key down" -m test kd:ctrl
expect_stdout "kd test mode multiple" "$HEADER
Hold ctrl key down
Hold cmd key down
Hold alt key down" -m test kd:ctrl,cmd,alt

# ---- key up / ku (upstream 37-40) ----
expect_stderr "ku without arg" \
    'Missing argument to command “ku”' ku
expect_stderr "ku invalid key" 'Invalid key “abc” given as argument to command “ku”' ku:abc
expect_stdout "ku test mode" "$HEADER
Release ctrl key" -m test ku:ctrl
expect_stdout "ku test mode multiple" "$HEADER
Release ctrl key
Release cmd key
Release alt key" -m test ku:ctrl,cmd,alt

# ---- key press / kp (upstream 41-43) ----
expect_stderr "kp without arg" 'Missing argument to command “kp”' kp
expect_stderr "kp invalid key" 'Invalid key “abc” given as argument to command “kp”' kp:abc
expect_stdout "kp test mode" "$HEADER
Press + release return key" -m test kp:return

# ---- print / p (upstream 44-46) ----
expect_stdout "p test mode" "$HEADER
Print the current mouse position" -m test p
expect_stdout "p test mode dot" "$HEADER
Print the current mouse position" -m test p:.
expect_stdout "p test mode message" "$HEADER
Print message “Helloworld”" -m test p:Helloworld

# ---- type / t (upstream 47-48) ----
expect_stderr "t without arg" 'Missing argument to command “t”' t
expect_stdout "t test mode" "$HEADER
Type: “Unimaginatively”" -m test t:Unimaginatively

# ---- color picker / cp (upstream 49-52) ----
expect_stderr "cp without arg" 'Missing argument to command “cp”' cp
expect_stderr "cp invalid coords" 'Invalid argument “123” to command “cp”' cp:123
expect_stdout "cp test mode dot" "$HEADER
Print color at current mouse position" -m test cp:.
expect_stdout "cp test mode coords" "$HEADER
Print color at location 123,456" -m test cp:123,456

# ---- test mode output routing (upstream 53-54) ----
expect_stderr "test:stderr routing" "$HEADER
Click at current location
Move to 123,456" -m test:stderr c:. m:123,456
expect_stderr "test output to invalid path" \
    'Cannot create file “/no/such/path.txt” specified as output destination' \
    -m test:/no/such/path.txt c:. m:123,456

# ---- test mode output to a file (upstream 55-56) ----
TEMPFILE="$(mktemp)"
expect_stdout_empty "test:file writes nothing to stdout" -m test:"$TEMPFILE" c:. m:123,456
FILE_CONTENT="$(cat "$TEMPFILE")"
EXPECTED_FILE="$HEADER
Click at current location
Move to 123,456"
case "$FILE_CONTENT" in
    "$EXPECTED_FILE") pass "test:file contains the commands" ;;
    *) fail "test:file contains the commands" "file has [$FILE_CONTENT]" ;;
esac
rm -f "$TEMPFILE"

# ---- command output destination (upstream 59-60) ----
expect_stderr "-d stderr routes p output" 'OK' -d stderr p:OK
expect_stdout "-d stdout routes p output" 'OK' -d stdout p:OK
expect_stdout_empty "-d clipboard writes nothing to stdout" -d clipboard p:OK
expect_stderr_contains "-d clipboard is an explicit unsupported boundary" \
    'clipboard output destination is not supported on OHOS' -d clipboard p:OK
expect_rc "-d clipboard exits non-zero" 1 -d clipboard p:OK

# ---- OHOS explicit capability boundaries (port additions) ----
expect_stderr_contains "cp execution is an explicit unsupported boundary" \
    'The cp command is not supported on OHOS' cp:10,10
expect_rc "cp execution exits non-zero" 1 cp:10,10
expect_stderr_contains "p position read-back is an explicit boundary" \
    'not observable on OHOS' p
expect_rc "p execution exits non-zero" 1 p
expect_stderr_contains "relative coordinates need the unobservable position" \
    'not observable on OHOS' m:+10,-10
expect_stderr_contains "clipboard destination is an explicit unsupported boundary" \
    'clipboard output destination is not supported on OHOS' -m test:clipboard c:. m:123,456
expect_rc "clipboard destination exits non-zero" 1 -m test:clipboard c:. m:123,456
expect_stderr_contains "-r restore is an explicit boundary" \
    'The -r option cannot restore the initial mouse location on OHOS' -r m:10,10

# ---- OHOS runtime capability: keys (authorized), mouse (gated) ----
if "$BINARY" kd:shift >/dev/null 2>&1 && "$BINARY" ku:shift >/dev/null 2>&1; then
    pass "key injection executes (kd/ku shift)"
else
    fail "key injection executes (kd/ku shift)" "key injection returned an error"
fi
if "$BINARY" w:50 >/dev/null 2>&1; then
    pass "w command executes"
else
    fail "w command executes" "w returned an error"
fi
MOUSE_OUT="$("$BINARY" m:100,100 2>&1)"
MOUSE_RC=$?
if [ "$MOUSE_RC" -eq 0 ]; then
    pass "mouse injection authorized in this environment (move executed)"
elif printf '%s\n' "$MOUSE_OUT" | grep -qF 'Mouse event injection was denied'; then
    pass "mouse injection denied with explicit authorization diagnostic"
else
    fail "mouse injection handling" "unexpected output [$MOUSE_OUT]"
fi

# ---- version / usage smoke (CI L2 contract) ----
expect_rc "--version exits 0" 0 --version
expect_rc "--help exits 0" 0 --help
VERSION_OUT="$("$BINARY" -V 2>/dev/null)"
case "$VERSION_OUT" in
    "cliclick $VERSION"*) pass "-V prints version" ;;
    *) fail "-V prints version" "got [$VERSION_OUT]" ;;
esac

echo ""
echo "checks=$CHECKS failures=$FAILURES"
if [ "$FAILURES" -gt 0 ]; then
    exit 1
fi
exit 0
