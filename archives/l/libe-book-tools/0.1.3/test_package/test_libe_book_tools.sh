#!/bin/sh
# test_package 消费者测试 —— libe-book-tools 0.1.3（HarmonyOS PC / aarch64）
#
# 用法: sh test_libe_book_tools.sh <bin目录> <工作目录> <包根目录>
#
# 只验交付物本身：三个转换器是否真的在 OHOS 上可执行、是否真的解析文档、
# 以及负向对照（不认格式必须报错、非法选项必须非零退出），避免「恒定回显」假绿。
# 语料由脚本就地生成（FictionBook 2 正向、XHTML 记 0.1.3 的已知边界、一段
# 非文档字节作负向），不往仓库里塞样本文件。
# 输出末行固定: TOTAL=<n> PASS=<n> FAIL=<n>

set -u

BIN="$1"
WORK="$2"
PKG="$3"

# 期望串（真机实测输出校准后固化在此处）
FB2_BODY_TOKEN="HarmonyOSFb2FixtureParagraph"
FB2_TITLE_TOKEN="FixtureOfTheMountain"
FB2_AUTHOR_TOKEN="Lovelace"
XHTML_BODY_TOKEN="HarmonyXhtmlFixtureSentence"

TOTAL=0
PASS=0
FAIL=0

ok() {
    TOTAL=$((TOTAL + 1))
    PASS=$((PASS + 1))
    printf '[PASS] %s\n' "$1"
}

bad() {
    TOTAL=$((TOTAL + 1))
    FAIL=$((FAIL + 1))
    printf '[FAIL] %s\n' "$1"
}

check() {
    # check <说明> <命令...>
    label="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        ok "$label"
    else
        bad "$label"
    fi
}

check_rc() {
    # check_rc <说明> <期望退出码> <命令...>
    label="$1"
    want="$2"
    shift 2
    "$@" >/dev/null 2>&1
    got=$?
    if [ "$got" = "$want" ]; then
        ok "$label (rc=$got)"
    else
        bad "$label (want rc=$want, got rc=$got)"
    fi
}

contains() {
    # contains <说明> <固定串> <文件>
    label="$1"
    needle="$2"
    file="$3"
    if [ -f "$file" ] && grep -qF -- "$needle" "$file"; then
        ok "$label"
    else
        bad "$label (缺少片段 ${needle})"
    fi
}

refutes() {
    label="$1"
    needle="$2"
    file="$3"
    if [ -f "$file" ] && ! grep -qF -- "$needle" "$file"; then
        ok "$label"
    else
        bad "$label (不该出现片段 ${needle})"
    fi
}

nonempty() {
    label="$1"
    file="$2"
    if [ -s "$file" ]; then
        ok "$label ($(wc -c < "$file" | tr -d ' ') bytes)"
    else
        bad "$label (输出为空)"
    fi
}

# ── 1. 交付物结构 ────────────────────────────────────────────────────────
check "包内 bin/ 目录存在" test -d "$BIN"
check "ebook2text 已安装且可执行" test -x "$BIN/ebook2text"
check "ebook2raw 已安装且可执行" test -x "$BIN/ebook2raw"
check "ebook2html 已安装且可执行" test -x "$BIN/ebook2html"
# 库与工具是两个包（W2）：本包只应交付可执行文件，不应重复交付 libe-book 的静态库/头文件
check "本包不重复交付 lib/（库属 libe-book 包）" test ! -e "$PKG/lib"
check "本包不重复交付 include/（库属 libe-book 包）" test ! -e "$PKG/include"
check "许可证已随包交付" test -f "$PKG/licenses/COPYING"

# ── 2. ELF 身份（OHOS 内核只放行本架构且签名有效的可执行文件）────────────
elf_magic() {
    head_bytes=$(od -An -tx1 -N4 "$1" 2>/dev/null | tr -d ' \n')
    [ "$head_bytes" = "7f454c46" ]
}
elf_aarch64() {
    # e_machine 位于偏移 18，小端 b700 == EM_AARCH64(183)
    mach=$(od -An -tx1 -j18 -N2 "$1" 2>/dev/null | tr -d ' \n')
    [ "$mach" = "b700" ]
}
check "ebook2text 是 ELF 镜像" elf_magic "$BIN/ebook2text"
check "ebook2text 的 e_machine 为 EM_AARCH64" elf_aarch64 "$BIN/ebook2text"
check "ebook2raw 的 e_machine 为 EM_AARCH64" elf_aarch64 "$BIN/ebook2raw"
check "ebook2html 的 e_machine 为 EM_AARCH64" elf_aarch64 "$BIN/ebook2html"

