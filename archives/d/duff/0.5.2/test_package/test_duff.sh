#!/data/service/hnp/bin/bash
# test_package/test_duff.sh — duff 0.5.2（上游 0.5.2）消费者端到端验证
#
# 由 test_package/conanfile.py 以 conanrun 环境执行：
#   PATH          含 <package_folder>/bin（duff 可执行文件）
#   LD_LIBRARY_PATH 含 gettext 包 lib（libintl.so.8）
#
# 断言分两组：
#   [上游行为] 真实执行安装好的 duff，覆盖重复检测/摘要/模式开关
#   [OHOS 契约] 平台适配是否真实生效（ELF 架构 / libintl 依赖 / gettext 译文）
# 注意：不要开 pipefail —— 断言里大量使用 `生产者 | grep -q`，grep 命中即退出会让
# 生产者收到 SIGPIPE（141），pipefail 会把整条管道判为失败（实测 rc=141 的假失败）。
set -u

PASS=0
FAIL=0

ok()   { PASS=$((PASS + 1)); echo "PASS $PASS: $1"; }
OUT=""
RC=0
bad()  { FAIL=$((FAIL + 1)); echo "FAIL: $1 :: rc=$RC :: $(echo "$OUT" | head -2 | tr '\n' ' ')"; }
check(){ OUT=$(eval "$2" 2>&1); RC=$?; if [ "$RC" = "0" ]; then ok "$1"; else bad "$1"; fi; }

echo "--- duff 消费者验证（上游行为 + OHOS 契约）---"

# ---------------------------------------------------------------- 0. 基本可用
command -v duff >/dev/null 2>&1 || { echo "FAIL: duff 不在 PATH 中"; exit 1; }
DUFF_BIN=$(command -v duff)
echo "duff binary: $DUFF_BIN"

VERSION_LINE=$(duff -v | head -1)
check "上游客端: -v 输出版本 duff 0.5.2" '[ "$VERSION_LINE" = "duff 0.5.2" ]'

# ------------------------------------------------------------ 1. 真实重复检测
SCRATCH="${TMPDIR:-$HOME/tmp}/duff-tp-$$"
rm -rf "$SCRATCH"
mkdir -p "$SCRATCH/sub"
trap 'rm -rf "$SCRATCH"' EXIT

printf 'hello world\n' > "$SCRATCH/a.txt"
cp "$SCRATCH/a.txt" "$SCRATCH/b.txt"
cp "$SCRATCH/a.txt" "$SCRATCH/sub/c.txt"
printf 'unique-content-xyz\n' > "$SCRATCH/u.txt"
printf 'AAAA\n' > "$SCRATCH/s1"
printf 'BBBB\n' > "$SCRATCH/s2"
: > "$SCRATCH/e1"
: > "$SCRATCH/e2"
cd "$SCRATCH" || exit 1

DEFAULT_OUT=$(duff -r .)
check "上游行为: 检出 3 文件重复簇（含子目录成员）" 'echo "$DEFAULT_OUT" | grep -q "3 files in cluster" && echo "$DEFAULT_OUT" | grep -q "^\./sub/c.txt$"'
check "上游行为: 默认 sha1 摘要值正确" 'echo "$DEFAULT_OUT" | grep -q "digest 22596363b3de40b06f981fb85d82312e8c0ed511"'
check "上游行为: 空文件簇被检出" 'echo "$DEFAULT_OUT" | grep -q "0 bytes, digest da39a3ee5e6b4b0d3255bfef95601890afd80709"'
check "上游行为: 同大小不同内容不误报" '[ "$(echo "$DEFAULT_OUT" | grep -c "s1\|s2")" = "0" ]'
check "上游行为: -e excess 模式只列多余副本（3 条：空文件簇 1 + 3 文件簇 2）" '[ "$(duff -e -r . | wc -l)" = "3" ]'
check "上游行为: -z 排除空文件" '! duff -z -r . | grep -q "0 bytes"'
check "上游行为: -t thorough 模式输出无 digest" '! duff -t -r . | grep -q "digest"'
check "上游行为: -d sha256 摘要选择正确" 'duff -d sha256 -r . | grep -q "digest a948904f2f0f479b8f8197694b30184b0d2ed1c1cd2a1ec0fb85d299a192a447"'
check "上游行为: -d sha512 摘要长度 128 hex" '[ "$(duff -d sha512 -r . | grep -oE "digest [0-9a-f]+" | head -1 | awk "{print length(\$2)}")" = "128" ]'
check "上游行为: -d 非法摘要名报错退出非 0" 'duff -d md5 -r . >/dev/null 2>&1; [ $? -ne 0 ]'
check "上游行为: -0 NUL 分隔输出" '[ "$(duff -0 -e -r . | tr -d "\0" | tr -cd "/" | wc -c)" -gt 0 ]'
check "上游行为: -q 静默不存在的路径" '[ -z "$(duff -q /nonexistent-duff-tp 2>&1)" ]'
check "上游行为: -h 列出 16 个选项" '[ "$(duff -h | grep -c "^  -")" = "16" ]'

# --------------------------------------------------------- 2. OHOS 平台契约
check "OHOS 契约: 产物为 AArch64 ELF" 'readelf -h "$DUFF_BIN" | grep -q "AArch64"'
check "OHOS 契约: 动态依赖 gettext 的 libintl.so.8" 'readelf -d "$DUFF_BIN" | grep -q "libintl.so.8"'
check "OHOS 契约: 动态依赖 musl libc.so" 'readelf -d "$DUFF_BIN" | grep -q "libc.so"'
PKG_PREFIX=$(dirname "$(dirname "$DUFF_BIN")")
check "OHOS 契约: 4 个 gettext 语言目录随包安装" '[ "$(ls "$PKG_PREFIX"/share/locale/*/LC_MESSAGES/duff.mo 2>/dev/null | wc -l)" = "4" ]'
# 编译期 LOCALEDIR 由 autoconf 以绝对路径写入二进制：Conan 打包保持可重定位
# 布局（--prefix=/），故二进制内的 LOCALEDIR 是 "//share/locale"（等价
# /share/locale），而包内 payload 落在 <pkg>/share/locale。这里校验 payload
# 真实可用 + 二进制内 LOCALEDIR 契约；译文“运行时”验证见适配报告上游测试 C 组
# （本地 --prefix=<真实前缀> 构建，LANGUAGE=sv 输出 "filer i grupp"）。
# 注：不能用系统 grep 直接搜 .mo —— conanrun 环境下 PATH 命中 /system/bin/grep
# （toybox 0.8.12），它在第一个 NUL 处停止搜索，二进制内容命中数恒为 0。
# 这里用 gettext 包自带 msgunfmt 把 .mo 还原成 .po 文本再断言（同时验证 catalog 结构有效）。
check "OHOS 契约: 瑞典语目录内容真实（msgunfmt 还原后可检索 msgstr）" 'msgunfmt "$PKG_PREFIX/share/locale/sv/LC_MESSAGES/duff.mo" | grep -q "filer i grupp"'
check "OHOS 契约: 二进制内置 LOCALEDIR（autoconf 绝对路径，prefix=/ 时为 //share/locale）" 'strings "$DUFF_BIN" | grep -q "^//share/locale$"'
check "OHOS 契约: C locale 输出英文对照" 'LC_ALL=C LANGUAGE=C duff -r . | grep -q "files in cluster"'

echo ""
echo "test_package duff/0.5.2: ${PASS} passed, ${FAIL} failed"
[ "$FAIL" = "0" ] || exit 1
exit 0
