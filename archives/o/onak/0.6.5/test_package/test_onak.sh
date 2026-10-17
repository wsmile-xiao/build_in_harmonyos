#!/bin/sh
# ---------------------------------------------------------------------------
# Consumer test for onak 0.6.5 (installed layout).
#
# Env:
#   ONAK_BIN          path to the installed onak executable
#   ONAK_BACKENDS_DIR path to the installed keydb backends (*.so)
#   ONAK_KEYFILE      path to a sample OpenPGP public key
# Exit: 0 = all checks passed, 1 = failure
# ---------------------------------------------------------------------------
set -eu

ONAK="${ONAK_BIN:?ONAK_BIN must point to the installed onak}"
BACKENDS="${ONAK_BACKENDS_DIR:?ONAK_BACKENDS_DIR must point to the backends dir}"
KEYFILE="${ONAK_KEYFILE:?ONAK_KEYFILE must point to a sample key}"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/onak-consumer.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

mkdir -p "$WORK/db"
touch "$WORK/blacklist"
cat > "$WORK/onak.ini" <<EOF
[main]
backend=test-file
backends_dir=$BACKENDS
logfile=$WORK/onak.log
loglevel=7
use_keyd=false
max_reply_keys=128

[backend:test-file]
type=file
location=$WORK/db

[verification]
blacklist=$WORK/blacklist
EOF

checks=0
fails=0
check() {
	checks=$((checks + 1))
	if [ "$2" = "$3" ]; then
		echo "PASS: $1"
	else
		echo "FAIL: $1 (got '$2', want '$3')"
		fails=$((fails + 1))
	fi
}

# 1. add a key through the dynamically loaded 'file' backend
"$ONAK" -b -c "$WORK/onak.ini" add < "$KEYFILE" > "$WORK/add.out" 2>&1 && rc=0 || rc=$?
check "add exits 0" "$rc" 0

# 2. retrieve it by long keyid
out="$("$ONAK" -c "$WORK/onak.ini" get 0x94FA372B2DA8B985 2>/dev/null || true)"
echo "$out" | grep -q 'BEGIN PGP PUBLIC KEY BLOCK' && ok=0 || ok=1
check "get by long keyid returns an armored key" "$ok" 0

# 3. the armored block is complete (base64 body, so check both delimiters)
echo "$out" | grep -q 'END PGP PUBLIC KEY BLOCK' && ok=0 || ok=1
check "retrieved armored block is complete" "$ok" 0

# 4. retrieve it by short keyid
out="$("$ONAK" -c "$WORK/onak.ini" get 0x2DA8B985 2>/dev/null || true)"
echo "$out" | grep -q 'BEGIN PGP PUBLIC KEY BLOCK' && ok=0 || ok=1
check "get by short keyid returns an armored key" "$ok" 0

# 5. delete it
"$ONAK" -b -c "$WORK/onak.ini" delete 0x94FA372B2DA8B985 > "$WORK/del.out" 2>&1 && rc=0 || rc=$?
check "delete exits 0" "$rc" 0

# 6. it is gone
out="$("$ONAK" -c "$WORK/onak.ini" get 0x94FA372B2DA8B985 2>&1 || true)"
echo "$out" | grep -q 'Key not found' && ok=0 || ok=1
check "get after delete reports Key not found" "$ok" 0

echo "ONAK_CHECK_SUMMARY checks=$checks fails=$fails"
[ "$fails" -eq 0 ]
