#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer-side test for the zls executable on OHOS.
# Runs in conanrun env (PATH includes installed bin/).
#
# OHOS-specific assertions (beyond upstream's own `zig build test` run in
# build()):
#   A. The packaged, self-signed ELF is accepted by the OHOS kernel — every
#      executed ELF must carry a valid signature, so simply running `zls`
#      proves the package() signing step worked.
#   B. known-folders resolves the OHOS HOME layout (`zls env`).
#   C. The product is a self-contained static ELF — the pure-Zig adaptation
#      must not introduce a host .so closure (no DT_NEEDED entries).
#   D. A real LSP stdio session works on OHOS: initialize -> initialized ->
#      shutdown -> exit with JSON-RPC Content-Length framing.
set -u

echo "[test] locating zls binary"
ZLS_BIN="$(command -v zls || true)"
if [ -z "$ZLS_BIN" ]; then
    for CAND in "$(dirname "$0")"/../../p/*/bin/zls; do
        [ -x "$CAND" ] && ZLS_BIN="$CAND" && break
    done
fi
if [ -z "$ZLS_BIN" ]; then
    echo "FAIL: zls binary not found in PATH"
    exit 1
fi
echo "[ok] zls binary: $ZLS_BIN"

# ── A. version (execution itself proves OHOS code-signing is accepted) ──
echo "[test] zls --version"
VER="$("$ZLS_BIN" --version 2>/dev/null)"
RC=$?
if [ $RC -ne 0 ]; then
    echo "FAIL: zls --version exited $RC (kernel refused unsigned/invalid ELF?)"
    exit 1
fi
echo "[test] version output: $VER"
case "$VER" in
    0.15.1*|*0.15.1*)
        echo "[ok] version is 0.15.1"
        ;;
    *)
        echo "FAIL: expected version 0.15.1, got: $VER"
        exit 1
        ;;
esac

# ── B. known-folders path resolution under OHOS HOME ──
echo "[test] zls env (known-folders resolution on OHOS)"
ENV_OUT="$("$ZLS_BIN" env 2>/dev/null)"
RC=$?
if [ $RC -ne 0 ] || [ -z "$ENV_OUT" ]; then
    echo "FAIL: zls env exited $RC or produced no output"
    exit 1
fi
echo "$ENV_OUT" | sed 's/^/       /'
echo "$ENV_OUT" | grep -qi "config" || {
    echo "FAIL: zls env output missing config path"
    exit 1
}
echo "[ok] zls env resolved config path"

# ── C. static ELF (no host .so closure) ──
READELF=""
for CAND in llvm-readelf readelf \
            /storage/Users/currentUser/usr/local/bin/llvm-readelf \
            /data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/llvm-readelf; do
    if command -v "$CAND" >/dev/null 2>&1 || [ -x "$CAND" ]; then
        READELF="$CAND"
        break
    fi
done
if [ -n "$READELF" ]; then
    echo "[test] static ELF check via $READELF"
    NEEDED="$("$READELF" -d "$ZLS_BIN" 2>/dev/null | grep -c NEEDED || true)"
    ARCH="$("$READELF" -h "$ZLS_BIN" 2>/dev/null | grep -i 'machine:' || true)"
    echo "       $ARCH; DT_NEEDED entries: $NEEDED"
    case "$ARCH" in
        *AArch64*|*aarch64*)
            echo "[ok] aarch64 ELF"
            ;;
        *)
            echo "FAIL: unexpected ELF architecture: $ARCH"
            exit 1
            ;;
    esac
    if [ "${NEEDED:-0}" -ne 0 ]; then
        echo "FAIL: zls must be a static ELF on OHOS but has DT_NEEDED entries"
        exit 1
    fi
    echo "[ok] static ELF without host .so closure"
else
    echo "[warn] readelf not available; skipping static ELF check"
fi

# ── D. real LSP stdio session ──
echo "[test] LSP stdio initialize/shutdown/exit handshake"
TMPDIR_T="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR_T"
WORK="$TMPDIR_T/zls_test_pkg.$$"
mkdir -p "$WORK"
trap 'rm -rf "$WORK"' EXIT

REQ_INIT='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"processId":null,"rootUri":null,"rootPath":null,"capabilities":{},"clientInfo":{"name":"ohos-test-package"}}}'
REQ_INITIALIZED='{"jsonrpc":"2.0","method":"initialized","params":{}}'
REQ_SHUTDOWN='{"jsonrpc":"2.0","id":2,"method":"shutdown","params":null}'
REQ_EXIT='{"jsonrpc":"2.0","method":"exit"}'

: > "$WORK/requests.bin"
for BODY in "$REQ_INIT" "$REQ_INITIALIZED" "$REQ_SHUTDOWN" "$REQ_EXIT"; do
    printf 'Content-Length: %d\r\n\r\n%s' "${#BODY}" "$BODY" >> "$WORK/requests.bin"
done

TIMEOUT_CMD=""
command -v timeout >/dev/null 2>&1 && TIMEOUT_CMD="timeout 120"
# shellcheck disable=SC2086
$TIMEOUT_CMD "$ZLS_BIN" < "$WORK/requests.bin" > "$WORK/response.txt" 2>/dev/null
RC=$?
if [ $RC -ne 0 ]; then
    echo "FAIL: LSP session exited $RC (expected clean exit after exit notification)"
    exit 1
fi

INIT_RESP=0
grep -q '"id":1' "$WORK/response.txt" && grep -q '"capabilities"' "$WORK/response.txt" && INIT_RESP=1
if [ $INIT_RESP -ne 1 ]; then
    echo "FAIL: no initialize response with capabilities for id:1"
    head -c 800 "$WORK/response.txt" 2>/dev/null
    exit 1
fi
echo "[ok] initialize response contains capabilities"

SHUTDOWN_RESP=0
grep -q '"id":2' "$WORK/response.txt" && grep -q '"result":null' "$WORK/response.txt" && SHUTDOWN_RESP=1
if [ $SHUTDOWN_RESP -ne 1 ]; then
    echo "FAIL: no shutdown response (id:2, result:null)"
    head -c 800 "$WORK/response.txt" 2>/dev/null
    exit 1
fi
echo "[ok] shutdown acknowledged"

echo "[test] all checks passed (version/env/static-ELF/LSP handshake)"
