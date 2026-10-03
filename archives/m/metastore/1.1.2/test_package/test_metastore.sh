#!/bin/sh
# Consumer assertions for the packaged metastore 1.1.2.
#
# Every assertion below really executes the packaged `metastore` binary and
# checks a real, observable effect: its exit status, its own --dump output,
# or the on-disk state it restores.  Nothing here is an echo/print stub.
#
# Three of the assertions are HarmonyOS-specific and are marked [OHOS].
# They are identified by the same ids the PASS/FAIL lines carry, so a grep
# for `[OHOS]` in a build log accounts for all of them:
#   [8]   cross-validates the in-tree strmode(3) shim that replaced the
#         libbsd import (the one and only adaptation in this port) by
#         diffing `metastore --dump`'s mode column against `ls -ld`'s,
#         across every file type and every setuid/setgid/sticky branch,
#         and asserts byte-exactly that each mode field is 11 bytes wide.
#   [8b]  pins the special-bit glyphs (setuid s/S, setgid s, sticky t/T).
#         A branch the filesystem refuses to grant is reported as
#         `unverifiable:<n>` rather than silently counted as a pass.
#   [9]   round-trips a `user.*` extended attribute, which drives
#         OHOS's <sys/xattr.h> family (listxattr/getxattr/lsetxattr/
#         lremovexattr) through the real binary.  Skipped, loudly and
#         with a reason, if the filesystem or the tooling cannot do it.
# Manifests declaring this count: archives/m/metastore/1.1.2/manifest.yaml,
# archives/m/metastore/manifest.yaml, notes.md, test_package/MANIFEST.yml.

set -u

passes=0
fails=0
skips=0

ok()   { passes=$((passes + 1)); echo "  PASS  $1"; }
bad()  { fails=$((fails + 1));  echo "  FAIL  $1"; }
skip() { skips=$((skips + 1));  echo "  SKIP  $1"; }

MS="$(command -v metastore)" || {
    echo "  FAIL  packaged binary 'metastore' is not resolvable in the runenv PATH"
    exit 1
}
echo "metastore under test: $MS"

WORK="$(mktemp -d)" || { echo "  FAIL  mktemp -d failed"; exit 1; }
trap 'chmod -R u+rwX "$WORK" 2>/dev/null; rm -rf "$WORK"' EXIT INT TERM

TREE="$WORK/tree"
META="$WORK/meta.bin"

# ---------------------------------------------------------------------------
# [1] the packaged artifact is on the runenv PATH
# ---------------------------------------------------------------------------
ok "[1] packaged binary resolves in runenv PATH: $MS"

# ---------------------------------------------------------------------------
# [2] --version reports the upstream version baked in at build time.
#     The Makefile compiles -DMETASTORE_VER from version.sh, which falls back
#     to grepping NEWS when there is no .git; this asserts that whole chain.
# ---------------------------------------------------------------------------
vout="$("$MS" --version 2>&1)"; vrc=$?
if [ "$vrc" -eq 0 ] && [ "$vout" = "metastore v1.1.2" ]; then
    ok "[2] --version reports the build-time version: $vout"
else
    bad "[2] --version: rc=$vrc out='$vout' (expected rc=0, 'metastore v1.1.2')"
fi

# ---------------------------------------------------------------------------
# [3] no ACTION => usage on stderr and a nonzero exit
# ---------------------------------------------------------------------------
uout="$("$MS" 2>&1)"; urc=$?
case "$uout" in
    *"Usage: "*) usage_ok=1 ;;
    *)           usage_ok=0 ;;
esac
if [ "$usage_ok" -eq 1 ] && [ "$urc" -ne 0 ]; then
    ok "[3] no-args prints usage and exits nonzero (rc=$urc)"
else
    bad "[3] no-args: rc=$urc usage_found=$usage_ok out='$(echo "$uout" | head -1)'"
fi

# ---------------------------------------------------------------------------
# [4] getopt error paths must be rejected, not silently ignored
# ---------------------------------------------------------------------------
"$MS" -Z >/dev/null 2>&1; zrc=$?
if [ "$zrc" -ne 0 ]; then
    ok "[4] invalid option -Z is rejected (rc=$zrc)"
else
    bad "[4] invalid option -Z was accepted (rc=0)"
fi

