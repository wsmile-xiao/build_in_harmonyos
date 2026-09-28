#!/bin/sh
# test_package consumer test for rephrase 0.2 (HarmonyOS PC / OHOS aarch64, musl).
#
# Upstream ships no test harness at all, so these are self-authored consumer
# assertions: the installed `rephrase` binary is invoked from PATH the way a
# real user invokes it, and every scenario is decided by its exit code plus
# observable stderr.
#
# Why all five paths are deterministic on a headless OHOS box: main() runs
#   banner -> mlock(2) -> setreuid -> setregid -> arg parse -> stat(command)
# and only AFTER that calls read_pattern(), the single place where /dev/tty is
# opened.  So none of the five assertions needs a controlling terminal or the
# gpg / cryptsetup helper binaries.
#
# T1  bare invocation   -> exit 7.  mlock(2) failure would exit 2 instead, so a
#                         7 also proves the gate is cleared by a 0755 non-setuid
#                         install (upstream insists on binmode 4711).
# T2  version banner    -> "rephrase (Rephrase) 0.2" proves the mandatory
#                         -DVERSION from the Makefile DEFS reached the ELF.
# T3  usage line        -> byte-identical to the compiled-in profiles[] table.
# T4  --luks <arg>      -> exit 4 naming /sbin/cryptsetup, i.e. the baked
#                         CRYPTSETUP default plus the stat() guard.
# T5  --bogus <arg>     -> exit 7, argc==3 with an unknown profile option.
set -u

BIN=rephrase
MIN="${1:-5}"
PASS=0
FAIL=0
ok() { printf '[PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
no() { printf '[FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }

if [ -x /usr/bin/timeout ]; then TMO="/usr/bin/timeout 30"; else TMO=""; fi

if ! command -v "$BIN" >/dev/null 2>&1; then
  printf '[FAIL] %s is not on PATH (conanrun env not applied?)\n' "$BIN"
  exit 1
fi

# ---- T1 / T2 / T3 : bare invocation -------------------------------------
out1=$($TMO $BIN 2>&1)
rc1=$?
if [ "$rc1" = "7" ]; then
  ok "T1 bare invocation exits 7 (usage path reached; mlock(2) passed without setuid)"
else
  no "T1 bare invocation expected exit 7, got exit $rc1 -- output: $out1"
fi

if printf '%s\n' "$out1" | grep -qF 'rephrase (Rephrase) 0.2'; then
  ok "T2 banner carries version 0.2 (upstream Makefile DEFS -DVERSION is baked in)"
else
  no "T2 banner has no version string -- output: $out1"
fi

USAGE='Usage: rephrase <key> | --gpg-key <key> | --gpg-symmetric <encrypted_file> | --luks <block_device>'
if printf '%s\n' "$out1" | grep -qF "$USAGE"; then
  ok "T3 usage line matches the compiled-in profiles[] table"
else
  no "T3 usage line mismatch -- output: $out1"
fi

# ---- T4 : baked CRYPTSETUP path is stat()ed before any tty is touched ----
out4=$($TMO $BIN --luks /nonexistent-luks-device 2>&1)
rc4=$?
if [ "$rc4" = "4" ] && printf '%s\n' "$out4" | grep -qF '/sbin/cryptsetup'; then
  ok "T4 --luks exits 4 naming /sbin/cryptsetup (baked path + stat() guard)"
else
  no "T4 --luks expected exit 4 naming /sbin/cryptsetup, got exit $rc4 -- output: $out4"
fi

# ---- T5 : unknown profile option falls through to the usage branch -------
out5=$($TMO $BIN --bogus-profile argument 2>&1)
rc5=$?
if [ "$rc5" = "7" ]; then
  ok "T5 unknown profile option exits 7 (argument parser rejects it)"
else
  no "T5 --bogus-profile expected exit 7, got exit $rc5 -- output: $out5"
fi

printf -- '---\n[PASS] counted=%d required=%s failed=%d\n' "$PASS" "$MIN" "$FAIL"
if [ "$FAIL" != "0" ] || [ "$PASS" -lt "$MIN" ]; then
  printf 'rephrase 0.2 consumer test: NOT SATISFACTORY (pass=%d min=%s fail=%d)\n' "$PASS" "$MIN" "$FAIL"
  exit 1
fi
printf 'rephrase 0.2 consumer test: %d/%s assertions PASS\n' "$PASS" "$MIN"
exit 0
