#!/usr/bin/env bash
# Consumer checks for the packaged isoquery binary.
# Arguments: <isoquery> <fixture-dir> <iso-codes-json-dir>
set -u
ISOQUERY=${1:?isoquery}
FIXDIR=${2:?fixture}
ISOJSON=${3:?isojson}
PASS=0
fail() {
  echo "FAIL: $1" >&2
  exit 1
}
ok() {
  PASS=$((PASS + 1))
  echo "PASS ${PASS}: $1"
}

[ -x "$ISOQUERY" ] || fail "binary is not executable: $ISOQUERY"
[ -f "$FIXDIR/iso_3166-1.json" ] || fail "fixture missing"
[ -f "$ISOJSON/iso_3166-1.json" ] || fail "iso-codes json missing: $ISOJSON/iso_3166-1.json"

version=$("$ISOQUERY" --version) || fail "version command failed"
printf '%s\n' "$version" | grep -F "isoquery 3.4.0" >/dev/null || fail "version text: $version"
ok "version banner is isoquery 3.4.0"
printf '%s\n' "$version" | grep -F "Copyright ©" >/dev/null || fail "utf-8 copyright missing"
ok "version banner keeps the UTF-8 copyright sign"

help_text=$("$ISOQUERY" --help) || fail "help failed"
printf '%s\n' "$help_text" | grep -F -- "--pathname" >/dev/null || fail "help has no --pathname"
ok "help documents --pathname"

stderr=$(mktemp)
if "$ISOQUERY" -p "/no/such/isoquery-dir" >/dev/null 2>"$stderr"; then
  fail "missing data directory exited 0"
fi
grep -F "/no/such/isoquery-dir" "$stderr" >/dev/null || fail "missing-dir stderr: $(cat "$stderr")"
ok "missing data directory is a hard error"

de=$("$ISOQUERY" -p "$FIXDIR" DE) || fail "DE query failed"
printf '%s\n' "$de" | grep -F "$(printf 'DE\tDEU\t276\tGermany')" >/dev/null || fail "DE line: $de"
ok "fixture query DE"

ci=$("$ISOQUERY" -p "$FIXDIR" CI) || fail "CI query failed"
printf '%s\n' "$ci" | grep -F "Côte d'Ivoire" >/dev/null || fail "utf-8 name: $ci"
ok "UTF-8 name Côte d'Ivoire round-trips"

official=$("$ISOQUERY" -p "$FIXDIR" --official_name DE) || fail "official name failed"
printf '%s\n' "$official" | grep -F "Federal Republic of Germany" >/dev/null || fail "official: $official"
ok "official_name field"

null_out=$(mktemp)
"$ISOQUERY" -p "$FIXDIR" -0 DE >"$null_out" || fail "null separator command failed"
python3 - "$null_out" <<'PY' || fail "null separator bytes"
import sys
data = open(sys.argv[1], "rb").read()
if not data.endswith(b"\0"):
    raise SystemExit("missing trailing NUL: %r" % data)
if b"\n" in data:
    raise SystemExit("newline leaked into NUL mode: %r" % data)
if not data.startswith(b"DE\tDEU\t276\tGermany"):
    raise SystemExit("unexpected record: %r" % data)
PY
ok "NUL separator instead of newline"

if ! "$ISOQUERY" -p "$FIXDIR" not-a-code >/dev/null 2>"$stderr"; then
  fail "unknown code should follow upstream and exit 0"
fi
grep -F 'is not defined in ISO 3166-1' "$stderr" >/dev/null || fail "unknown-code stderr: $(cat "$stderr")"
ok "unknown code reports the upstream English error"

real=$("$ISOQUERY" -p "$ISOJSON" -i 3166-1 DE) || fail "iso-codes DE query failed"
printf '%s\n' "$real" | grep -F "$(printf 'DE\tDEU\t276\t')" >/dev/null || fail "real DE line: $real"
printf '%s\n' "$real" | grep -F "Germany" >/dev/null || fail "real DE name: $real"
ok "published iso-codes JSON answers DE"

if "$ISOQUERY" DE >/dev/null 2>"$stderr"; then
  fail "default /usr/share/iso-codes/json unexpectedly succeeded"
fi
grep -F "/usr/share/iso-codes/json" "$stderr" >/dev/null || fail "default-path stderr: $(cat "$stderr")"
ok "compiled-in default data path is absent"

if "$ISOQUERY" -i 9999 >/dev/null 2>"$stderr"; then
  fail "invalid standard exited 0"
fi
grep -F 'is not supported' "$stderr" >/dev/null || fail "invalid-standard stderr: $(cat "$stderr")"
ok "invalid ISO standard is rejected"

rm -f "$stderr" "$null_out"
echo "OHOS_RESULT ${PASS}/${PASS}"