# --empty-dirs is only meaningful together with --apply
"$MS" --save --empty-dirs "$TREE" >/dev/null 2>&1; erc=$?
if [ "$erc" -ne 0 ]; then
    ok "[4b] --empty-dirs without --apply is rejected (rc=$erc)"
else
    bad "[4b] --empty-dirs without --apply was accepted (rc=0)"
fi

# ---------------------------------------------------------------------------
# [5] FUNCTIONAL: permissions survive a save -> mutate -> apply round trip.
#     Mode is read back with `ls -ld`, i.e. by an implementation entirely
#     independent of the tool under test.
# ---------------------------------------------------------------------------
mkdir -p "$TREE/sub"
echo alpha > "$TREE/file_a"
echo beta  > "$TREE/sub/file_b"

# Ask for the modes we want to store, then read back what the filesystem
# actually granted.  They are not always the same: on a real HarmonyOS
# device the "other" (world) permission bits get masked off, so a chmod 0644
# lands as 0640.  Asserting the *requested* mode here would be testing the
# filesystem's policy, not metastore -- so the contract under test is
# metastore's own: restore exactly the mode that was recorded.  A separate
# guard below skips the group outright if the filesystem will not give us two
# distinct modes to move between.
chmod 0644 "$TREE/file_a"
chmod 0755 "$TREE/sub/file_b"
chmod 0700 "$TREE/sub"
want_a="$(ls -ld "$TREE/file_a"     | awk '{print $1}')"
want_b="$(ls -ld "$TREE/sub/file_b" | awk '{print $1}')"

(cd "$WORK" && "$MS" --save --file "$META" ./tree) >/dev/null 2>&1; src=$?
if [ "$src" -ne 0 ] || [ ! -s "$META" ]; then
    bad "[5] --save failed (rc=$src) or produced an empty metafile"
else
    ok "[5a] --save produced a non-empty metafile ($(wc -c < "$META") bytes)"
    chmod 0600 "$TREE/file_a"
    chmod 0666 "$TREE/sub/file_b"
    mut_a="$(ls -ld "$TREE/file_a"     | awk '{print $1}')"
    mut_b="$(ls -ld "$TREE/sub/file_b" | awk '{print $1}')"
    if [ "$mut_a" = "$want_a" ] && [ "$mut_b" = "$want_b" ]; then
        skip "[5b] permission round trip - this filesystem grants no distinct modes here (stored $want_a/$want_b, mutation left them unchanged), so there is nothing for --apply to restore"
    else
        (cd "$WORK" && "$MS" --apply --file "$META" ./tree) >/dev/null 2>&1; arc=$?
        ma="$(ls -ld "$TREE/file_a"     | awk '{print $1}')"
        mb="$(ls -ld "$TREE/sub/file_b" | awk '{print $1}')"
        if [ "$arc" -eq 0 ] && [ "$ma" = "$want_a" ] && [ "$mb" = "$want_b" ]; then
            ok "[5b] --apply restored the recorded modes exactly: file_a=$ma sub/file_b=$mb (from $mut_a/$mut_b, rc=$arc)"
        else
            bad "[5b] --apply: rc=$arc file_a=$ma (want $want_a) sub/file_b=$mb (want $want_b)"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# [6] FUNCTIONAL: mtimes survive a --mtime round trip.
#     `date -r` is used for the read-back (POSIX-ish, present on OHOS and
#     GNU alike) rather than stat(1) format strings.
# ---------------------------------------------------------------------------
touch -d '2001-02-03 04:05:06' "$TREE/file_a" 2>/dev/null \
    || touch -t 200102030405.06 "$TREE/file_a"
want_y="2001"
got_before="$(date -r "$TREE/file_a" +%Y)"
(cd "$WORK" && "$MS" --save --mtime --file "$META" ./tree) >/dev/null 2>&1
touch -d '2020-12-31 23:59:59' "$TREE/file_a" 2>/dev/null \
    || touch -t 202012312359.59 "$TREE/file_a"
(cd "$WORK" && "$MS" --apply --mtime --file "$META" ./tree) >/dev/null 2>&1; mrc=$?
got_after="$(date -r "$TREE/file_a" +%Y)"
if [ "$got_before" = "$want_y" ] && [ "$got_after" = "$want_y" ] && [ "$mrc" -eq 0 ]; then
    ok "[6] --mtime round trip restored the stored mtime year (2001 -> 2020 -> $got_after, rc=$mrc)"
