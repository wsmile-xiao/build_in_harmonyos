#!/bin/sh
# test_package/test_twclock.sh — consumer test for twclock 3.5 (R34 / L0c).
# Usage: sh test_twclock.sh <bin_dir> [<llvm-readelf>]
# Executes the packaged binary directly; asserts the ELF DT_NEEDED
# Motif/X11/PulseAudio chain, the TRANSITIVE runtime closure of that chain,
# the app-defaults resource file, and headless behaviour.  Never hangs
# (timeout => FAIL).
#
# A loader failure is only reported as NOT VERIFIED (SKIP) when the transitive
# runtime closure is provably complete; an incomplete closure is a packaging
# defect and fails.  See the (c) block for the full rationale.
set -u

BIN_DIR="${1:-}"
READELF="${2:-}"
[ -n "$READELF" ] || READELF="/data/service/hnp/bin/llvm-readelf"
if [ ! -x "$READELF" ]; then
    READELF="$(command -v llvm-readelf || command -v readelf || true)"
fi

A=0
F=0
S=0
pass() { A=$((A + 1)); echo "PASS: $1"; }
fail() { A=$((A + 1)); F=$((F + 1)); echo "FAIL: $1"; }
# skip() marks a check that this host genuinely cannot execute.  It is NOT an
# assertion: it is reported separately so an environment limitation can never
# be counted as evidence (and can never inflate assertion_count).
skip() { S=$((S + 1)); echo "SKIP: $1"; }

echo "=== twclock 3.5 consumer test ==="
echo "bin_dir=$BIN_DIR"
echo "readelf=$READELF"

if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin dir not found: '${BIN_DIR}'"
    echo "assertions=1 failures=1"
    exit 1
fi

BIN="${BIN_DIR}/twclock"

# (a) bin/twclock exists and is executable
if [ -x "$BIN" ]; then
    pass "bin/twclock exists and is executable"
else
    fail "bin/twclock missing or not executable at ${BIN}"
fi

# (b) ELF DT_NEEDED evidence: the packaged Motif/X11/PulseAudio chain is linked
if [ -x "$READELF" ]; then
    DYN="$("$READELF" -d "$BIN" 2>&1)"
    echo "--- captured: ${READELF} -d ... (NEEDED/SONAME lines) ---"
    printf '%s\n' "$DYN" | grep -E "NEEDED|SONAME" || true
    echo "--- end ---"
    for lib in libXm.so.4 libXt.so.6 libX11.so.6 libpulse-simple.so.0 libpulse.so.0; do
        if printf '%s\n' "$DYN" | grep -q "NEEDED.*${lib}"; then
            pass "ELF DT_NEEDED ${lib}"
        else
            fail "ELF DT_NEEDED ${lib} missing"
        fi
    done
else
    fail "no usable llvm-readelf/readelf found (got '${READELF}')"
fi

