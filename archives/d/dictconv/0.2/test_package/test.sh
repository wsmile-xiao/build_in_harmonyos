#!/data/service/hnp/bin/bash
# test_package/test.sh — dictconv 0.2 消费者测试（OHOS / aarch64-linux-ohos）
#
# 上游 dictconv 0.2（2007-10）没有测试套件：autotools 侧 Makefile.am 无 TESTS/check
# 目标，CMake 侧无 enable_testing()/add_test()，源码树也没有 test 目录，因此本脚本
# 从消费者视角验证已安装的 dictconv 可执行文件（夹具在脚本内生成，不依赖外部文件）：
#   1. --version：GNU 长选项（补丁 0003）+ 版本号
#   2. --help：用法与支持的输入/输出格式清单
#   3. FreeDict(.tei) → PlainText(.dic)：libxml2 解析路径 + 字节级结果
#   4. FreeDict(.tei) → StarDict(.ifo/.idx/.dict)：写入器 + 二进制 .idx 字节级结果
#   5. FreeDict(.tei) → DICT(.index/.dict)：偏移表与词典体字节级结果
#   6. 非法输出扩展名 → 非零退出 + 明确提示
#   7. 输入文件不存在 → 非零退出 + 明确提示
#   8. HarmonyOS/aarch64 消费者运行时：验证安装的 ELF 架构并实际执行版本查询
#
# R34: 每个用例都真实调用被测包安装出来的二进制。
# 说明：本脚本对所有可能非零退出的命令都用 `||` / `if` / run() 包装（run() 显式捕获
# 退出码），因此可以安全启用 set -e；见下方 run() 注释。
set -euo pipefail

PASS=0
FAIL=0
ok() { printf '  [PASS] %s\n' "$1"; PASS=$((PASS + 1)); }
bad() { printf '  [FAIL] %s\n' "$1"; FAIL=$((FAIL + 1)); }

DICTCONV="$(command -v dictconv || true)"
if [ -z "$DICTCONV" ]; then
    echo "  [FAIL] dictconv not found in PATH (conanrun 应把包内 bin/ 加入 PATH)"
    exit 1
fi
echo "[info] dictconv = $DICTCONV"

# 工作目录：优先用 mktemp；/tmp 不可写时退回脚本所在目录，退出时统一清理
WORK="$(mktemp -d 2>/dev/null || true)"
if [ -z "${WORK:-}" ] || [ ! -d "$WORK" ]; then
    WORK="$(pwd)/dictconv-test-work"
    rm -rf "$WORK"
    mkdir -p "$WORK"
fi
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

# 退出码捕获：set -u 环境下属正常语句，用 || 兜住非零退出
RC=0
run() {
    local log="$1"
    shift
    RC=0
    "$@" >"$log" 2>&1 || RC=$?
}

# 夹具：FreeDict TEI 词典（根元素必须是 tei.2，上游 FreedictReader 的要求）
cat >sample.tei <<'TEI'
<?xml version="1.0" encoding="UTF-8"?>
<tei.2>
  <teiHeader>
    <fileDesc>
      <titleStmt><title>dictconv consumer test</title></titleStmt>
      <publicationStmt><p>test fixture</p></publicationStmt>
      <sourceDesc><p>test fixture</p></sourceDesc>
    </fileDesc>
  </teiHeader>
  <text>
    <body>
      <entry><form><orth>apple</orth></form><trans><tr>a round fruit</tr></trans></entry>
      <entry><form><orth>book</orth></form><trans><tr>a written work</tr></trans></entry>
    </body>
  </text>
</tei.2>
TEI

echo
echo "[1/8] --version"
run version.txt "$DICTCONV" --version
if [ "$RC" -eq 0 ] && grep -q 'Dictconv 0.2' version.txt; then
    ok "--version 退出码 0 且输出含 'Dictconv 0.2'"
else
    bad "--version（rc=$RC）"
    sed 's/^/        /' version.txt
fi

echo
echo "[2/8] --help 用法清单"
run help.txt "$DICTCONV" --help
MISSING=""
for fmt in '.bgl' '.tei' '.dct' '.ifo' '.index' '.dic'; do
    grep -qF "$fmt" help.txt || MISSING="$MISSING $fmt"
done
if [ -z "$MISSING" ]; then
    ok "--help 列出全部输入/输出格式（.bgl/.tei/.dct/.ifo/.index/.dic）"
else
    bad "--help 缺少格式说明:$MISSING"
    sed 's/^/        /' help.txt
fi