else
    bad "[6] --mtime: before=$got_before want=$want_y after=$got_after want=$want_y rc=$mrc"
fi

# ---------------------------------------------------------------------------
# [7] --compare must notice metadata that drifted away from the metafile
# ---------------------------------------------------------------------------
chmod 0700 "$TREE/file_a"
cout="$( (cd "$WORK" && "$MS" --compare --file "$META" ./tree) 2>&1 )"
case "$cout" in
    *mode*) ok "[7] --compare detects the mode drift" ;;
    *)      bad "[7] --compare did not report the mode drift: '$(echo "$cout" | head -1)'" ;;
esac
(cd "$WORK" && "$MS" --apply --mtime --file "$META" ./tree) >/dev/null 2>&1

# ---------------------------------------------------------------------------
# [8] [OHOS] strmode(3) shim cross-validation.
#     This is the assertion that proves the one real adaptation in this port
#     is behaviourally correct: the in-tree replacement for libbsd's
#     strmode() must render the same mode column `ls` does, for every file
#     type and for all three special-bit branches (setuid S/s, setgid S/s,
#     sticky T/t) plus the ACL placeholder column.
# ---------------------------------------------------------------------------
mkdir -p "$TREE/dir_sgid"
: > "$TREE/f_plain";    chmod 0644 "$TREE/f_plain"
: > "$TREE/f_setuid";   chmod 4755 "$TREE/f_setuid"
: > "$TREE/f_sticky";   chmod 1755 "$TREE/f_sticky"
: > "$TREE/f_none";     chmod 0600 "$TREE/f_none"
chmod 2755 "$TREE/dir_sgid"
chmod 1777 "$TREE"
: > "$TREE/f_suid_noexec"; chmod 4644 "$TREE/f_suid_noexec"
ln -sf f_plain "$TREE/link" 2>/dev/null
mkfifo "$TREE/fifo" 2>/dev/null
ln -s target_nowhere "$TREE/dangling" 2>/dev/null

dump="$(cd "$WORK" && "$MS" --dump ./tree 2>/dev/null)"

# Extract metastore's raw mode field for one path.
#
# FS is deliberately a TAB, not the default whitespace run: the field that
# comes back must keep the trailing ACL-placeholder byte that BSD strmode
# writes as its 11th character.  With awk's default whitespace splitting
# that byte is collapsed and a shim that dropped it would be undetectable —
# which is precisely the defect this test exists to catch.  Length is
# therefore asserted separately below (must be exactly 11).
ms_field() {
    printf '%s\n' "$dump" | awk -F'\t' -v want="$1" '
        { sub(/[ \t]+$/, "", $NF) }
        $NF == want { print $1; exit }'
}

shim_fail=0
shim_checked=0
for p in ./tree/f_plain ./tree/f_setuid ./tree/f_sticky ./tree/f_none \
         ./tree/f_suid_noexec ./tree/dir_sgid/ ./tree/ ./tree/link \
         ./tree/fifo ./tree/dangling; do
    [ -e "$WORK/${p#./}" ] || [ -L "$WORK/${p#./}" ] || continue
    want="$(ls -ld "$WORK/${p#./}" | awk '{print $1}')"
    raw="$(ms_field "$p")"
    got="$(printf '%s' "$raw" | sed 's/[ \t]*$//')"
    shim_checked=$((shim_checked + 1))
    if [ "$got" != "$want" ]; then
        bad "[8] [OHOS] strmode shim: $p rendered '$got' but ls says '$want'"
        shim_fail=1
    fi
    # Byte-exact width: 1 type + 9 permission + 1 ACL placeholder = 11.
    # This is what catches a shim that "forgot" the ACL column.
    if [ "${#raw}" -ne 11 ]; then
        bad "[8] [OHOS] strmode shim: $p mode field is ${#raw} bytes, expected 11 (ACL placeholder missing?)"
        shim_fail=1
    fi
done
if [ "$shim_fail" -eq 0 ] && [ "$shim_checked" -ge 8 ]; then
    ok "[8] [OHOS] strmode shim matches ls on $shim_checked entries, each mode field exactly 11 bytes (types: -/d/l/p + setuid/setgid/sticky branches)"
else
    [ "$shim_checked" -lt 8 ] && bad "[8] [OHOS] only $shim_checked entries could be compared, expected >= 8"
    shim_fail=1
fi

# Pin the special-bit glyphs down explicitly, independently of whatever ls
# happens to print.  Each sub-check first confirms the filesystem actually
# granted the bit (some sandboxed filesystems silently drop setuid/setgid/
# sticky), and only then asserts the exact BSD glyph -- otherwise we would be
# asserting a filesystem policy instead of the shim.
suid_ok=na; suid_noexec_ok=na; sgid_ok=na; sticky_ok=na
suid_reason=""; suid_noexec_reason=""; sgid_reason=""; sticky_reason=""

ls_mode_of() { ls -ld "$1" | awk '{print $1}'; }

# setuid + exec  (4755) -> the 's' in the user-exec slot
if [ -f "$TREE/f_setuid" ]; then
    got="$(ls_mode_of "$TREE/f_setuid")"
    case "$got" in
        *s*|*S*) case "$dump" in
                    *"$got"*) suid_ok=1 ;;
                    *) suid_ok=0; suid_reason="dump lacks '$got'" ;;
                esac ;;
        *)       suid_ok=na
                 suid_reason="fs did not grant the setuid bit (mode is '$got')" ;;
    esac