# (e-pre) Transitive runtime closure of the packaged binary.
#
# (b) only proves the 5 DIRECT DT_NEEDED sonames are linked; (e) below only
# proved those same 5 are resolvable.  Neither can tell apart
#   (i)  this package failed to ship a resolvable dependency  -> real defect,
#   (ii) the platform loader refused an otherwise complete set  -> worker/OS
#        condition, nothing this recipe can fix.
# The discriminator is the FULL transitive closure: start from every DT_NEEDED
# of bin/twclock and follow DT_NEEDED transitively, resolving each one against
# the conanrun-injected LD_LIBRARY_PATH.  No execution is involved, so this is
# real evidence on any host architecture.
#
# System libraries provided by the OHOS loader itself (libc/libm/libgcc_s/
# libstdc++/loaders) are excluded: they are not package payload.
CLOSURE_MISSING=""
CLOSURE_SEEN=" "
CLOSURE_RESOLVED=""
closure_resolve() {
    # echo the first LD_LIBRARY_PATH entry holding $1, else empty
    for d in $(printf '%s' "${LD_LIBRARY_PATH:-}" | tr ':' ' '); do
        if [ -e "$d/$1" ]; then
            printf '%s' "$d/$1"
            return 0
        fi
    done
    return 0
}
closure_is_system() {
    case "$1" in
        libc.so|libc.so.*|libm.so*|libgcc_s.so*|libstdc++.so*|ld-musl-*|ld-linux-*|libpthread.so*) return 0 ;;
    esac
    return 1
}
if [ -x "$READELF" ]; then
    echo "--- transitive runtime closure: DT_NEEDED walk from ${BIN} ---"
    TODO=""
    for n in $(printf '%s\n' "$DYN" | grep '(NEEDED)' | sed 's/.*\[//; s/\].*//'); do
        closure_is_system "$n" || TODO="$TODO $n"
    done
    # Level-order expansion: everything discovered in one round is processed in
    # the next, and CLOSURE_SEEN guarantees each library is expanded at most
    # once, so dependency cycles terminate.
    while [ -n "$TODO" ]; do
        NEXT=""
        for CUR in $TODO; do
            case "$CLOSURE_SEEN" in
                *" $CUR "*) continue ;;
            esac
            CLOSURE_SEEN="$CLOSURE_SEEN$CUR "
            R="$(closure_resolve "$CUR")"
            if [ -z "$R" ]; then
                echo "    MISSING $CUR (no LD_LIBRARY_PATH entry provides it)"
                CLOSURE_MISSING="$CLOSURE_MISSING $CUR"
                continue
            fi
            echo "    OK      $CUR -> $R"
            CLOSURE_RESOLVED="$CLOSURE_RESOLVED $CUR"
            for n in $("$READELF" -d "$R" 2>/dev/null | grep '(NEEDED)' | sed 's/.*\[//; s/\].*//'); do
                closure_is_system "$n" && continue
                case "$CLOSURE_SEEN" in
                    *" $n "*) continue ;;
                esac
                NEXT="$NEXT $n"
            done
        done
        TODO="$NEXT"
    done
    echo "    resolved:$(printf '%s' "$CLOSURE_RESOLVED" | wc -w | tr -d ' ') library/libraries"
    echo "--- end transitive runtime closure ---"
else
    echo "    (skipped: no usable readelf)"
fi

# (c) headless init: DISPLAY unset.  When the binary can actually be started we
#     assert the real upstream behaviour (Xt/display error, never hangs).
#     When it CANNOT be started, the behaviour is *unverified* — and whether
#     that is our fault or the platform's is decided by the transitive runtime
#     closure computed above (CLOSURE_MISSING):
#       * closure INCOMPLETE -> FAIL: the package really did fail to ship a
#         resolvable dependency, a real delivery defect (R34/交付物不完整).
#       * closure COMPLETE   -> SKIP (NOT VERIFIED): every library the binary
#         needs, transitively, is present and resolvable from the consumer
#         environment, so the loader failure is a platform/worker condition
#         outside this package (see notes.md "加载器条件的判据").
#
#     Evidence that this is a worker condition, not a packaging defect: CI
#     #63039 FAILED on worker OpenHarmonyPCDeveloper-CI-036 while #63074 PASSED
#     on worker OpenHarmonyPCDeveloper-CI-005 for the *same* SHA 5270206912.
#
#     The earlier revision of this script mapped `Error relocating` to PASS,
#     which is why CI #62849 was green while the headless behaviour had in fact
#     never been exercised.  The revision after that downgraded *every* loader
#     failure to SKIP, which threw away a real assertion that demonstrably
#     passes on a healthy worker.  The closure check above restores that
#     discrimination.
HL_RC=0
HL_OUT=""
HL_NATIVE=0
HL_ATTEMPTED=0
if [ -x "$BIN" ]; then
    HOST_ARCH="$(uname -m)"
    case "$HOST_ARCH" in
        aarch64|arm64) HL_NATIVE=1 ;;
    esac
    if [ "$HL_NATIVE" -eq 1 ]; then
        HL_ATTEMPTED=1
        HL_OUT="$(unset DISPLAY; timeout 30 "$BIN" 2>&1)"
        HL_RC=$?
    else
        QEMU_BIN="$(command -v qemu-aarch64 || true)"
        if [ -z "$QEMU_BIN" ]; then
            skip "headless run NOT VERIFIED: foreign-arch host ${HOST_ARCH}, qemu-aarch64 not installed"
        elif [ -z "${QEMU_LD_PREFIX:-}" ] || [ ! -d "${QEMU_LD_PREFIX:-}" ]; then
            skip "headless run NOT VERIFIED: set QEMU_LD_PREFIX to a real OHOS sysroot to execute the aarch64 binary on ${HOST_ARCH}"
        else
            echo "--- using qemu-aarch64 with QEMU_LD_PREFIX=${QEMU_LD_PREFIX} ---"
            HL_ATTEMPTED=1
            HL_OUT="$(unset DISPLAY; timeout 30 "$QEMU_BIN" -L "$QEMU_LD_PREFIX" "$BIN" 2>&1)"
            HL_RC=$?
        fi
    fi
