#!/data/service/hnp/bin/bash
# test_package/test_dehydrated_tools_extra.sh — real smoke test for
# dehydrated-tools-extra 20260506 on the packaged artifact.
#
# Pure shell tool package: the scripts do NOT support --version/--help and
# executing them has side effects (dehydrated-cron calls dehydrated and
# writes to /var/log). So we verify structure instead:
#   1. all 10 scripts installed (bin/ + share/dehydrated/hooks/) and executable
#   2. shebang rewritten to the OHOS bash (/data/service/hnp/bin/bash)
#   3. bash -n syntax check passes for every script
#   4. cron.d/logrotate.d configs and rst docs installed
set -u

BIN_DIR="${1:?usage: test_dehydrated_tools_extra.sh <package bin dir> <package root>}"
PKG_ROOT="${2:?usage: test_dehydrated_tools_extra.sh <package bin dir> <package root>}"
OHOS_BASH="/data/service/hnp/bin/bash"

FAIL=0

check_script() {
    local f="$1"
    if [ ! -f "$f" ]; then
        echo "FAIL: $f missing"
        FAIL=1
        return
    fi
    if [ ! -x "$f" ]; then
        echo "FAIL: $f not executable"
        FAIL=1
    fi
    local shebang
    shebang=$(head -1 "$f")
    if [ "$shebang" != "#!${OHOS_BASH}" ]; then
        echo "FAIL: $f unexpected shebang: $shebang"
        FAIL=1
    fi
    if ! "$OHOS_BASH" -n "$f"; then
        echo "FAIL: $f bash syntax check failed"
        FAIL=1
    fi
}

for s in dehydrated-cron dehydrated-hook dehydrated-nsupdate; do
    check_script "$BIN_DIR/$s"
done

HOOKS_DIR="$PKG_ROOT/share/dehydrated/hooks"
for s in deploy_cert.chrony deploy_cert.extra deploy_cert.hostname \
         deploy_ocsp.extra exit_hook.extra-cleanup \
         exit_hook.fix-permissions exit_hook.service-reload; do
    check_script "$HOOKS_DIR/$s"
done

for c in etc/cron.d/dehydrated etc/logrotate.d/dehydrated; do
    if [ ! -f "$PKG_ROOT/$c" ]; then
        echo "FAIL: $c missing"
        FAIL=1
    fi
done

DOC_DIR="$PKG_ROOT/share/doc/dehydrated-tools-extra"
for d in LICENSE.txt CHANGELOG.txt dehydrated-cron.1.rst dehydrated-hook.1.rst dehydrated-nsupdate.1.rst; do
    if [ ! -f "$DOC_DIR/$d" ]; then
        echo "FAIL: doc $d missing"
        FAIL=1
    fi
done

if [ "$FAIL" -eq 0 ]; then
    echo "dehydrated-tools-extra smoke test: OK"
fi
exit "$FAIL"