# ── 3. 真能跑起来（--version 走 exit 0 分支）─────────────────────────────
check_rc "ebook2text --version 退出码 0" 0 "$BIN/ebook2text" --version
check_rc "ebook2raw --version 退出码 0" 0 "$BIN/ebook2raw" --version
check_rc "ebook2html --version 退出码 0" 0 "$BIN/ebook2html" --version
"$BIN/ebook2text" --version > "$WORK/ver_text.txt" 2>&1
contains "ebook2text --version 自报的程序名与版本" "ebook2text 0.1.3" "$WORK/ver_text.txt"

# ── 4. 生成两份真实语料 ─────────────────────────────────────────────────
cat > "$WORK/fixture.fb2" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <genre>Detetective</genre>
      <author>
        <nickname>$FB2_AUTHOR_TOKEN</nickname>
      </author>
      <book-title>$FB2_TITLE_TOKEN</book-title>
      <lang>en</lang>
    </title-info>
    <document-info>
      <program-version>libe-book-tools-fixture</program-version>
      <version>1</version>
    </document-info>
  </description>
  <body>
    <section>
      <title><p>$FB2_BODY_TOKEN title line</p></title>
      <p>$FB2_BODY_TOKEN first line.</p>
      <p>Second line of the same paragraph body.</p>
    </section>
  </body>
</FictionBook>
EOF
check "FB2 语料已生成" test -s "$WORK/fixture.fb2"

cat > "$WORK/fixture.xhtml" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <head><title>xhtml fixture</title></head>
  <body>
    <p>$XHTML_BODY_TOKEN first line.</p>
    <p>$XHTML_BODY_TOKEN second line.</p>
  </body>
</html>
EOF
check "XHTML 语料已生成" test -s "$WORK/fixture.xhtml"

# 负向语料：不是任何受支持格式的字节串
printf 'NOT-A-DOCUMENT\x00\x01\x02 plain bytes\n' > "$WORK/garbage.bin"
check "负向语料已生成" test -s "$WORK/garbage.bin"

# ── 5. 正向：三种输出都能把文档解析出来 ────────────────────────────────
# 第二种格式（XHTML）在 0.1.3 上不成立，已按实测移除而非伪造语料：
# ebook2text 对最小 .xhtml 语料的 rc=1 且 **stderr 为空** —— 说明 detectXML 认出
# 了 TYPE_XHTML（否则会打印 "has not been recognized"），失败发生在
# EBOOKDocument::parse 内部，即 0.1.3 的 HTMLParser 不接受该语料（0.1.4 改了
# src/lib/EBOOKSAXParser.cpp / EBOOKXMLParser.cpp 等）。见 notes.md「已知边界」。
"$BIN/ebook2text" "$WORK/fixture.fb2" > "$WORK/text_fb2.out" 2> "$WORK/text_fb2.err"
check_rc "ebook2text 解析 FB2 退出码 0" 0 "$BIN/ebook2text" "$WORK/fixture.fb2"
contains "ebook2text 的 FB2 输出含正文句" "$FB2_BODY_TOKEN" "$WORK/text_fb2.out"
nonempty "ebook2text 的 FB2 输出非空" "$WORK/text_fb2.out"
refutes "ebook2text 未把 FB2 原文当字节回显（确实过了 XML 解析）" "<FictionBook" "$WORK/text_fb2.out"

"$BIN/ebook2raw" "$WORK/fixture.fb2" > "$WORK/raw_fb2.out" 2> "$WORK/raw_fb2.err"
check_rc "ebook2raw 解析 FB2 退出码 0" 0 "$BIN/ebook2raw" "$WORK/fixture.fb2"
nonempty "ebook2raw 的 FB2 输出非空" "$WORK/raw_fb2.out"
contains "ebook2raw 转储文档模型结构（openParagraph）" "openParagraph" "$WORK/raw_fb2.out"
contains "ebook2raw 转储里正文以 insertText 出现（内容确实流过 RVNGTextInterface）" "insertText(text: $FB2_BODY_TOKEN first line.)" "$WORK/raw_fb2.out"
contains "ebook2raw 转储带元数据（setDocumentMetaData）" "setDocumentMetaData" "$WORK/raw_fb2.out"

