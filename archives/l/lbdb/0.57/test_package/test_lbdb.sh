#!/bin/sh
# lbdb/0.57 consumer selftest -- runs under toybox /bin/sh (ash).
#
# It deliberately does NOT use /bin/bash or /usr/bin/perl (both absent on
# HarmonyOS PC) and does not rely on any FHS interpreter path, so a green run is
# also proof that the E049 shebang normalisation in conanfile.package() produced
# installed scripts that start on this platform.
#
# Static assertion sites (the PR body may not declare more executed tests than
# this list, and the SUMMARY line below must match the w3 log):
#   A1  lbdbq present on PATH
#   A2  lbdb-fetchaddr present on PATH
#   A3  lbdbq --version banner runs under /bin/sh
#   A4  lbdb-fetchaddr -v banner runs under /bin/sh
#   A5  nodelist2lbdb resolves its Perl interpreter (E049)
#   A6  mutt_ldap_query resolves its Perl interpreter (E049)
#   A7  installed bin/libexec contain no machine-bound interpreter shebang (E049)
#   A8  at least 8 installed scripts were scanned (A7 is not vacuous)
#   A9  lbdb-fetchaddr -> lbdbq round trip returns the stored address
#       (drives the compiled fetchaddr + lbdb_dotlock helpers and the awk munge/tac)
#   A10 destructive: lbdbq for a bogus pattern reports "no matches" (R34 real query)
# Total sites = 10.

# Fail on unset vars and non-zero pipelines, but every deliberate rc-capture
# below is written as `rc=0; cmd || rc=$?` so -e does not abort before it runs.
set -euo pipefail

checks=0
failures=0
ok()  { checks=$((checks + 1)); echo "ok $checks - $1"; }
bad() { checks=$((checks + 1)); failures=$((failures + 1)); echo "NOT OK $checks - $1"; }

scratch=$(pwd)/lbdb-selftest.$$
mkdir -p "$scratch" || { echo "cannot create $scratch"; exit 70; }
cd "$scratch" || exit 70

# /tmp is read-only on HarmonyOS (E002): lbdbq builds its working dir from
# ${TMPDIR-/tmp}.  Point TMPDIR and HOME into the scratch tree.
export TMPDIR="$scratch"
export HOME="$scratch"
unset XDG_CONFIG_HOME XDG_DATA_HOME

# --------------------------------------------------------- A1/A2: tools ------
for t in lbdbq lbdb-fetchaddr; do
    if command -v "$t" >/dev/null 2>&1; then
        ok "packaged command '$t' resolves on PATH"
    else
        bad "packaged command '$t' missing from PATH"
    fi
done

# ------------------------------------------------- A3/A4: version banners ----
rc=0; lbdbq --version > vq.out 2>&1 || rc=$?
if [ "$rc" -ne 127 ] && grep -q '^lbdbq version 0.57' vq.out; then
    ok "lbdbq --version runs under the platform /bin/sh: $(tr '\n' ' ' < vq.out)"
else
    bad "lbdbq --version failed rc=$rc: $(tr '\n' ' ' < vq.out)"
fi

rc=0; lbdb-fetchaddr -v > vf.out 2>&1 || rc=$?
if [ "$rc" -ne 127 ] && grep -q 'lbdb-fetchaddr version' vf.out; then
    ok "lbdb-fetchaddr -v runs under the platform /bin/sh"
else
    bad "lbdb-fetchaddr -v failed rc=$rc: $(tr '\n' ' ' < vf.out)"
fi

# --------------------- A5/A6: delivered perl scripts resolve interpreter -----
# Running with stdin closed; a missing interpreter yields rc=127 plus a kernel
# "No such file or directory", which is exactly what the shebang fix must avoid.
# An absent CPAN module (e.g. Net::LDAP for m_ldap) dies later with a different
# code -- that is a runtime-optional dependency, not a broken interpreter.
for perltool in nodelist2lbdb mutt_ldap_query; do
    rc=0; "$perltool" --help </dev/null > "$perltool.out" 2>&1 || rc=$?
    if [ "$rc" -ne 127 ] && ! grep -qi 'No such file or directory' "$perltool.out"; then
        ok "$perltool resolves its Perl interpreter after the shebang fix (rc=$rc)"
    else
        bad "$perltool still points at a missing interpreter (rc=$rc): $(tr '\n' ' ' < "$perltool.out")"
    fi