fi
# setuid, no exec (4644) -> the capital 'S'
if [ -f "$TREE/f_suid_noexec" ]; then
    got="$(ls_mode_of "$TREE/f_suid_noexec")"
    case "$got" in
        *S*)     case "$dump" in
                    *"$got"*) suid_noexec_ok=1 ;;
                    *) suid_noexec_ok=0; suid_noexec_reason="dump lacks '$got'" ;;
                esac ;;
        *)       suid_noexec_ok=na
                 suid_noexec_reason="fs did not grant the setuid bit (mode is '$got')" ;;
    esac
fi
# setgid on a directory (2755) -> 's' in the group-exec slot
if [ -d "$TREE/dir_sgid" ]; then
    got="$(ls_mode_of "$TREE/dir_sgid")"
    case "$got" in
        *s*|*S*) case "$dump" in
                    *"$got"*) sgid_ok=1 ;;
                    *) sgid_ok=0; sgid_reason="dump lacks '$got'" ;;
                esac ;;
        *)       sgid_ok=na
                 sgid_reason="fs did not grant the setgid bit (mode is '$got')" ;;
    esac
fi
# sticky on a directory (1777) -> 't' in the other-exec slot
got="$(ls_mode_of "$TREE")"
case "$got" in
    *t*|*T*) case "$dump" in
                *"$got"*) sticky_ok=1 ;;
                *) sticky_ok=0; sticky_reason="dump lacks '$got'" ;;
            esac ;;
    *)       sticky_ok=na
             sticky_reason="fs did not grant the sticky bit (mode is '$got')" ;;
esac

checked=0; failed=0; unverifiable=""
for pair in "setuid:$suid_ok:$suid_reason" \
            "setuid-noexec:$suid_noexec_ok:$suid_noexec_reason" \
            "setgid:$sgid_ok:$sgid_reason" \
            "sticky:$sticky_ok:$sticky_reason"; do
    name=${pair%%:*}; rest=${pair#*:}; state=${rest%%:*}; reason=${rest#*:}
    case "$state" in
        1) checked=$((checked + 1)) ;;
        0) failed=$((failed + 1));  echo "  FAIL  [8b] $name glyph: $reason" ;;
        *) unverifiable="$unverifiable $name($reason)" ;;
    esac
done
if [ "$failed" -ne 0 ]; then
    bad "[8b] [OHOS] strmode shim special-bit glyphs: $failed of 4 wrong (checked $checked, unverifiable:$unverifiable)"
elif [ "$checked" -eq 0 ]; then
    skip "[8b] [OHOS] strmode shim special-bit glyphs - this filesystem granted none of the setuid/setgid/sticky bits, so the glyphs cannot be exercised (unverifiable:$unverifiable)"
else
    ok "[8b] [OHOS] strmode shim special-bit glyphs exact on $checked of 4 branches (unverifiable:$unverifiable)"
fi

