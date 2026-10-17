#!/bin/sh
# samhain 4.1.4 — test_package consumer assertions (5 items).
#
# 无网络无守护形态：全部操作走 samhain 的本地 file: 数据通路
# （版本查询 / TIGER hash / 建库 / 正向验证 / 篡改检出），
# 不读写配置文件、不落守护进程、不开任何 socket。
#
# 任一断言失败 → exit 1 → conan test_package 判负。
set -u   # 断言计数契约：只开 -u 不开 -e，5 条断言必须全部跑完并输出 PASS/FAIL 汇总行与退出码（-e 会在首条失败即中断、丢后续断言与汇总——code_style §7 的断言脚本例外场景，此处显式注记）

pass=0
fail=0
ok ()  { pass=$((pass + 1)); echo "[ok  ] $1"; }
bad () { fail=$((fail + 1)); echo "[FAIL] $1"; }

# ── 1. 版本断言：装出的二进制自报 4.1.4 ──────────────────────────────
ver=$(samhain -v 2>&1 | grep -F "This is samhain (4.1.4)" | head -1)
if [ -n "$ver" ]; then
    ok "1/5 samhain -v 自报 4.1.4"
else
    bad "1/5 samhain -v 未找到版本串 4.1.4"
fi

# ── 2. TIGER hash：两次调用确定性 + 与公布测试向量一致 ───────────────
h1=$(samhain -H "abc" 2>&1 | grep "string=" | head -1)
h2=$(samhain -H "abc" 2>&1 | grep "string=" | head -1)
expected="hash=<F258C1E88414AB2A527AB541FFC5B8BF935F7B951C132951>"
if [ -n "$h1" ] && [ "$h1" = "$h2" ] && echo "$h1" | grep -q "$expected"; then
    ok "2/5 TIGER hash 确定性且命中公布向量 abc"
else
    bad "2/5 TIGER hash 输出不符: [$h1] vs [$h2]"
fi

# ── 准备：两份样本文件 + 文件清单（本地临时目录，全部可写）───────────
# ABSOLUTE-FIX: samhain's --create-database only materialises the database for
# ABSOLUTE list entries (rc=0 with no output for relative ones — bisected:
# abs=produces file.*, rel=produces nothing, same binary); upstream harnesses
# always write absolute paths into their tmp_list_file too.
base="$(pwd)"
workdir="$base/tp_samhain_work"
rm -rf "$workdir"
mkdir -p "$workdir" || { bad "3/5 无法创建工作目录"; exit 1; }
echo "sample data A" > "$workdir/a.txt"
echo "sample data B" > "$workdir/b.txt"
printf '%s\n%s\n' "$workdir/a.txt" "$workdir/b.txt" > "$workdir/list.txt"

# ── 3. 建库：从文件清单生成校验数据库（免配置）───────────────────────
rm -f ./file.*
if samhain --create-database="$workdir/list.txt" >/dev/null 2>&1; then
    db=$(find . -maxdepth 1 -name 'file.*' | head -1)
    if [ -n "$db" ]; then
        ok "3/5 --create-database 生成数据库 $(basename "$db")"
    else
        bad "3/5 --create-database rc=0 但未产出 file.* 数据库"
    fi
else
    bad "3/5 --create-database 退出码非 0"
    db=""
fi

# ── 4. 正向验证：未篡改时 verify 通过（rc=0）─────────────────────────
if [ -n "$db" ] && samhain --verify-database="$db" >/dev/null 2>&1; then
    ok "4/5 --verify-database 未篡改树验证通过"
else
    bad "4/5 --verify-database 未篡改树未通过"
fi

# ── 5. 篡改检出：改动一个被守护文件后 verify 必须失败（rc!=0）────────
if [ -n "$db" ]; then
    echo "tampered by test_package" >> "$workdir/a.txt"
    if samhain --verify-database="$db" >/dev/null 2>&1; then
        bad "5/5 篡改后 --verify-database 仍通过（漏检）"
    else
        ok "5/5 篡改被检出（verify 返回非 0）"
    fi
else
    bad "5/5 跳过依赖的数据库缺失"
fi

echo "test_package: PASS=$pass FAIL=$fail TOTAL=$((pass + fail))"
[ "$fail" -eq 0 ] || exit 1
exit 0
