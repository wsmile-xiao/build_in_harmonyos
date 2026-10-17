#!/usr/bin/env bash
# kwartz_client_test.sh — kwartz-client 3.0 consumer smoke (OHOS adaptation
# points), 18 assertions in 6 groups.
#
# Runs under the bash/5.3 required by test_package/conanfile.py (the repo's
# published OHOS shell), with:
#   BASH_BIN  path to the bash/5.3 binary
#   PKG_ROOT  package folder of the tested kwartz-client/3.0
#
# Design notes:
# - Every assertion reads the tested package through PKG_ROOT only; nothing
#   is written outside the test's own working area, so this is safe to run
#   from the CI conan test stage (and it is what makes the CI L1e negative
#   test work: remove bin/ and groups B/C/E/F must fail).
# - Zero-ELF property is checked in pure bash (read -N 4), no od/dd/head
#   dependency, so the assertion set is self-contained.
# - Upstream has zero tests (NO_UPSTREAM_TESTS, see MANIFEST.yml /
#   EXCLUDED-TESTS.md / UPSTREAM-TESTS-EVIDENCE.json); these assertions
#   verify the adaptation itself — install-face fidelity, POSIX syntax under
#   a real shell, template-variable contract — and never claim "enrolment
#   works on OHOS" (known-unreachable function, disclosed in manifest).

set -u

BASH_BIN="${BASH_BIN:?BASH_BIN not set}"
PKG_ROOT="${PKG_ROOT:?PKG_ROOT not set}"

PASS=0
FAIL=0

ok() { PASS=$((PASS + 1)); echo "[ok]   $1"; }
bad() { FAIL=$((FAIL + 1)); echo "[FAIL] $1"; }

echo "== kwartz-client/3.0 test_package smoke (18 assertions) =="

# ── Group A: harness sanity ─────────────────────────────────────────────
# A1
if [ -x "$BASH_BIN" ]; then ok "A1 harness bash executable: $BASH_BIN"
else bad "A1 harness bash not executable: $BASH_BIN"; fi
# A2
if [ -d "$PKG_ROOT" ]; then ok "A2 package root present: $PKG_ROOT"
else bad "A2 package root missing: $PKG_ROOT"; fi

SCRIPT="$PKG_ROOT/bin/kwartz-cloud"
TPL="$PKG_ROOT/share/doc/kwartz-client/kwartz-install.tpl"

# ── Group B: pure POSIX shell package, zero ELF (OHOS adaptation) ───────
# B1
if [ -f "$SCRIPT" ] && [ -x "$SCRIPT" ]; then
    ok "B1 bin/kwartz-cloud present and executable"
else
    bad "B1 bin/kwartz-cloud missing or not executable: $SCRIPT"
fi
# B2: kwartz-cloud must NOT be an ELF (pure sh script; no signing needed)
magic=""
if [ -f "$SCRIPT" ]; then
    IFS= read -r -N 4 magic < "$SCRIPT" || true
fi
if [ "$magic" != "$(printf '\177ELF')" ]; then
    ok "B2 bin/kwartz-cloud is not an ELF artifact"
else
    bad "B2 bin/kwartz-cloud unexpectedly an ELF"
fi
# B3: whole package contains zero ELF files
elf_found=0
while IFS= read -r -d '' f; do
    m=""
    IFS= read -r -N 4 m < "$f" || true
    if [ "$m" = "$(printf '\177ELF')" ]; then
        elf_found=1
        echo "       ELF file found: $f"
    fi
done < <(find "$PKG_ROOT" -type f -print0)
if [ "$elf_found" -eq 0 ]; then ok "B3 zero ELF files in package tree"
else bad "B3 package tree contains ELF files"; fi

# ── Group C: syntax gates under the repo bash (real shell parse) ────────
# C1
if "$BASH_BIN" -n "$SCRIPT" 2>/dev/null; then
    ok "C1 bash -n parses bin/kwartz-cloud"
else
    bad "C1 bin/kwartz-cloud fails bash -n"
fi
# C2: the template is rendered into a root shell script by postinst; it must
# therefore already be syntactically valid shell before substitution.
if [ -f "$TPL" ] && "$BASH_BIN" -n "$TPL" 2>/dev/null; then
    ok "C2 bash -n parses share/doc/kwartz-client/kwartz-install.tpl"