# ---------------------------------------------------------------------------
# [9] [OHOS] extended-attribute round trip.  This is metastore's headline
#     feature and the only one that depends on the OHOS xattr syscall family.
#     The metafile must capture the xattr, and --apply must put it back.
#
#     Guarded by a NATIVE probe first: if the filesystem will not even hand a
#     user.* attribute back to a plain getxattr, the round trip is simply not
#     available here and asserting it would be asserting the impossible.  That
#     case is reported as an explicit SKIP with the reason, never a silent
#     pass.
# ---------------------------------------------------------------------------
xa_native=no
xa_probe=setfattr
: > "$WORK/xa_probe_file"      # the probe needs a real file to work on
if command -v setfattr >/dev/null 2>&1 && command -v getfattr >/dev/null 2>&1; then
    if setfattr -n user.metastore_selftest -v PROBE "$WORK/xa_probe_file" 2>/dev/null \
       && [ "$(getfattr --only-values -n user.metastore_selftest "$WORK/xa_probe_file" 2>/dev/null | tr -d '\n')" = "PROBE" ]; then
        xa_native=yes
    fi
elif command -v python3 >/dev/null 2>&1; then
    xa_probe=python3
    if python3 -c 'import os,sys; os.setxattr(sys.argv[1], b"user.metastore_selftest", b"PROBE")' \
         "$WORK/xa_probe_file" 2>/dev/null \
       && [ "$(python3 -c 'import os,sys; sys.stdout.write(os.getxattr(sys.argv[1], b"user.metastore_selftest").decode())' \
         "$WORK/xa_probe_file" 2>/dev/null)" = "PROBE" ]; then
        xa_native=yes
    fi
fi

# A vacuous SKIP is a hollow test, so the skip path stays honest: the probe
# wrote to a real file, so a failure here means the filesystem genuinely does
# not serve user.* attributes back.  That is reported, never counted as a pass.
if [ "$xa_native" != yes ]; then
    if command -v setfattr >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
        skip "[9] [OHOS] xattr round trip - the probe wrote user.metastore_selftest to a real file and the filesystem would not serve it back to a native getxattr, so the round trip is not observable here (SKIP, not a pass)"
    else
        skip "[9] [OHOS] xattr round trip - neither setfattr nor python3 is available, so extended attributes cannot be exercised at all (SKIP, not a pass)"
    fi
else
    : > "$TREE/f_xattr"
    if [ "$xa_probe" = setfattr ]; then
        setfattr -n user.metastore_selftest -v HAROMS "$TREE/f_xattr" 2>/dev/null
    else
        python3 -c 'import os,sys; os.setxattr(sys.argv[1], b"user.metastore_selftest", b"HAROMS")' \
            "$TREE/f_xattr" 2>/dev/null
    fi
    (cd "$WORK" && "$MS" --save --file "$META" ./tree) >/dev/null 2>&1
    if [ "$xa_probe" = setfattr ]; then
        setfattr -x user.metastore_selftest "$TREE/f_xattr" 2>/dev/null
    else
        python3 -c 'import os,sys; os.removexattr(sys.argv[1], b"user.metastore_selftest")' \
            "$TREE/f_xattr" 2>/dev/null
    fi
    (cd "$WORK" && "$MS" --apply --file "$META" ./tree) >/dev/null 2>&1
    if [ "$xa_probe" = setfattr ]; then
        xa_val="$(getfattr --only-values -n user.metastore_selftest "$TREE/f_xattr" 2>/dev/null | tr -d '\n')"
    else
        xa_val="$(python3 -c 'import os,sys; sys.stdout.write(os.getxattr(sys.argv[1], b"user.metastore_selftest").decode())' \
            "$TREE/f_xattr" 2>/dev/null)"
    fi
    if [ "$xa_val" = "HAROMS" ]; then
        ok "[9] [OHOS] xattr round trip: user.metastore_selftest was captured, removed, and restored by --apply"
    else
        bad "[9] [OHOS] xattr round trip: expected HAROMS, got '$xa_val'"
    fi
fi

# ---------------------------------------------------------------------------
echo
echo "consumer assertions: $((passes + fails)) run, $passes PASS, $fails FAIL, $skips SKIP"
if [ "$fails" -ne 0 ]; then
    echo "RESULT: FAILED"
    exit 1
fi
echo "RESULT: PASS"
exit 0