echo
echo "[3/8] FreeDict(.tei) → PlainText(.dic)"
printf 'apple\ta round fruit\nbook\ta written work\n' >expect.dic
run c3.log "$DICTCONV" -o plain.dic sample.tei
if [ "$RC" -eq 0 ] && cmp -s expect.dic plain.dic; then
    ok "plain.dic 与期望字节一致（2 条词条，headword<TAB>definition）"
else
    bad "转换失败或输出不符（rc=$RC）"
    sed 's/^/        /' c3.log
fi

echo
echo "[4/8] FreeDict(.tei) → StarDict(.ifo/.idx/.dict)"
printf "StarDict's dict ifo file\nversion=2.4.2\nbookname=dictconv consumer test\nwordcount=2\nidxfilesize=27\nsametypesequence=m\n" >expect.ifo
printf 'apple\000\000\000\000\000\000\000\000\015' >expect.idx
printf 'book\000\000\000\000\015\000\000\000\016' >>expect.idx
printf 'a round fruita written work' >expect.stardict.dict
run c4.log "$DICTCONV" --output star.ifo sample.tei
if [ "$RC" -eq 0 ] && cmp -s expect.ifo star.ifo && cmp -s expect.idx star.idx && cmp -s expect.stardict.dict star.dict; then
    ok "star.ifo/star.idx/star.dict 均与期望字节一致（同时验证 --output 长选项）"
else
    bad "StarDict 输出不符（rc=$RC）"
    sed 's/^/        /' c4.log
fi

echo
echo "[5/8] FreeDict(.tei) → DICT(.index/.dict)"
printf 'apple\tA\tN\nbook\tN\tO\n' >expect.index
printf 'a round fruita written work' >expect.dictd.dict
run c5.log "$DICTCONV" -o dict.index sample.tei
if [ "$RC" -eq 0 ] && cmp -s expect.index dict.index && cmp -s expect.dictd.dict dict.dict; then
    ok "dict.index（偏移表 A/N/N/O = 0/13/13/14）与 dict.dict 均与期望字节一致"
else
    bad "DICT 输出不符（rc=$RC）"
    sed 's/^/        /' c5.log
fi

echo
echo "[6/8] 非法输出扩展名"
run c6.log "$DICTCONV" -o output.xyz sample.tei
if [ "$RC" -ne 0 ] && grep -q 'valid output file' c6.log; then
    ok "非法输出扩展名被拒绝（rc=$RC: You should specify a valid output file.）"
else
    bad "非法输出扩展名未被拒绝（rc=$RC）"
    sed 's/^/        /' c6.log
fi

echo
echo "[7/8] 输入文件不存在"
run c7.log "$DICTCONV" -o missing.dic no-such-file.tei
if [ "$RC" -ne 0 ] && grep -q 'Error converting' c7.log; then
    ok "输入不存在时报错退出（rc=$RC: Error converting ...）"
else
    bad "输入不存在时未报错（rc=$RC）"
    sed 's/^/        /' c7.log
fi

echo

echo "[8/8] HarmonyOS/aarch64 消费者运行时"
if command -v readelf >/dev/null 2>&1; then
    RC=0
    readelf -h "$DICTCONV" >elf-header.txt 2>&1 || RC=$?
    if [ "${RC:-0}" -eq 0 ] && grep -q 'AArch64' elf-header.txt \
        && "$DICTCONV" --version >ohos-version.txt 2>&1 \
        && grep -q 'Dictconv 0.2' ohos-version.txt; then
        ok "OHOS 消费者运行时可执行（ELF Machine=AArch64，--version 正常）"
    else
        bad "OHOS/aarch64 消费者运行时验证失败"
        sed 's/^/        /' elf-header.txt ohos-version.txt 2>/dev/null || true
    fi
elif command -v file >/dev/null 2>&1; then
    RC=0
    file "$DICTCONV" >elf-header.txt 2>&1 || RC=$?
    if [ "${RC:-0}" -eq 0 ] && grep -Eiq 'aarch64|arm64' elf-header.txt \
        && "$DICTCONV" --version >ohos-version.txt 2>&1 \
        && grep -q 'Dictconv 0.2' ohos-version.txt; then
        ok "OHOS 消费者运行时可执行（file 确认为 AArch64，--version 正常）"
    else
        bad "OHOS/aarch64 消费者运行时验证失败"
        sed 's/^/        /' elf-header.txt ohos-version.txt 2>/dev/null || true
    fi
else
    bad "无法验证 OHOS/aarch64 架构：readelf 和 file 均不可用"
fi

echo
echo "===== dictconv/0.2 test_package: ${PASS} passed, ${FAIL} failed ====="
[ "$FAIL" -eq 0 ] || exit 1