else
    bad "C2 kwartz-install.tpl missing or fails bash -n"
fi
# C3: POSIX sh shebang — no /bin/bash dependency at runtime
shebang=""
if [ -f "$SCRIPT" ]; then
    IFS= read -r shebang < "$SCRIPT" || true
fi
case "$shebang" in
    "#! "*"/sh"| "#!"/sh| "#! "*"/sh"*) ok "C3 kwartz-cloud shebang is POSIX sh ($shebang)" ;;
    *) bad "C3 unexpected shebang: $shebang" ;;
esac

# ── Group D: install-face completeness (debian/kwartz-client.install) ───
# D1..D4
for pair in \
    "D1|$PKG_ROOT/share/icons/kwartz-cloud.svg" \
    "D2|$PKG_ROOT/share/applications/kwartz-cloud.desktop" \
    "D3|$PKG_ROOT/etc/kwartz-cloud.conf" \
    "D4|$PKG_ROOT/share/man/man1/kwartz-cloud.1"; do
    tag="${pair%%|*}"
    path="${pair#*|}"
    if [ -f "$path" ]; then ok "$tag present: ${path#"$PKG_ROOT"/}"
    else bad "$tag missing: ${path#"$PKG_ROOT"/}"; fi
done
# D5: license face (full phrase as printed by debian/copyright)
if [ -f "$PKG_ROOT/licenses/copyright" ] \
    && grep -q "GNU General Public License" "$PKG_ROOT/licenses/copyright"; then
    ok "D5 licenses/copyright present with GPL notice"
else
    bad "D5 licenses/copyright missing or without GPL notice"
fi

# ── Group E: byte fidelity vs pinned upstream (E241 pattern) ────────────
# E1
sha_actual=""
[ -f "$SCRIPT" ] && sha_actual="$(sha256sum "$SCRIPT" 2>/dev/null | cut -d' ' -f1)"
if [ "$sha_actual" = "eb6a383d1986ab4185e44178ba690946f1c552246bb922cb0edca5b6480d7da2" ]; then
    ok "E1 bin/kwartz-cloud sha256 matches pinned upstream"
else
    bad "E1 bin/kwartz-cloud sha256 mismatch: $sha_actual"
fi
# E2
sha_actual=""
[ -f "$TPL" ] && sha_actual="$(sha256sum "$TPL" 2>/dev/null | cut -d' ' -f1)"
if [ "$sha_actual" = "5fc6f8e7581290a531291195d751a680ecf71c46db05f3f6c52b26af310fb8c9" ]; then
    ok "E2 kwartz-install.tpl sha256 matches pinned upstream"
else
    bad "E2 kwartz-install.tpl sha256 mismatch: $sha_actual"
fi

# ── Group F: data-flow contracts ────────────────────────────────────────
# F1: the template must reference the 8 envsubst variables that postinst
#     exports from debconf (landing_page is postinst-only by upstream design).
tpl_vars_missing=0
for v in ip_proxy port_proxy proxy_gnome_noproxy proghalt \
         unattended_upgrades login_apt mdp_apt nom_kwartz; do
    if ! grep -qF -e "$v" "$TPL"; then
        tpl_vars_missing=1
        echo "       template misses debconf variable: $v"
    fi
done
if [ "$tpl_vars_missing" -eq 0 ]; then
    ok "F1 template references all 8 debconf envsubst variables"
else
    bad "F1 template misses debconf variables"
fi
# F2: script ↔ packaged config contract
if grep -q "/etc/kwartz-cloud.conf" "$SCRIPT"; then
    ok "F2 kwartz-cloud sources /etc/kwartz-cloud.conf (packaged in etc/)"
else
    bad "F2 kwartz-cloud does not reference /etc/kwartz-cloud.conf"
fi
# F3: desktop ↔ bin launch chain
if grep -q "^Exec=kwartz-cloud" "$PKG_ROOT/share/applications/kwartz-cloud.desktop"; then
    ok "F3 desktop entry Exec points at installed kwartz-cloud"
else
    bad "F3 desktop entry Exec mismatch"
fi

echo "== result: PASS=$PASS FAIL=$FAIL =="
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
exit 0
