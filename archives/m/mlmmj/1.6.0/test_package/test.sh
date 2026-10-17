#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer end-to-end test for mlmmj 1.6.0.
#
# Runs in the conanrun environment: PATH already contains the packaged
# bin/ directory.  Creates a real mailing list with the packaged
# mlmmj-make-ml, then drives mlmmj-sub / mlmmj-unsub / mlmmj-list against
# it — every case executes the real installed binaries and checks their
# real output and exit codes.  No mail is ever sent (silent subscription
# triple -f -q -s; -U avoids the setuid to the listdir owner, which is
# unreliable on HMDFS uid mapping).
#
# OHOS invocation notes (device-verified):
#   * mlmmj ELF tools all carry CHECKFULLPATH (include/mlmmj.h): argv[0]
#     must contain a '/', so every tool below is invoked by absolute path.
#   * OHOS has no binfmt_script: a shell script can never be started via
#     its shebang — the packaged mlmmj-make-ml script is started as
#     `sh /abs/path/mlmmj-make-ml`.
#
# Output contract: "TEST PASS: <case>" / "TEST FAIL: <case>" per case,
# final line "TEST SUMMARY: N passed, M failed"; exit 1 on any failure.
set -u

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "TEST PASS: $1"; }
bad() { FAIL=$((FAIL + 1)); echo "TEST FAIL: $1"; }

WS="$PWD/e2e-work"
rm -rf "$WS"
mkdir -p "$WS/spool"
LDIR="$WS/spool/testlist"

BIN_DIR="$(dirname "$(command -v mlmmj-sub)")"
SUB="$BIN_DIR/mlmmj-sub"
UNSUB="$BIN_DIR/mlmmj-unsub"
LIST="$BIN_DIR/mlmmj-list"
MAKEML="$BIN_DIR/mlmmj-make-ml"
echo "# mlmmj bin dir: $BIN_DIR"

# ── fixture: answer file for non-interactive list creation ──────────
cat > "$WS/answers" <<EOF
SPOOLDIR='$WS/spool'
LISTNAME='testlist'
FQDN='lists.example.org'
OWNER='owner@example.org'
TEXTLANG='en'
ADDALIAS='n'
DO_CHOWN='n'
CHOWN=''
ADDCRON='n'
EOF

# ── 1. create the list with the packaged mlmmj-make-ml ─────────────
if sh "$MAKEML" -f "$WS/answers" > "$WS/make-ml.log" 2>&1 \
   && [ -f "$LDIR/control/owner" ] && [ -f "$LDIR/control/listaddress" ]; then
    ok "make-ml creates list tree (control/owner + control/listaddress)"
else
    bad "make-ml creates list tree (control/owner + control/listaddress)"
    echo "--- make-ml.log ---"; cat "$WS/make-ml.log"
fi

# ── 2. control files carry the configured values ────────────────────
if [ "$(cat "$LDIR/control/owner")" = "owner@example.org" ] \
   && [ "$(cat "$LDIR/control/listaddress")" = "testlist@lists.example.org" ]; then
    ok "control/owner and control/listaddress content"
else
    bad "control/owner and control/listaddress content"
fi

# ── 3. text skeleton deployed from the package (relocatable TEXTLIBDIR)
ntext=$(ls -1 "$LDIR/text" 2>/dev/null | wc -l)
if [ "$ntext" -eq 17 ] && [ -f "$LDIR/text/confirm" ] && [ -f "$LDIR/text/digest" ]; then
    ok "text skeleton: 17 files copied from packaged share/mlmmj/text.skel/en"
else
    bad "text skeleton: expected 17 files, got $ntext"
fi

# ── 4. silent subscribe alice (normal) ──────────────────────────────
if "$SUB" -L "$LDIR" -a alice@example.org -f -q -s -U > "$WS/sub1.log" 2>&1 \
   && [ "$("$LIST" -L "$LDIR")" = "alice@example.org" ]; then
    ok "mlmmj-sub subscribes alice; mlmmj-list lists alice"
else
    bad "mlmmj-sub subscribes alice; mlmmj-list lists alice"
    echo "--- sub1.log ---"; cat "$WS/sub1.log"
fi

# ── 5. default subscriber count is 1 ────────────────────────────────
if [ "$("$LIST" -L "$LDIR" -c)" = "1" ]; then
    ok "mlmmj-list -c (normal) == 1"
else
    bad "mlmmj-list -c (normal) == 1 (got $("$LIST" -L "$LDIR" -c))"
fi

# ── 6. digest subscription: bob ─────────────────────────────────────
if "$SUB" -L "$LDIR" -a bob@example.org -d -f -q -s -U > "$WS/sub2.log" 2>&1 \
   && [ "$("$LIST" -L "$LDIR" -d)" = "bob@example.org" ] \
   && [ "$("$LIST" -L "$LDIR" -d -c)" = "1" ]; then
    ok "mlmmj-sub -d subscribes bob to digest; -d -c == 1"