done

# --------------- A7/A8: no machine-bound shebang left in installed scripts ---
bindir=$(dirname "$(command -v lbdbq)")
libexecdir=$(dirname "$bindir")/libexec
offenders=0
inspected=0
offender_list=""
for d in "$bindir" "$libexecdir"; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
        [ -f "$f" ] || continue
        # Only scripts carry a shebang; grep the ASCII #! line instead of head so
        # the compiled ELF helpers (fetchaddr/qpto8bit/lbdb_dotlock) are skipped
        # without emitting binary bytes.
        line=$(grep -m1 -a '^#!' "$f" 2>/dev/null || true)
        case "$line" in
            '#!'*)
                inspected=$((inspected + 1))
                case "$line" in
                    */storage/Users/*|*/data/service/*|*/.harmonybrew/*|*/usr/local/*|/usr/bin/perl*|*bash*)
                        offenders=$((offenders + 1))
                        offender_list="$offender_list $f"
                        ;;
                esac
                ;;
        esac
    done
done
if [ "$offenders" -eq 0 ]; then
    ok "every installed #! line is platform-resolvable (no machine-bound interpreter)"
else
    bad "machine-bound shebangs remain in:$offender_list"
fi
if [ "$inspected" -ge 8 ]; then
    ok "scanned $inspected installed scripts (shebang check is meaningful)"
else
    bad "only $inspected installed scripts scanned, shebang check inconclusive"
fi

# ---------------------- A9: fetch-address -> query round trip ----------------
# The db lives directly in $scratch via `lbdb-fetchaddr -f`: lbdb-fetchaddr's own
# default path ($HOME/.local/share/lbdb) needs a nested `mkdir -p`, and on HMDFS
# chmod is ignored so the intermediate `.local`/`.local/share` land without the
# +x owner bit and the descent fails with "Permission denied" (measured).  A file
# inside the already-created, traversable scratch dir sidesteps that; INMAIL_DB is
# honoured by m_inmail (M_INMAIL_DB=${INMAIL_DB:-fallbackdb}) so lbdbq reads the
# very file lbdb-fetchaddr wrote.  This still drives the compiled fetchaddr +
# lbdb_dotlock helpers and the awk munge/tac post-processing.
db="$scratch/m_inmail.db"
rc=0
printf 'From: Joe Bloggs <joe@example.com>\nSubject: lbdb selftest\n\nhello\n' \
    | lbdb-fetchaddr -a -f "$db" > fa.out 2>&1 || rc=$?
if INMAIL_DB="$db" lbdbq 'joe' > q.out 2>&1 && grep -qi 'joe@example.com' q.out; then
    ok "lbdb-fetchaddr -> lbdbq round trip returns the stored address: $(tr '\n' ' ' < q.out)"
else
    bad "round trip failed (fetchaddr rc=$rc): $(tr '\n' ' ' < fa.out) / $(tr '\n' ' ' < q.out)"
fi

# ------------------- A10: destructive no-match control (R34) -----------------
rc=0; lbdbq 'zzzNoSuchPersonZzz' > none.out 2>&1 || rc=$?
if [ "$rc" -ne 0 ] && grep -qi 'no matches' none.out; then
    ok "destructive check: lbdbq exits non-zero with 'no matches' for a bogus query"
else
    bad "destructive check inconclusive (rc=$rc): $(tr '\n' ' ' < none.out)"
fi

# ------------------------------------------------------------- summary -------
# Leave no scratch behind: this helper runs inside test_package/ (build_folder ==
# recipe_folder), so an un-removed lbdb-selftest.$$ would show up as an untracked
# stray under archives/.  cd out first, then drop it.
cd .. || true
rm -rf "$scratch"

total=$checks
failed=$failures
passed=$((total - failed))
echo "SUMMARY lbdb consumer: total=$total passed=$passed failed=$failed"
[ "$failures" -eq 0 ] || exit 1
exit 0
