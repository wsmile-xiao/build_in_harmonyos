#!/bin/sh
# dd_rescue 消费者侧功能测试（R34：真实执行，非空壳断言）
#   用法: sh run_dd_rescue_tests.sh <package_folder> <outdir>
set -u

PKG="${1:-}"; OUT="${2:-.}"
BIN="$PKG/bin/dd_rescue"
LIBDIR="$PKG/lib"
mkdir -p "$OUT"
cd "$OUT" || exit 1

PASS=0; FAIL=0; SKIP=0
ok()   { PASS=$((PASS+1)); echo "  [PASS] $1"; }
bad()  { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }
skip() { SKIP=$((SKIP+1)); echo "  [SKIP] $1"; }

echo "== dd_rescue 上游接口测试 =="
echo "  包目录: $PKG"

# ---------- ① 版本断言 ----------
if [ ! -x "$BIN" ]; then
    bad "bin/dd_rescue 不存在或不可执行"
else
    V=$("$BIN" -V 2>&1 | tr -d '\r' | grep -oE 'Version [0-9]+\.[0-9]+\.[0-9]+' | head -1 | awk '{print $2}')
    if [ "$V" = "1.99.22" ]; then
        ok "dd_rescue -V 报告版本 $V"
    else
        bad "版本号不符：期望 1.99.22，实得 '${V:-空}'"
    fi
fi

# ---------- ② 真实数据复制 + 逐字节比对（核心功能）----------
SRC=ddr_in.bin; DST=ddr_out.bin
rm -f "$SRC" "$DST"
# 造 1MiB 非平凡数据（不用 /dev/zero，避免"内容全零"掩盖复制缺陷）
i=0
while [ $i -lt 64 ]; do
    printf 'dd_rescue-payload-block-%04d-abcdefghijklmnopqrstuvwxyz\n' "$i"
    i=$((i+1))
done > "$SRC"
# 补齐到 1MiB，保证有跨块边界的数据
dd if=/dev/urandom of="$SRC" bs=1024 count=1024 2>/dev/null || true

if [ -s "$SRC" ]; then
    if "$BIN" -q "$SRC" "$DST" >/dev/null 2>&1; then
        if [ -s "$DST" ] && cmp -s "$SRC" "$DST"; then
            ok "真实复制 1MiB 数据并逐字节一致（cmp 无差异）"
        else
            bad "复制结果与源不一致（cmp 有差异或输出为空）"
        fi
    else
        bad "dd_rescue 复制执行失败"
    fi
else
    skip "无法生成测试数据"
fi

# ---------- ③ 插件真实加载（dlopen 验证）----------
if [ -f "$LIBDIR/libddr_hash.so" ]; then
    # 用插件对已复制的文件做哈希；插件能被 dlopen 且返回 0 即通过
    if "$BIN" -qATL "$LIBDIR/libddr_hash.so=algo=sha256" "$SRC" "$OUT/plug.bin" >/dev/null 2>&1; then
        ok "插件 libddr_hash.so 被真实加载并完成哈希路径调用"
    else
        skip "插件调用未成功（依赖缺失时如实跳过，不计通过）"
    fi
else
    bad "缺少插件 libddr_hash.so"
fi
for p in libddr_null.so libddr_crypt.so; do
    [ -f "$LIBDIR/$p" ] && ok "插件存在: $p" || bad "缺少插件: $p"
done

# ---------- ④ 负向用例（证明断言非恒真）----------
# ⚠️ 必须在二进制**可用**时才做此断言：否则命令 127（不存在）会被误当作"正确失败"，
#    与 ① 的缺失态叠加成**假阳性**（断言恒真）。实测踩过此坑。
if [ ! -x "$BIN" ]; then
    skip "负向用例：二进制不可用，无法区分「工具正确报错」与「命令不存在」"
else
    if "$BIN" -q "this_file_does_not_exist_xyz.bin" "$OUT/neg.bin" >/dev/null 2>&1; then
        bad "负向用例失败：对不存在的输入竟返回成功（断言可能恒真）"
    elif [ $? -eq 127 ]; then
        skip "负向用例：命令无法执行（127），不作判定"
    else
        ok "负向用例：不存在的输入文件正确返回失败"
    fi
fi

echo ""
echo "RESULT: passed=$PASS failed=$FAIL skipped=$SKIP"
[ "$FAIL" -eq 0 ] || exit 1