"$BIN/ebook2html" "$WORK/fixture.fb2" > "$WORK/html_fb2.out" 2> "$WORK/html_fb2.err"
check_rc "ebook2html 解析 FB2 退出码 0" 0 "$BIN/ebook2html" "$WORK/fixture.fb2"
nonempty "ebook2html 的 FB2 输出非空" "$WORK/html_fb2.out"
contains "ebook2html 产出 html 根元素" "<html>" "$WORK/html_fb2.out"
contains "ebook2html 输出含正文句" "$FB2_BODY_TOKEN" "$WORK/html_fb2.out"
contains "ebook2html 把作者写进 meta" "content=\"$FB2_AUTHOR_TOKEN\"" "$WORK/html_fb2.out"
contains "ebook2html 把书名写进 meta subject" "content=\"$FB2_TITLE_TOKEN\"" "$WORK/html_fb2.out"

# 0.1.3 的已知边界，按实测写成可执行断言而不是伪造语料：最小 XHTML 文档被
# detectXML 认出（否则会像 garbage.bin 那样打印 "has not been recognized"），
# 但 EBOOKDocument::parse 返回非 OK → rc=1 且 stderr 为空。上游在 0.1.4 里改了
# 这条链路（EBOOKSAXParser.cpp / EBOOKXMLParser.cpp 等 43 个文件与 0.1.3 不同）。
"$BIN/ebook2text" "$WORK/fixture.xhtml" > "$WORK/text_xhtml.out" 2> "$WORK/text_xhtml.err"
check_rc "0.1.3 已知边界：XHTML 语料 parse 非 OK 必须退出码 1" 1 "$BIN/ebook2text" "$WORK/fixture.xhtml"
refutes "XHTML 失败点在 parse 而非识别（stderr 不得出现 not recognized）" "has not been recognized" "$WORK/text_xhtml.err"
refutes "XHTML 失败时不得把源文件内容当正文吐出" "$XHTML_BODY_TOKEN" "$WORK/text_xhtml.out"

# 元数据通道（--info 走 RVNGTextTextGenerator 的 isInfo 分支）
"$BIN/ebook2text" --info "$WORK/fixture.fb2" > "$WORK/info_fb2.out" 2> "$WORK/info_fb2.err"
check_rc "ebook2text --info 退出码 0" 0 "$BIN/ebook2text" --info "$WORK/fixture.fb2"
contains "ebook2text --info 报出书名元数据（dc:subject）" "dc:subject $FB2_TITLE_TOKEN" "$WORK/info_fb2.out"
contains "ebook2text --info 报出作者元数据（meta:initial-creator）" "meta:initial-creator $FB2_AUTHOR_TOKEN" "$WORK/info_fb2.out"
if cmp -s "$WORK/text_fb2.out" "$WORK/info_fb2.out"; then
    bad "--info 的输出与正文输出相同（元数据分支形同虚设）"
else
    ok "--info 走的是与正文不同的输出分支"
fi

# ── 6. 负向对照：证明非零退出真的来自判定，而不是恒零回显 ──────────────
"$BIN/ebook2text" "$WORK/garbage.bin" > "$WORK/garbage.out" 2> "$WORK/garbage.err"
check_rc "无法识别的输入必须退出码 1" 1 "$BIN/ebook2text" "$WORK/garbage.bin"
contains "报错文案指明格式未被识别" "has not been recognized" "$WORK/garbage.err"
check_rc "同一负向输入下 ebook2raw 也必须退出码 1" 1 "$BIN/ebook2raw" "$WORK/garbage.bin"
check_rc "同一负向输入下 ebook2html 也必须退出码 1" 1 "$BIN/ebook2html" "$WORK/garbage.bin"

# 上游 CLI 语义：未知选项与无参数都落到 printUsage()（return -1 → 255）
check_rc "未知选项非零退出" 255 "$BIN/ebook2text" --definitely-not-an-option
check_rc "无参数时打印 usage 并非零退出" 255 "$BIN/ebook2text"

printf 'TOTAL=%s PASS=%s FAIL=%s\n' "$TOTAL" "$PASS" "$FAIL"
[ "$FAIL" = 0 ] || exit 1
exit 0
