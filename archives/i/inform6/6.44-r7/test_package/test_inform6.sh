#!/usr/bin/env bash
# inform6 6.44-r7 消费者冒烟测试（修复版：四坑已按源码语义重写）
#
# 用打包出的编译器真实编译两个 Z-machine 游戏源：
#   1) min.inf —— 最小游戏（Story/Headline 常量 + parser/verblib/grammar
#      全库 + Initialise 例程入口，v5）
#   2) advent.inf —— 上游标准演示（完整标准库特性，v5）
# 断言：编译退出码 0、产物存在且非空、Z-code 版本字节正确、数据目录清单在位；
# 并附负向用例（错误源必须被编译器拒绝）。
#
# 用法: test_inform6.sh <package_folder> <writable_work_root>
set -u

PKG="$1"
WORK_ROOT="$2"
WORK="$WORK_ROOT/inform6-test"

BIN="$PKG/bin/inform6"
LIB="$PKG/share/inform6/std/lib"
INC="$PKG/share/inform6/std/include"
DEMOS="$PKG/share/inform6/std/demos"

PASS=0

ok() { PASS=$((PASS + 1)); echo "  [OK] $1"; }
fail() { echo "  [FAIL] $1"; exit 1; }

# R10: 所有临时文件落在调用方提供的构建目录内，不依赖只读的 /tmp。
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK" || fail "无法创建测试工作目录 $WORK"

echo "== [1/6] 二进制与数据目录在位"
[ -x "$BIN" ] || fail "inform6 二进制缺失: $BIN"
[ -f "$LIB/parser.h" ] || fail "标准库 lib 缺失 parser.h"
[ -f "$INC/dmenus.h" ] || fail "标准库 include 缺失 dmenus.h"
[ -f "$DEMOS/advent.inf" ] || fail "演示源缺失 advent.inf"
[ -f "$LIB/English.h" ] && [ -f "$LIB/VerbLib.h" ] || fail "大小写别名副本缺失"
NLIB=$(find "$LIB" -type f | wc -l)
# 20=大小写敏感文件系统（15 原件 + 5 个大写别名真副本，CI Linux）；
# 15=大小写不敏感文件系统（别名即原文件，package() 跳过副本，OHOS 真机）。
[ "$NLIB" -eq 20 ] || [ "$NLIB" -eq 15 ] || fail "std/lib 文件数 $NLIB != 15/20"
[ "$(find "$INC" -type f | wc -l)" -eq 19 ] || fail "std/include 文件数 != 19"
[ "$(find "$DEMOS" -type f | wc -l)" -eq 9 ] || fail "std/demos 文件数 != 9"
ok "二进制可执行、lib/include/demos 清单与大小写别名在位"

echo "== [2/6] 编译最小游戏（min.inf, v5）"
# 6.44 语义（directs.c 源码注释，与 6.42 同款）：Include ">name" 从当前
# 文件所在目录加载（.inf 扩展名）；无 ">" 的 Include 走 Include_Path
# （+目录，.h 扩展名）。
# 注意：inform.c:1666 的 main() 选项循环调用 set_path_command(p+1) 时剥掉
# '+'，而该函数靠 command[0]=='+' 判断前插 → prepend 分支不可达，+目录
# 实际是替换语义、最后一个生效（源码实证 + 本地 A/B 实验）。上游 Makefile
# 规则本身每次编译也只传一个 +目录（%.z5 仅 +$(STDSRC)），故每次编译
# 只传 +"$LIB"（parser/verblib/grammar 均在 std/lib）。
# 6.12.8 标准库 parser.h 自带默认 Main（[ Main; InformLibrary.play(); ];，
# 不可重定义），游戏入口用 Initialise 例程（上游 advent.inf 同款写法）。
cat > min.inf <<'EOF'
Constant Story "OHOS test";
Constant Headline "^Hello, OHOS!^";

Include "parser";
Include "verblib";
Include "grammar";

[ Initialise;
    "Hello, OHOS!";
];
EOF
"$BIN" -v5 +"$LIB" min.inf min.z5 || fail "min.inf 编译失败"
[ -s min.z5 ] || fail "min.z5 未生成或为空"
ok "min.z5 生成"

echo "== [3/6] Z-code 版本字节校验（首字节 = 5）"
V=$(od -An -N1 -tu1 min.z5 | tr -d ' ')
[ "$V" = "5" ] || fail "min.z5 首字节 $V != 5"
ok "min.z5 为合法的 Z-machine v5 故事文件"

echo "== [4/6] 编译上游标准演示 advent.inf"
# 编译器从 cwd 打开源文件（Source_Path），源文件不走 Include_Path →
# 必须用 $DEMOS 全路径；+目录 同样只传一个。
"$BIN" -v5 +"$LIB" "$DEMOS/advent.inf" advent.z5 || fail "advent.inf 编译失败"
[ -s advent.z5 ] || fail "advent.z5 未生成或为空"
V=$(od -An -N1 -tu1 advent.z5 | tr -d ' ')
[ "$V" = "5" ] || fail "advent.z5 首字节 $V != 5"
ok "advent.inf → advent.z5 (v5)"

echo "== [5/6] 负向用例：语法错误源必须被拒绝"
cat > bad.inf <<'EOF'
[ This is not valid Inform syntax ]]]
EOF
if "$BIN" bad.inf bad.z5 >/dev/null 2>&1; then
  fail "错误源被编译通过（编译器未真正解析输入）"
fi
ok "错误源被正确拒绝（exit != 0）"

echo "== [6/6] 命令行 +目录 语义（punyinform 同款 -v3 +lib 规则）"
# PunyInform 6.6 序言按上游官方最小示例（tests/minimal-provideundo.inf
# 实测核对）：globals.h 必须先于 puny.h（RTE_* 常量定义在 globals.h，
# puny.h 自身只 include messages/grammar/scope/parser）；Puny 游戏
# 不定义 Main——puny.h 自带小写 main 主循环（与游戏 Main 同名冲突），
# 入口用 Initialise 例程；-~S 为官方 v3 序言标配。
cat > puny.in <<'EOF'
!% -~S
Constant Story "OHOS puny test";
Constant Headline "^Hello, OHOS!^";
Include "globals.h";
Include "puny.h";
[ Initialise; ];
EOF
if [ -f "$PKG/share/inform6/punyinform/lib/puny.h" ]; then
  "$BIN" -v3 +"$PKG/share/inform6/punyinform/lib" puny.in puny.z3 \
    || fail "PunyInform 入口编译失败（+目录 语义异常）"
  [ -s puny.z3 ] || fail "puny.z3 未生成或为空"
  V=$(od -An -N1 -tu1 puny.z3 | tr -d ' ')
  [ "$V" = "3" ] || fail "puny.z3 首字节 $V != 3"
  ok "puny.h 入口 → z3（+目录 参数生效）"
else
  echo "  [SKIP] 包内无 punyinform/lib/puny.h"
fi

echo "inform6 消费者测试全部通过（$PASS 组断言）"
