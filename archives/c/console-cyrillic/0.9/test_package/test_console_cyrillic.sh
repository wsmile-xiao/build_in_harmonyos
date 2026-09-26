#!/bin/bash
# console-cyrillic 0.9 消费者冒烟测试（OHOS 真机，包安装后执行）
# 基线：.deb 黄金 261 项 + 脚本真实行为实测（RC 不经管道）
set -u
# $1 = 包目录（conanfile test() 显式传参；缺省时回退 dirname($0)/..）
PKG="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
PASS=0; FAIL=0
ok()  { PASS=$((PASS+1)); echo "  [PASS] $1"; }
bad() { FAIL=$((FAIL+1)); echo "  [FAIL] $1"; }
check() { # $1=描述 $2=期望RC 其余=命令
  local d="$1" e="$2"; shift 2
  "$@" >/dev/null 2>&1
  [ "$?" -eq "$e" ] && ok "$d" || bad "$d (RC=$? 期望 $e)"
}
CC=$PKG/share/console-cyrillic

echo "=== T1: 6 个 bin 脚本落位且可执行 ==="
for s in cyr displayfont dumppsf makeacm mkvgafont raw2psf; do
  [ -x "$PKG/bin/$s" ] && ok "bin/$s 可执行" || bad "bin/$s 缺失或不可执行"
done

echo "=== T2: perl 脚本 shebang 已适配 ==="
for s in displayfont dumppsf makeacm raw2psf cyr; do
  head -1 "$PKG/bin/$s" | grep -q "^#!/usr/bin/env perl$" && ok "$s shebang env perl" || bad "$s shebang 未适配: $(head -1 $PKG/bin/$s)"
done
[ "$(head -1 $PKG/bin/mkvgafont)" = "#!/bin/sh" ] && ok "mkvgafont #!/bin/sh 保留" || bad "mkvgafont shebang 被误改"

echo "=== T3: kmap 数据（120 生成 + 16 option）==="
n=$(ls $CC/*.kmap 2>/dev/null | wc -l)
[ "$n" -eq 136 ] && ok "kmap 总数 136" || bad "kmap 总数 $n != 136"
no=$(ls $CC/option-*.kmap 2>/dev/null | wc -l)
[ "$no" -eq 16 ] && ok "option-kmap 16" || bad "option-kmap $no != 16"
# 生成 kmap 内容断言：keycode 行 + 12 布局前缀
for pre in ru ru_ms by bg_bds bg_phon sr mk ua ua_ms mn kaz_gost kaz_alt; do
  [ -f "$CC/$pre-unicode.kmap" ] && ok "布局 $pre-unicode 落位" || bad "布局 $pre-unicode 缺失"
done
kc=$(grep -c "^keycode" $CC/ru-unicode.kmap)
[ "$kc" -ge 100 ] && ok "ru-unicode keycode 行数 $kc>=100" || bad "ru-unicode keycode 行数 $kc"
grep -q "generated for encoding" $CC/ru-unicode.kmap && ok "kmap 含编码生成标记" || bad "kmap 无编码生成标记"
grep -qE "keycode +13[0-9] +=|keycode +[0-9] *=" $CC/ua_ms-unicode.kmap && ok "kmap keycode 行格式" || bad "kmap keycode 行格式异常"

echo "=== T4: 字体 44 psf（PSF 双魔数）==="
np=$(ls $CC/*.psf 2>/dev/null | wc -l)
[ "$np" -eq 44 ] && ok "psf 44" || bad "psf $np != 44"
m=$(head -c 2 $CC/alt_8x8.psf 2>/dev/null | od -An -tx1 | tr -d " \n")
{ [ "$m" = "3604" ] || [ "$m" = "72b5" ]; } && ok "alt_8x8.psf PSF 魔数 $m" || bad "alt_8x8.psf 魔数 $m"

echo "=== T5: 字符映射/屏幕映射/回退 ==="
[ "$(ls $CC/*.sfm.gz | wc -l)" -eq 8 ] && ok "sfm.gz 8" || bad "sfm.gz 数量异常"
[ "$(ls $CC/*.acm.gz | wc -l)" -eq 9 ] && ok "acm.gz 9" || bad "acm.gz 数量异常"
[ "$(ls $CC/*.screenmap | wc -l)" -eq 8 ] && ok "screenmap 8" || bad "screenmap 数量异常"
[ "$(ls $CC/*.trans | wc -l)" -eq 9 ] && ok "trans 9" || bad "trans 数量异常"
[ -f $CC/cyrillic.fallback.gz ] && [ -f $CC/cyrillic-graph.fallback.gz ] && ok "fallback.gz x2" || bad "fallback.gz 缺失"
# graph.fallback 组合还原（头行 + cyrillic + graph 段非空）
zcat $CC/cyrillic-graph.fallback.gz | head -1 | grep -q "combination between cyrillic.fallback and graph.fallback" && ok "graph.fallback 组合头行" || bad "graph.fallback 组合头行异常"

echo "=== T6: man/doc ==="
[ "$(ls $PKG/share/man/man1/*.1.gz | wc -l)" -eq 6 ] && ok "man1 gz 6" || bad "man1 gz 数量异常"
zcat $PKG/share/man/man1/cyr.1.gz 2>/dev/null | grep -q "console" && ok "man cyr.1 可读" || bad "man cyr.1 不可读"
[ -f $PKG/share/doc/console-cyrillic/windows/utf-8 ] && ok "windows/utf-8" || bad "windows/utf-8 缺失"
[ -f $PKG/share/doc/console-cyrillic/windows/pt154 ] && [ -f $PKG/share/doc/console-cyrillic/windows/mik ] && ok "windows/pt154+mik" || bad "windows/pt154/mik 缺失"

echo "=== T7: 脚本行为（真实 RC，无管道）==="
export PATH=/data/service/hnp/bin:$PATH
check "cyr --help 退出 2" 2 $PKG/bin/cyr --help
check "cyr 无参 退出 2" 2 $PKG/bin/cyr
check "mkvgafont 无参 退出 1" 1 $PKG/bin/mkvgafont
# displayfont 无参：探测 VT 失败 graceful 退出 0
check "displayfont 无参 退出 0" 0 $PKG/bin/displayfont
# raw2psf 功能：raw 8x16 → PSF1（魔数 36 04 + 256 字符 16 行 = 4116 字节）
# OHOS /tmp 只读——临时文件落 $PWD（包目录，run 命令 cwd=pkg_folder）
RF="$PWD/_r8x16.bin"; HF="$PWD/_psf_hdr"
python3 -c "open('$RF','wb').write(bytes(range(256))*16)" 2>/dev/null
if [ -f "$RF" ]; then
  # PSF1 魔数 = 前 2 字节 36 04（进度信息在 stderr，stdout 纯二进制）
  $PKG/bin/raw2psf "$RF" 2>/dev/null | head -c 2 > "$HF"
  H=$(od -An -tx1 "$HF" | tr -d " \n")
  [ "$H" = "3604" ] && ok "raw2psf 输出 PSF1 魔数 36 04" || bad "raw2psf 输出魔数 $H"
  rm -f "$RF" "$HF"
fi

echo
echo "=== 结果: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -eq 0 ] && echo "ALL PASS" || exit 1
