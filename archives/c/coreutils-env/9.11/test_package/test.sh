#!/data/service/hnp/bin/bash
# test_package/test.sh — HarmonyOS 专项 smoke test for env binary
# Runs in conanrun env (PATH includes installed bin/)
set -eu

ENV_BIN="$(command -v env)"
echo "[test] env binary at: $ENV_BIN"

echo "[test] env --version"
"$ENV_BIN" --version | head -1 | grep -q "coreutils" && echo "✅ env --version OK" || {
    echo "[test] env --version failed"
    exit 1
}

echo "[test] env -i 清空环境并注入变量 (HarmonyOS 专项)"
OUT="$("$ENV_BIN" -i FOO=bar /bin/sh -c 'echo FOO=$FOO')"
[ "$OUT" = "FOO=bar" ] && echo "✅ env -i FOO=bar OK" || {
    echo "[test] env -i 失败, got: $OUT"
    exit 1
}

echo "[test] env 继承现有环境变量 (HarmonyOS 专项)"
export OHPCD_ENV_TEST=hello
OUT2="$("$ENV_BIN" /bin/sh -c 'echo OHPCD_ENV_TEST=$OHPCD_ENV_TEST')"
[ "$OUT2" = "OHPCD_ENV_TEST=hello" ] && echo "✅ env 继承环境 OK" || {
    echo "[test] env 继承失败, got: $OUT2"
    exit 1
}

echo "[test] env -u 删除变量 (HarmonyOS 专项)"
export OHPCD_ENV_TEST=hello
OUT3="$("$ENV_BIN" -u OHPCD_ENV_TEST /bin/sh -c 'if [ -z "${OHPCD_ENV_TEST+x}" ]; then echo UNSET; else echo SET; fi')"
[ "$OUT3" = "UNSET" ] && echo "✅ env -u 删除变量 OK" || {
    echo "[test] env -u 失败, got: $OUT3"
    exit 1
}

echo "[test] env -C 切换目录后执行 (HarmonyOS 专项)"
OUT4="$("$ENV_BIN" -C / /bin/sh -c 'pwd')"
[ "$OUT4" = "/" ] && echo "✅ env -C 切换目录 OK" || {
    echo "[test] env -C 失败, got: $OUT4"
    exit 1
}

echo "[test] env 无参数输出完整环境"
"$ENV_BIN" | grep -q "PATH=" && echo "✅ env 无参数输出环境 OK" || {
    echo "[test] env 无参数失败"
    exit 1
}

echo "All env tests passed ✅"