else
    bad "mlmmj-sub -d subscribes bob to digest; -d -c == 1"
    echo "--- sub2.log ---"; cat "$WS/sub2.log"
fi

# ── 7. nomail subscription: carol ───────────────────────────────────
if "$SUB" -L "$LDIR" -a carol@example.org -n -f -q -s -U > "$WS/sub3.log" 2>&1 \
   && [ "$("$LIST" -L "$LDIR" -n)" = "carol@example.org" ] \
   && [ "$("$LIST" -L "$LDIR" -n -c)" = "1" ]; then
    ok "mlmmj-sub -n subscribes carol to nomail; -n -c == 1"
else
    bad "mlmmj-sub -n subscribes carol to nomail; -n -c == 1"
    echo "--- sub3.log ---"; cat "$WS/sub3.log"
fi

# ── 8. subscriber partitions stay separated ─────────────────────────
n_normal=$("$LIST" -L "$LDIR" -c)
n_digest=$("$LIST" -L "$LDIR" -d -c)
n_nomail=$("$LIST" -L "$LDIR" -n -c)
if [ "$n_normal" = "1" ] && [ "$n_digest" = "1" ] && [ "$n_nomail" = "1" ]; then
    ok "partitions: normal=$n_normal digest=$n_digest nomail=$n_nomail (no cross-contamination)"
else
    bad "partitions: normal=$n_normal digest=$n_digest nomail=$n_nomail"
fi

# ── 9. duplicate silent subscription is idempotent ──────────────────
if "$SUB" -L "$LDIR" -a alice@example.org -f -q -s -U > "$WS/sub4.log" 2>&1 \
   && [ "$("$LIST" -L "$LDIR" -c)" = "1" ]; then
    ok "duplicate subscribe alice is a no-op (count still 1)"
else
    bad "duplicate subscribe alice is a no-op"
    echo "--- sub4.log ---"; cat "$WS/sub4.log"
fi

# ── 10. owner listing ───────────────────────────────────────────────
if [ "$("$LIST" -L "$LDIR" -o)" = "owner@example.org" ]; then
    ok "mlmmj-list -o prints control/owner"
else
    bad "mlmmj-list -o prints control/owner"
fi

# ── 11. silent unsubscribe carol ────────────────────────────────────
if "$UNSUB" -L "$LDIR" -a carol@example.org -q -s -U > "$WS/unsub1.log" 2>&1 \
   && [ "$("$LIST" -L "$LDIR" -n -c)" = "0" ]; then
    ok "mlmmj-unsub removes carol from nomail (count 0)"
else
    bad "mlmmj-unsub removes carol from nomail (count 0)"
    echo "--- unsub1.log ---"; cat "$WS/unsub1.log"
fi

# ── 12. other partitions untouched by carol's removal ───────────────
if [ "$("$LIST" -L "$LDIR" -c)" = "1" ] && [ "$("$LIST" -L "$LDIR" -d -c)" = "1" ]; then
    ok "normal=1 digest=1 after carol removal"
else
    bad "normal=1 digest=1 after carol removal"
fi

# ── 13. mlmmj-recieve alias is a real file (E050 copy, not symlink) ─
if [ -f "$BIN_DIR/mlmmj-recieve" ] && [ ! -L "$BIN_DIR/mlmmj-recieve" ] \
   && "$BIN_DIR/mlmmj-recieve" -h > /dev/null 2>&1; then
    ok "mlmmj-recieve alias is a regular executable copy (-h exits 0)"
else
    bad "mlmmj-recieve alias check"
fi

# ── 14. mlmmj-make-ml.sh alias is a real file ───────────────────────
if [ -f "$BIN_DIR/mlmmj-make-ml.sh" ] && [ ! -L "$BIN_DIR/mlmmj-make-ml.sh" ] \
   && sh "$BIN_DIR/mlmmj-make-ml.sh" -h > /dev/null 2>&1; then
    ok "mlmmj-make-ml.sh alias is a regular executable copy (-h exits 0)"
else
    bad "mlmmj-make-ml.sh alias check"
fi

# ── 15. version banner ──────────────────────────────────────────────
vout="$("$SUB" -V 2>&1)"
case "$vout" in
    *"mlmmj-sub version 1.6.0"*) ok "mlmmj-sub -V prints version 1.6.0" ;;
    *) bad "mlmmj-sub -V prints version 1.6.0 (got: $vout)" ;;
esac

# ── 16. all 11 installed commands present and executable ────────────
missing=""
for tool in mlmmj-send mlmmj-receive mlmmj-process mlmmj-sub mlmmj-unsub \
            mlmmj-bounce mlmmj-maintd mlmmj-list \
            mlmmj-recieve mlmmj-make-ml mlmmj-make-ml.sh; do
    [ -x "$BIN_DIR/$tool" ] || missing="$missing $tool"
done
if [ -z "$missing" ]; then
    ok "all 11 commands installed and executable"
else
    bad "missing commands:$missing"
fi

echo "TEST SUMMARY: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
    exit 1
fi
exit 0
