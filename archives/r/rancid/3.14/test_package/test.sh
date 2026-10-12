#!/data/service/hnp/bin/bash
# test_package/test.sh — rancid 3.14 消费者冒烟测试（在 conanrun env 下运行，
# 由 test_package/conanfile.py 调用）。
#
# rancid 是自包含 prefix 的 CLI/脚本工具集合，没有可链接的库 API，因此按
# "真实调用方式" 验证打包产物：
#   (A) C 助手 hpuifilter（无参数）→ 打印用法 + 退出码 64 (EX_USAGE)
#   (B) C 助手 par（-h）        → 退出码 64 (EX_USAGE)
#   (C) perl 模块 rancid.pm 已安装且 perl -c 语法校验通过
#   (D) use rancid 模块可加载（"rancid module loaded OK"）—— 证明 perl 脚本
#       依赖的模块在包内齐全
#   (E) perl 主脚本 bin/rancid 已安装且 perl -c 语法校验通过
#
# 用法: bash test.sh <package_root>
# 参数 $1 = 被测包安装根目录（conan 传 self.dependencies["rancid"].package_folder）
set -u

PKG="$1"
if [ -z "$PKG" ] || [ ! -d "$PKG/bin" ]; then
    echo "FAIL: package root not provided/invalid: '$PKG'"
    exit 2
fi
LIBDIR="$PKG/lib/rancid"

# 计数器（确定性来源：每次实际执行累计）
pass=0
fail=0
passname=""

# 全局退出码：任一断言失败即最终失败，但所有断言都执行完再汇总
# 失败时会立即打印 RANCID_TEST_* 汇总，随后 exit 1。

# ---------- 辅助：一次断言 ----------
# 参数: $1=名称  $2=期望退出码 其余=命令（将运行 "$@"，捕获退出码）
run_case() {
    local name="$1" want="$2"; shift 2
    "$@" >/dev/null 2>&1
    local got=$?
    if [ "$got" -eq "$want" ]; then
        pass=$((pass+1))
        passname="${passname} ${name}"
        echo "[PASS] $name (exit=$got)"
    else
        fail=$((fail+1))
        echo "[FAIL] $name (want exit=$want, got=$got)"
    fi
}

# ---------- 收集断言（每项对应一个用例） ----------

# (A) hpuifilter 存在且 no-args 返回 EX_USAGE(64)
if [ -x "$PKG/bin/hpuifilter" ]; then
    run_case "hpuifilter UX on no-args" 64 "$PKG/bin/hpuifilter"
else
    echo "[FAIL] hpuifilter binary missing: $PKG/bin/hpuifilter"; fail=$((fail+1))
fi

# (B) par 存在且 -h 返回 EX_USAGE(64)
if [ -x "$PKG/bin/par" ]; then
    run_case "par UX on -h" 64 "$PKG/bin/par" -h
else
    echo "[FAIL] par binary missing: $PKG/bin/par"; fail=$((fail+1))
fi

# (C) perl 模块 rancid.pm 已安装且语法有效
if [ -f "$LIBDIR/rancid.pm" ]; then
    if perl -I"$LIBDIR" -c "$LIBDIR/rancid.pm" >/dev/null 2>&1; then
        pass=$((pass+1)); passname="${passname} rancid.pm-syntax"; echo "[PASS] rancid.pm syntax"
    else
        fail=$((fail+1)); echo "[FAIL] rancid.pm perl -c syntax"
    fi
else
    echo "[FAIL] rancid.pm module missing: $LIBDIR/rancid.pm"; fail=$((fail+1))
fi

# (D) use rancid 模块可加载（真实 perl 引用路径）
if out=$(perl -I"$LIBDIR" -e 'use rancid; print "rancid module loaded OK\n"' 2>&1); then
    if printf '%s' "$out" | grep -q "rancid module loaded OK"; then
        pass=$((pass+1)); passname="${passname} rancid-load"; echo "[PASS] rancid module load"
    else
        fail=$((fail+1)); echo "[FAIL] rancid module load (unexpected output)"
    fi
else
    fail=$((fail+1)); echo "[FAIL] rancid module load: $out"
fi

# (E) perl 主脚本 bin/rancid 已安装且语法有效
if [ -f "$PKG/bin/rancid" ]; then
    if perl -I"$LIBDIR" -c "$PKG/bin/rancid" >/dev/null 2>&1; then
        pass=$((pass+1)); passname="${passname} rancid-script-syntax"; echo "[PASS] bin/rancid syntax"
    else
        fail=$((fail+1)); echo "[FAIL] bin/rancid perl -c syntax"
    fi
else
    echo "[FAIL] bin/rancid script missing: $PKG/bin/rancid"; fail=$((fail+1))
fi

# ---------- 汇总（确定性来源，供 conanfile 解析生成 HMBS 标记） ----------
total=$((pass+fail))
echo "RANCID_TEST_TOTAL=$total"
echo "RANCID_TEST_PASS=$pass"
echo "RANCID_TEST_FAIL=$fail"
if [ "$fail" -eq 0 ] && [ "$total" -gt 0 ]; then
    echo "rancid consumer test: ALL PASS ($pass/$total)$passname"
    exit 0
else
    echo "rancid consumer test: FAILED (pass=$pass fail=$fail total=$total)"
    exit 1
fi
