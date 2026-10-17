#!/bin/sh
# kerberos-configs 2.7 consumer test script (POSIX sh)
# Usage: sh test_kerberos_configs.sh <package_folder>
#
# Substantive checks (R34, non-stub) for a pure config package:
#   1. krb5.conf.template installed under share/kerberos-configs/
#      (mirrors debian/krb5-config.install payload)
#   2. krb5.conf syntax sanity: required INI sections present
#      ([libdefaults] / [realms] / [domain_realm])
#   3. Realm blocks balanced: '{' count == '}' count
#   4. default_realm assignment present in [libdefaults]
#   5. Known realm markers present (ATHENA.MIT.EDU, stanford.edu)
#   6. Helper + docs shipped: krb5confparse.pl, README, packaging-guidelines
#
# Only POSIX sh builtins + grep/wc are used (adduser #17506 lesson: never
# invoke python3/perl on OHOS CI workers; plain shell is the most robust).

set -eu

pkg="$1"
fail=0

share="$pkg/share/kerberos-configs"
template="$share/krb5.conf.template"

echo "[INFO] package folder: $pkg"

check_file() {
    if [ -f "$share/$1" ]; then
        echo "[OK] artifact present: $1"
    else
        echo "[FAIL] missing artifact: $1"
        fail=1
    fi
}

# 1. payload presence
check_file krb5.conf.template
check_file krb5confparse.pl
check_file README
check_file packaging-guidelines

# 2. required krb5.conf sections
for section in libdefaults realms domain_realm; do
    if grep -qE "^\s*\[$section\]" "$template"; then
        echo "[OK] section [$section] present"
    else
        echo "[FAIL] section [$section] missing"
        fail=1
    fi
done

# 3. balanced realm braces (10 '{' vs 10 '}' in upstream 2.7 template)
open_braces=$(grep -o '{' "$template" | wc -l)
close_braces=$(grep -o '}' "$template" | wc -l)
if [ "$open_braces" -eq "$close_braces" ] && [ "$open_braces" -gt 0 ]; then
    echo "[OK] realm braces balanced: $open_braces/$close_braces"
else
    echo "[FAIL] realm braces unbalanced: $open_braces open vs $close_braces close"
    fail=1
fi

# 4. default_realm assignment in [libdefaults]
if grep -qE '^[^#;]*default_realm\s*=' "$template"; then
    echo "[OK] default_realm assignment present"
else
    echo "[FAIL] default_realm assignment missing"
    fail=1
fi

# 5. known realm markers (upstream 2.7 template content integrity)
for marker in 'ATHENA.MIT.EDU' 'stanford.edu' 'kerberos.mit.edu'; do
    if grep -qF "$marker" "$template"; then
        echo "[OK] content marker present: $marker"
    else
        echo "[FAIL] content marker missing: $marker"
        fail=1
    fi
done

# 6. template non-trivial size (upstream 84 lines / ~3 KB)
lines=$(wc -l < "$template")
if [ "$lines" -ge 80 ]; then
    echo "[OK] template size sane: $lines lines"
else
    echo "[FAIL] template unexpectedly small: $lines lines"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[FAIL] kerberos-configs test failed"
    exit 1
fi
echo "[PASS] kerberos-configs 2.7 artifacts verified (krb5.conf template well-formed)"
