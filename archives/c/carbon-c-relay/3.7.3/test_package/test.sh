#!/bin/sh
# carbon-c-relay consumer test — real behavior through the packaged binary.
# Usage: test.sh <relay-binary> <package-folder>
#
# OHOS 平台说明（知识 E054/E077/E374，blogc 0.20.1 同款先例）：
# 未签名 ELF 在 OHOS worker 上首次执行会触发安全确认对话框，headless 环境
# 无人应答导致静默挂死。因此先将打包产物拷贝到任务私有工作区并用
# binary-sign-tool 自签名后再执行；签名工具缺失时按 E374 语义如实输出
# NOT_RUN（保留编译链接证据，不虚报运行通过）。
set -e

BIN="$1"
PKG="$2"

if [ -z "$BIN" ] || [ -z "$PKG" ]; then
    echo "usage: test.sh <relay-binary> <package-folder>" >&2
    exit 2
fi

# WORK 固定在 $HOME/tmp（HMDFS）：CI worker 的 TMPDIR 指向应用沙箱
# （/data/storage/el2/base/cache），签名后的 ELF 在该挂载下无法执行
# （CI #41392 实测 Error 124）；HMDFS 临时目录已实测可执行（E354 同类先例）。
mkdir -p "${HOME}/tmp" 2>/dev/null || true
WORK="$(mktemp -d "${HOME}/tmp/ccrtest.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT

RUNBIN="$BIN"
SIGN_TOOL="$(command -v binary-sign-tool 2>/dev/null || true)"
if [ -z "$SIGN_TOOL" ]; then
    SIGN_TOOL="$(ls /system/bin/binary-sign-tool \
                     /data/service/hnp/bin/binary-sign-tool \
                     "$HOME/usr/local/bin/binary-sign-tool" 2>/dev/null | head -1 || true)"
fi

TOUT=""
if command -v timeout >/dev/null 2>&1; then
    TOUT="timeout 60"
fi

if [ -n "$SIGN_TOOL" ]; then
    cp "$BIN" "$WORK/relay.signed"
    echo "consumer-runtime: step1 copy done"
    if "$SIGN_TOOL" sign -inFile "$WORK/relay.signed" \
            -outFile "$WORK/relay.signed" -selfSign 1 >/dev/null 2>&1; then
        chmod a+x "$WORK/relay.signed" 2>/dev/null || true
        RUNBIN="$WORK/relay.signed"
        echo "consumer-runtime: step2 sign done"
    else
        # E374: signing tool present but failed — do NOT execute unsigned ELF
        # (would hang on the OHOS security dialog); report NOT_RUN truthfully.
        echo "consumer-runtime: NOT_RUN (signing failed; compile-link evidence retained)"
        echo "HMBS_TEST_PACKAGE_RESULT={\"runtime\": \"NOT_RUN_signing_failed\"}"
        exit 0
    fi
else
    # E374: no signing tool on this worker — runtime NOT_RUN, no execution.
    echo "consumer-runtime: NOT_RUN (binary-sign-tool unavailable on this worker)"
    echo "HMBS_TEST_PACKAGE_RESULT={\"runtime\": \"NOT_RUN_no_sign_tool\"}"
    exit 0
fi

# 1. version banner: upstream prints "carbon-c-relay v<version> (<date>)"
echo "consumer-runtime: step3 version banner"
$TOUT "$RUNBIN" -v > "$WORK/ver.txt" 2>&1 || {
    echo "consumer-runtime: FAIL (version banner step, rc=$?)"
    cat "$WORK/ver.txt" 2>/dev/null
    exit 1
}
grep -q "carbon-c-relay v3\.7\.3" "$WORK/ver.txt"

# 2. config validation (-tt: MODE_CONFIGTEST — parse config and exit):
#    valid config must pass (rc=0); a config with a syntax error must be
#    rejected (rc!=0). NOTE: single -t is MODE_TEST (starts listeners and
#    runs forever) — CI #41399 实证 worker 上 unix socket 可 bind 导致
#    -t 永不退出，故消费者测试必须用 -tt。
echo "consumer-runtime: step4 configtest (-tt)"
cat > "$WORK/relay.conf" <<EOF
cluster test
    forward 127.0.0.1:2103
    ;
match *
    send to test
    stop
    ;
EOF

$TOUT "$RUNBIN" -H test.hostname -tt -f "$WORK/relay.conf" > "$WORK/cfgout.txt" 2>&1 || {
    echo "consumer-runtime: FAIL (valid config rejected, rc=$?)"
    cat "$WORK/cfgout.txt" 2>/dev/null
    exit 1
}
echo "consumer-runtime: step5 invalid config rejected"
cat > "$WORK/bad.conf" <<EOF
cluster bad
    frobnicate 42
    ;
EOF
BADRC=0
$TOUT "$RUNBIN" -H test.hostname -tt -f "$WORK/bad.conf" > "$WORK/badout.txt" 2>&1 || BADRC=$?
if [ "$BADRC" -eq 0 ]; then
    echo "consumer-runtime: FAIL (invalid config accepted)"
    exit 1
fi
grep -q "failed to read configuration" "$WORK/badout.txt"

echo "HMBS_TEST_PACKAGE_RESULT={\"version_banner\": \"pass\", \"config_valid\": \"pass\", \"config_invalid_rejected\": \"pass\"}"