else
    skip "headless run NOT VERIFIED: binary not executable, already reported as FAIL in (a)"
fi
echo "--- captured: headless twclock (DISPLAY unset, timeout 30) exit=${HL_RC} native=${HL_NATIVE} attempted=${HL_ATTEMPTED} ---"
echo "$HL_OUT"
echo "--- end ---"
if [ "$HL_ATTEMPTED" -eq 1 ]; then
    UNLOADABLE=""
    if printf '%s\n' "$HL_OUT" | grep -qE "Error relocating|symbol not found|cannot open shared object|error while loading shared libraries|Error loading shared library"; then
        UNLOADABLE="$(printf '%s\n' "$HL_OUT" | grep -oE 'Error loading shared library [^:]+' | head -3 | tr '\n' ' ')"
        [ -n "$UNLOADABLE" ] || UNLOADABLE="dynamic loader could not resolve DT_NEEDED libs"
    fi
    if [ "$HL_RC" -eq 124 ]; then
        fail "headless twclock hung (timeout 30 exceeded)"
    elif [ -n "$UNLOADABLE" ]; then
        if [ -n "$CLOSURE_MISSING" ]; then
            # The package really did not deliver a resolvable dependency: a
            # genuine delivery defect, not a platform condition.  Fail.
            fail "headless twclock: packaged runtime closure is INCOMPLETE${CLOSURE_MISSING} -- loader failure is a packaging defect, not a platform condition"
        else
            skip "headless run NOT VERIFIED: loader could not start the binary although the transitive runtime closure is COMPLETE (${UNLOADABLE}) -- platform/worker condition, see notes.md"
        fi
    elif printf '%s\n' "$HL_OUT" | grep -q "Can't open display"; then
        pass "headless twclock printed upstream display error and exited (${HL_RC})"
    elif [ "$HL_RC" -ne 0 ] && printf '%s\n' "$HL_OUT" | grep -qiE "display|Xt[ _]?(Error|Warning)|cannot open"; then
        pass "headless twclock: non-zero exit (${HL_RC}) with Xt/display error"
    elif [ "$HL_RC" -eq 0 ]; then
        pass "headless twclock: started and exited 0 without a display error"
    else
        fail "headless twclock: unexpected exit=${HL_RC} output='${HL_OUT}'"
    fi
fi

# (d) packaged payload: app-defaults resource, man page, desktop entry, icon
PAYLOAD_DIR="$(dirname "$BIN_DIR")"
for rel in "share/X11/app-defaults/Twclock" "share/man/man1/twclock.1" "share/applications/twclock.desktop" "share/pixmaps/twclock.png"; do
    if [ -f "$PAYLOAD_DIR/$rel" ]; then
        pass "packaged payload present: $rel"
    else
        fail "packaged payload missing: $rel"
    fi
