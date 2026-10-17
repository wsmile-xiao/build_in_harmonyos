#!/usr/bin/env bash
# test.sh — rsyslog 8.2404.0 test_package
# 1) rsyslogd -v — version banner self-check (upstream output has two
#    spaces between "rsyslogd" and the version)
# 2) rsyslogd -N1 — config validation run: parses the config, initializes
#    classes, loads the default modules (lmnet, lmnetstrms, ...) through
#    RSYSLOG_MODDIR (exported by the package's runenv) and exits 0 only
#    on success. Exercises the real daemon initialization path.
set -euo pipefail

# NB: capture output in variables before grepping — a plain `cmd | grep -q`
# under pipefail can SIGPIPE the producer and fail the whole pipeline.
V_OUT="$(rsyslogd -v 2>&1)"
printf '%s\n' "$V_OUT" | grep -Eq 'rsyslogd +8\.2404\.0' > /dev/null
echo "rsyslogd version self-test passed"

TMP_BASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMP_BASE"
CONF="$TMP_BASE/rsyslog-test-$$.conf"
OUT="$TMP_BASE/rsyslog-test-$$.log"
trap 'rm -f "$CONF" "$OUT"' EXIT
{
  echo "global(workDirectory=\"$TMP_BASE\")"
  echo "*.* $OUT"
} > "$CONF"
N1_RC=0
N1_OUT="$(rsyslogd -N1 -f "$CONF" 2>&1)" || N1_RC=$?
printf '%s\n' "$N1_OUT"
[ "$N1_RC" -eq 0 ] || { echo "rsyslogd -N1 exited with $N1_RC"; exit 1; }
case "$N1_OUT" in
  *"config validation"*) ;;
  *) echo "rsyslogd -N1 produced no validation output"; exit 1 ;;
esac
echo "rsyslogd config validation (-N1) passed"
