#!/usr/bin/env bash
# test_package runtime test for medusa 2.3.
#
# Verifies, from a consumer's point of view, that the packaged binary really
# starts (which means OpenSSL initialised, its providers loaded, and the CLI
# linked correctly) and that it can dlopen() the service modules that the
# package ships.
#
# Usage: bash test_medusa.sh /path/to/pkg/bin/medusa
set -euo pipefail

BIN="${1:?usage: test_medusa.sh <path-to-medusa>}"
PKG_ROOT="$(cd "$(dirname "$BIN")/.." && pwd)"
MODULE_DIR="$PKG_ROOT/lib/medusa/modules"

# medusa aborts at startup unless OpenSSL can load BOTH the `default' and the
# `legacy' provider.  libcrypto is linked statically, so it dlopen()s the
# provider DSO from OPENSSL_MODULES.  The package ships its own copy of the
# provider (see the recipe's package()) and exports OPENSSL_MODULES for it;
# the Conan cache is searched as a fallback in case the run environment is not
# applied for some reason.
candidates="$PKG_ROOT/lib/ossl-modules"
if [ -z "${OPENSSL_MODULES:-}" ] || [ ! -f "${OPENSSL_MODULES}/legacy.so" ]; then
  : "${CONAN_HOME:=$HOME/.conan2}"
  candidates="$candidates $CONAN_HOME/p/opens*/p/lib/ossl-modules"
fi
for cand in $candidates; do
  if [ -f "$cand/legacy.so" ]; then
    if [ "${OPENSSL_MODULES:-}" != "$cand" ]; then
      echo "[info] using OpenSSL providers from $cand"
    fi
    export OPENSSL_MODULES="$cand"
    break
  fi
done
if [ -z "${OPENSSL_MODULES:-}" ] || [ ! -f "$OPENSSL_MODULES/legacy.so" ]; then
  echo "[fail] OpenSSL 'legacy' provider not found (OPENSSL_MODULES=${OPENSSL_MODULES:-<unset>})" >&2
  echo "[hint] medusa calls OSSL_PROVIDER_load(NULL, \"legacy\") at startup and" >&2
  echo "       exits with ERR_FATAL when it fails; openssl/3.0.21 ships" >&2
  echo "       lib/ossl-modules/legacy.so, openssl/3.5.6.x does not." >&2
  exit 1
fi

echo "== medusa test_package =="
echo "binary       : $BIN"
echo "package root : $PKG_ROOT"
echo "module dir   : $MODULE_DIR"
echo "MEDUSA_MODULE_PATH=${MEDUSA_MODULE_PATH:-<unset>}"
echo "OPENSSL_MODULES=${OPENSSL_MODULES:-<unset>}"
ls -l "$MODULE_DIR" 2>&1 | head -n 40 || true
for tool in readelf llvm-readobj nm llvm-nm; do
  if command -v "$tool" >/dev/null 2>&1; then
    echo "== dynamic section ($tool) =="
    "$tool" -d "$BIN" 2>&1 | head -n 30 || true
    echo "== dynamic symbols exported by the core ($tool) =="
    case "$tool" in
      readelf)     "$tool" --dyn-syms "$BIN" 2>/dev/null | grep -c ' EVP_' || true ;;
      llvm-readobj) "$tool" --dyn-symbols "$BIN" 2>/dev/null | grep -c 'EVP_' || true ;;
      nm|llvm-nm)  "$tool" -D "$BIN" 2>/dev/null | grep -c ' EVP_' || true ;;
    esac
    break
  fi
done
if [ -n "${OPENSSL_MODULES:-}" ]; then
  echo "providers:"
  ls -l "$OPENSSL_MODULES" 2>&1 | head -n 20 || true
fi

test -d "$MODULE_DIR"
ls "$MODULE_DIR"/*.mod >/dev/null 2>&1
echo "[ok] service modules are packaged"

# DEFAULT_MOD_PATH is compiled in as an absolute path that cannot point into
# the Conan package folder, so use the documented runtime override when the
# generated run environment did not provide it.
if [ -z "${MEDUSA_MODULE_PATH:-}" ]; then
  export MEDUSA_MODULE_PATH="$MODULE_DIR"
fi

# Unpredictable temporary files.  OHOS has no writable /tmp, so TMPDIR must be
# honoured; make the failure explicit rather than silently falling back.
: "${TMPDIR:=${HOME:-/tmp}/tmp}"
mkdir -p "$TMPDIR" 2>/dev/null || true
TMP_OUT="$(mktemp "${TMPDIR%/}/medusa-modules.XXXXXX")" || {
  echo "[fail] cannot create a temporary file in TMPDIR=$TMPDIR" >&2
  exit 1
}
TMP_NAMES="${TMP_OUT}.names"
trap 'rm -f "$TMP_OUT" "$TMP_NAMES"' EXIT

"$BIN" -d 2>&1 | tee "$TMP_OUT"

# `medusa -d' prints one `+ <name>.mod : <detail>' line per *.mod file it finds,
# and upstream src/listModules.c emits the SAME shape for the three outcomes:
#
#   success          "+ ftp.mod : Brute force module for FTP/FTPS sessions : ..."
#   dlopen() failure "+ ftp.mod : Couldn't load "<path>" [<dlerror>]"
#   dlsym() failure  "+ ftp.mod : Invalid module "<path>" [no export of ...]"
#
# so failure lines must be excluded explicitly; otherwise a build in which every
# module fails to load would still satisfy the counts below.  The two failure
# forms are the ones listModules.c actually prints.
sed -e "/Couldn't load/d" -e '/Invalid module/d' "$TMP_OUT" \
  | sed -n 's/^[[:space:]]*+[[:space:]]*\([A-Za-z0-9._-]*\)\.mod[[:space:]]*:[[:space:]]*[^[:space:]].*/\1/p' \
  | sort -u > "$TMP_NAMES"
LOADED="$(wc -l < "$TMP_NAMES" | tr -d '[:space:]')"
FAILED_MODS="$(grep -cE "Couldn't load|Invalid module" "$TMP_OUT" || true)"
echo "[info] modules dlopen'ed successfully: $LOADED"
if [ "${FAILED_MODS:-0}" -gt 0 ]; then
  echo "[warn] $FAILED_MODS module line(s) report a load failure:"
  grep -E "Couldn't load|Invalid module" "$TMP_OUT" | sed 's/^/       /' >&2 || true
fi
echo "[info] $(tr '\n' ' ' < "$TMP_NAMES")"

if [ "$LOADED" -lt 10 ]; then
  echo "[fail] medusa dlopen'ed only $LOADED modules, expected at least 10" >&2
  exit 1
fi

for mod in http ftp smtp telnet vnc; do
  if ! grep -qx "$mod" "$TMP_NAMES"; then
    echo "[fail] expected module '$mod' was not loaded" >&2
    exit 1
  fi
done
echo "[ok] core modules (http ftp smtp telnet vnc) loaded via dlopen"

# The SSH module is a strong end-to-end check: it needs libssh2 (and the
# thread-safe libgcrypt path) to be present at link and run time.
if [ "${MEDUSA_EXPECT_SSH:-1}" = "1" ]; then
  if ! grep -qx "ssh" "$TMP_NAMES"; then
    echo "[fail] ssh module missing - libssh2/libgcrypt integration failed" >&2
    exit 1
  fi
  echo "[ok] ssh module loaded (libssh2 + libgcrypt)"
fi

echo "ALL MEDUSA TESTS PASSED"