done

# (e) packaged runtime closure: the TRANSITIVE closure computed before (c)
#     must be fully resolvable from the conanrun LD_LIBRARY_PATH that the
#     recipe's dependencies inject.  This runs on ANY host (no execution), so it
#     is real evidence on the x86_64 dev box as well as on the aarch64 CI
#     worker.  Each resolved path is echoed above so the result is auditable.
#
# NON-VACUITY GUARD.  "nothing was found missing" is trivially true when
# "nothing was looked at": if DT_NEEDED yields no parseable, non-system entry
# (unreadable binary, readelf failure, or a binary whose whole dependency set
# is filtered as system), the walk above terminates with an empty CLOSURE_MISSING
# and the assertion below used to report PASS while having examined ZERO
# libraries.  Reproduced on the MR head with a real ELF with no dynamic section:
#   resolved:0 library/libraries  ->  "PASS: runtime closure: ... resolvable"
#                                    TRANSITIVE_CLOSURE=complete
# So the claim must also be backed by positive evidence: the walk must have
# resolved at least one library AND must have resolved all 5 DIRECT sonames
# that (b) asserts.  Empty walk => FAIL, not PASS.
DIRECT_SONAMES="libXm.so.4 libXt.so.6 libX11.so.6 libpulse-simple.so.0 libpulse.so.0"
CLOSURE_RESOLVED_COUNT="$(printf '%s' "$CLOSURE_RESOLVED" | wc -w | tr -d ' ')"
if [ -x "$READELF" ]; then
    if [ -z "$CLOSURE_MISSING" ]; then
        NOT_COVERED=""
        for lib in $DIRECT_SONAMES; do
            case " $CLOSURE_RESOLVED " in
                *" $lib "*) ;;
                *) NOT_COVERED="$NOT_COVERED $lib" ;;
            esac
        done
        if [ "$CLOSURE_RESOLVED_COUNT" -eq 0 ]; then
            fail "runtime closure: VACUOUS -- DT_NEEDED walk resolved 0 libraries, so 'nothing missing' proves nothing (bin/twclock exposes no non-system DT_NEEDED entry)"
        elif [ -n "$NOT_COVERED" ]; then
            fail "runtime closure: DT_NEEDED walk resolved ${CLOSURE_RESOLVED_COUNT} libraries but did NOT resolve the direct sonames asserted by (b):${NOT_COVERED}"
        else
            pass "runtime closure: transitive Motif/X11/PulseAudio closure resolvable from LD_LIBRARY_PATH (${CLOSURE_RESOLVED_COUNT} libraries, 5/5 direct sonames covered)"
        fi
    else
        fail "runtime closure: transitive libs not resolvable from LD_LIBRARY_PATH:${CLOSURE_MISSING}"
    fi
else
    fail "runtime closure: no usable readelf to derive DT_NEEDED"
fi

echo "assertions=${A} failures=${F} skipped=${S}"
# The summary verdict must agree with the (e) assertion: a walk that examined
# nothing is NOT a complete closure, it is an absence of evidence.
if [ -n "$CLOSURE_MISSING" ]; then
    echo "TRANSITIVE_CLOSURE=incomplete${CLOSURE_MISSING}"
elif [ "${CLOSURE_RESOLVED_COUNT:-0}" -eq 0 ]; then
    echo "TRANSITIVE_CLOSURE=vacuous (0 libraries examined -- no evidence, not a pass)"
else
    echo "TRANSITIVE_CLOSURE=complete (${CLOSURE_RESOLVED_COUNT} libraries)"
fi
if [ "$S" -gt 0 ]; then
    echo "NOTE: ${S} check(s) were NOT VERIFIED in this environment (see SKIP lines above);"
    echo "      they are not counted as passing assertions."
fi
[ "$F" -eq 0 ] || exit 1
exit 0
