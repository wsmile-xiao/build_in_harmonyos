#!/usr/bin/env bash
# acf-tinydns 0.11.1 test_package smoke test
#
# Verifies the installed ACF app module files:
#   1. tinydns*.lua controllers/model are present and syntactically valid Lua
#   2. tinydns*.lsp html templates are present
#   3. tinydns.roles and tinydns.menu are present
#   4. dangling symlinks (tinydns-editfile-html.lsp → ../filedetails-html.lsp)
#      are preserved via -L (matching upstream cp -a semantics)
#
# Exit code: 0 = all checks pass, non-zero = failure
set -euo pipefail

PKG_FOLDER="${1:?usage: test_tinydns.sh <package-folder>}"
APPDIR="${PKG_FOLDER}/share/acf/app/tinydns"

echo "=== acf-tinydns 0.11.1 smoke test ==="
echo "APPDIR=${APPDIR}"

# ── Check 1: app directory exists ──────────────────────────────────
if [ ! -d "${APPDIR}" ]; then
    echo "FAIL: ACF app directory missing: ${APPDIR}"
    exit 1
fi
echo "PASS: ACF app directory exists"

# ── Check 2: tinydns*.lua controllers/model present and valid Lua ──
lua_files_found=0
for f in "${APPDIR}"/tinydns*.lua; do
    [ -e "$f" ] || continue
    lua_files_found=$((lua_files_found + 1))
    # Syntax check: luac -p (parse only, no execution)
    if command -v luac >/dev/null 2>&1; then
        if luac -p "$f" 2>/dev/null; then
            echo "PASS: $(basename "$f") is valid Lua"
        else
            echo "FAIL: $(basename "$f") has Lua syntax errors"
            exit 1
        fi
    else
        # No luac available; verify file is non-empty and readable
        if [ -s "$f" ]; then
            echo "PASS: $(basename "$f") is non-empty (luac unavailable)"
        else
            echo "FAIL: $(basename "$f") is empty"
            exit 1
        fi
    fi
done
if [ "${lua_files_found}" -eq 0 ]; then
    echo "FAIL: no tinydns*.lua files found"
    exit 1
fi
echo "PASS: ${lua_files_found} tinydns*.lua files found"

# ── Check 3: tinydns.menu present ──────────────────────────────────
if [ -f "${APPDIR}/tinydns.menu" ]; then
    echo "PASS: tinydns.menu present"
else
    echo "FAIL: tinydns.menu missing"
    exit 1
fi

# ── Check 4: tinydns.roles present ─────────────────────────────────
if [ -f "${APPDIR}/tinydns.roles" ]; then
    echo "PASS: tinydns.roles present"
else
    echo "FAIL: tinydns.roles missing"
    exit 1
fi

# ── Check 5: *.lsp html templates present (including symlinks) ─────
lsp_files_found=0
# Use -L to follow symlinks; upstream cp -a preserves them
for f in "${APPDIR}"/tinydns*.lsp; do
    [ -e "$f" ] || [ -L "$f" ] || continue
    lsp_files_found=$((lsp_files_found + 1))
    echo "PASS: $(basename "$f") template present"
done
if [ "${lsp_files_found}" -eq 0 ]; then
    echo "FAIL: no tinydns*.lsp template files found"
    exit 1
fi
echo "PASS: ${lsp_files_found} tinydns*.lsp template files found"

# ── Check 6: no stray non-tinydns files in appdir ──────────────────
stray_count=0
for f in "${APPDIR}"/*; do
    [ -e "$f" ] || [ -L "$f" ] || continue
    case "$(basename "$f")" in
        tinydns*) ;;  # OK
        *) stray_count=$((stray_count + 1)); echo "WARN: stray file: $(basename "$f")" ;;
    esac
done
if [ "${stray_count}" -gt 0 ]; then
    echo "WARN: ${stray_count} stray files found (non-fatal)"
fi

echo ""
echo "=== All smoke tests PASSED ==="
exit 0
