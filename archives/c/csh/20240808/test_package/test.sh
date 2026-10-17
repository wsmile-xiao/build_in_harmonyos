#!/bin/sh
set -eu

csh=${1:?usage: test.sh /path/to/csh}
[ -x "$csh" ]

base=${TMPDIR:-${HOME:-/tmp}}
work=$base/csh-consumer-test.$$
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT HUP INT TERM

cat > "$work/program.csh" <<'EOF'
set value = 2
@ value = $value + 3
if ( $value != 5 ) exit 1
echo csh-consumer-ok
EOF

output=$($csh -f "$work/program.csh")
[ "$output" = "csh-consumer-ok" ]

command_output=$($csh -f -c 'echo csh-command-ok')
[ "$command_output" = "csh-command-ok" ]

: > "$work/one.txt"
: > "$work/two.txt"
cat > "$work/glob.csh" <<EOF
cd "$work"
echo *.txt
EOF
glob_output=$($csh -f "$work/glob.csh")
[ "$glob_output" = "one.txt two.txt" ]

pipeline_output=$($csh -f -c 'echo csh-pipeline-ok | cat')
[ "$pipeline_output" = "csh-pipeline-ok" ]

$csh -f -c "echo csh-redirect-ok > $work/result.txt"
[ "$(cat "$work/result.txt")" = "csh-redirect-ok" ]

for signal in INT SIGINT; do
    if signal_output=$($csh -f -c "kill -$signal 2147483647" 2>&1); then
        signal_rc=0
    else
        signal_rc=$?
    fi
    [ "$signal_rc" -eq 1 ]
    case "$signal_output" in
        *"Bad signal number"*) exit 1 ;;
    esac
done

printf '%s\n' 'csh consumer test passed'
