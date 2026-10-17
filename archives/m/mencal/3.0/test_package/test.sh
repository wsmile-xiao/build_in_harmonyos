#!/data/service/hnp/bin/bash
# test_package/test.sh — mencal/3.0 消费者测试（鸿蒙特有测试）
# 运行于 conanrun env（PATH 已含包 bin/）；上游无测试套件，全部 45 条断言均为鸿蒙侧新增。
# 其中 K 组 = 1 个端到端完整消费者用例（11 步闭环，真实跑通一条完整使用流程）：
#   经期配置生成 → 落盘 → 以落盘文件重载 → 年/三月视图渲染 → 标记回读 → 双路径等价 → 全流程产物终判。
# 用例设计依据（上游用法文档，非自造）：README 第 5 行 `NEXTINFO: ./mencal -h` 指向的帮助文本——
#   `Usage: mencal [options] [file1 file2 ... -c CONF1 -c CONF2 ...]`（位置参数=配置文件重载）、
#   `-c, --config s=..,l=..,d=..,n=NAME,f=FILE,c=COLOR` 与 `f,file=FILE filename to save configuration to`（配置落盘）、
#   `-1 / -3 / -y [YYYY]`（月/三月/年视图）。
# 断言计数口径：ok/ng 每调用一次 = 1 条断言；合计须等于 MANIFEST.yml 的 assertion_count。
set -u

PASS=0
FAIL=0
ok() { PASS=$((PASS + 1)); echo "  [ok] $1"; }
ng() { FAIL=$((FAIL + 1)); echo "  [NG] $1"; }

WORKBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$WORKBASE" 2>/dev/null || WORKBASE="$HOME/tmp"
mkdir -p "$WORKBASE" 2>/dev/null || WORKBASE="/tmp"
mkdir -p "$WORKBASE" 2>/dev/null || { echo "  [NG] 无法创建可写工作目录"; exit 1; }
WORK="$WORKBASE/mencal-tp-$$"
mkdir -p "$WORK" || exit 1
# 工作目录不得落进仓库（设备/CI 双端可写），退出即清理
trap 'rm -rf "$WORK"' EXIT

echo "== A. 直接执行与 shebang 适配（4） =="
if mencal -V >"$WORK/v.txt" 2>"$WORK/v.err"; then
  ok "A1 mencal -V 直接执行退出码 0（env-perl shebang 生效）"
else
  ng "A1 mencal -V 退出码非 0"
fi
grep -Fq "Menstruation calendar 3.0" "$WORK/v.txt" && ok "A2 -V 输出含版本串 Menstruation calendar 3.0" || ng "A2 -V 版本串缺失"
grep -Fq "(C) 2013 C. McCohy" "$WORK/v.txt" && ok "A3 -V 输出含版权行" || ng "A3 -V 版权行缺失"
shead=$(head -1 "$(command -v mencal)")
[ "$shead" = "#!/usr/bin/env perl" ] && ok "A4 安装脚本首行为 #!/usr/bin/env perl" || ng "A4 shebang 首行不符: $shead"

echo "== B. 帮助（2） =="
if mencal -h >"$WORK/h.txt" 2>/dev/null; then ok "B1 -h 退出码 0"; else ng "B1 -h 退出码非 0"; fi
grep -Fq "Usage: mencal [options]" "$WORK/h.txt" && ok "B2 -h 含 Usage 行" || ng "B2 -h Usage 行缺失"

echo "== C. 当月视图（3） =="
if mencal -q -1 >"$WORK/c1.txt" 2>/dev/null; then ok "C1 -q -1 退出码 0"; else ng "C1 -q -1 退出码非 0"; fi
[ -s "$WORK/c1.txt" ] && ok "C2 月视图 stdout 非空" || ng "C2 月视图 stdout 为空"
[ "$(sed -n 2p "$WORK/c1.txt")" = "Su Mo Tu We Th Fr Sa" ] \
  && ok "C3 默认星期头 Su Mo Tu We Th Fr Sa（locale 缺失仍走默认分支）" \
  || ng "C3 默认星期头不符: [$(sed -n 2p "$WORK/c1.txt")]"

echo "== D. monday-first（2） =="
if mencal -q -m -1 >"$WORK/d1.txt" 2>/dev/null; then ok "D1 -q -m -1 退出码 0"; else ng "D1 -q -m -1 退出码非 0"; fi
[ "$(sed -n 2p "$WORK/d1.txt")" = "Mo Tu We Th Fr Sa Su" ] \
  && ok "D2 monday-first 星期头 Mo Tu We Th Fr Sa Su" || ng "D2 monday-first 星期头不符"

echo "== E. 三月视图（2） =="
if mencal -q -3 >"$WORK/e1.txt" 2>/dev/null; then ok "E1 -q -3 退出码 0"; else ng "E1 -q -3 退出码非 0"; fi
case "$(sed -n 2p "$WORK/e1.txt")" in
  *"Su Mo Tu We Th Fr Sa   Su Mo Tu We Th Fr Sa   Su Mo Tu"*) ok "E2 三月并排三条星期头" ;;
  *) ng "E2 三月并排星期头不符" ;;
esac

echo "== F. 年视图（4） =="
if mencal -q -y 2026 >"$WORK/f1.txt" 2>/dev/null; then ok "F1 -q -y 2026 退出码 0"; else ng "F1 -q -y 2026 退出码非 0"; fi
grep -Fq "2026" "$WORK/f1.txt" && ok "F2 年视图含年份 2026" || ng "F2 年视图缺年份"
grep -Fq "January" "$WORK/f1.txt" && ok "F3 年视图含 January" || ng "F3 年视图缺 January"
grep -Fq "December" "$WORK/f1.txt" && ok "F4 年视图含 December" || ng "F4 年视图缺 December"

echo "== G. 确定性（1） =="
mencal -q -y 2026 >"$WORK/g1.txt" 2>/dev/null
mencal -q -y 2026 >"$WORK/g2.txt" 2>/dev/null
cmp -s "$WORK/g1.txt" "$WORK/g2.txt" && ok "G1 年视图两次运行输出逐字节一致" || ng "G1 年视图两次运行输出不一致"

echo "== H. 配置解析与经期日标记（3） =="
if mencal -n -c "n=alice,s=20260115,d=2,l=28,c=red" -y 2026 >"$WORK/h1.txt" 2>"$WORK/h1.err"; then
  ok "H1 带 -c 配置运行退出码 0"
else
  ng "H1 带 -c 配置运行退出码非 0"
fi
grep -Fq "Calendar for alice" "$WORK/h1.txt" && ok "H2 输出含配置名 Calendar for alice" || ng "H2 配置名标题缺失"
grep -Fq "**" "$WORK/h1.txt" && ok "H3 年视图含经期日标记 **（20260115 起 2 天）" || ng "H3 经期日标记缺失"

echo "== I. 配置文件落盘（7） =="
if mencal -q -c "n=bob,s=20260115,d=3,l=30,c=blue,f=$WORK/bob.rc" -y 2026 >/dev/null 2>/dev/null; then
  ok "I1 带 f= 保存配置运行退出码 0"
else
  ng "I1 带 f= 保存配置运行退出码非 0"
fi
[ -f "$WORK/bob.rc" ] && ok "I2 配置文件 bob.rc 已生成" || ng "I2 配置文件未生成"
grep -Fxq "start 20260115" "$WORK/bob.rc" && ok "I3 配置含 start 20260115" || ng "I3 start 行缺失"
grep -Fxq "name bob" "$WORK/bob.rc" && ok "I4 配置含 name bob" || ng "I4 name 行缺失"
grep -Fxq "color blue" "$WORK/bob.rc" && ok "I5 配置含 color blue" || ng "I5 color 行缺失"
grep -Fxq "length 30" "$WORK/bob.rc" && ok "I6 配置含 length 30" || ng "I6 length 行缺失"
grep -Fxq "duration 3" "$WORK/bob.rc" && ok "I7 配置含 duration 3" || ng "I7 duration 行缺失"

echo "== J. 错误路径（6） =="
if mencal -q -c "bogus=1" -1 >"$WORK/j1.txt" 2>/dev/null; then ok "J1 非法配置参数运行退出码 0（上游语义）"; else ng "J1 非法配置参数运行退出码非 0"; fi
grep -Fq "Invalid parameter 'bogus=1'" "$WORK/j1.txt" && ok "J2 输出非法参数告警" || ng "J2 非法参数告警缺失"
if mencal -q -c "n=x,d=0" -1 >"$WORK/j3.txt" 2>/dev/null; then ok "J3 duration=0 运行退出码 0"; else ng "J3 duration=0 运行退出码非 0"; fi
grep -Fq "Duration cannot be set to zero. Setting 4." "$WORK/j3.txt" \
  && ok "J4 输出 duration 钳制告警" || ng "J4 duration 钳制告警缺失"
if mencal -q /nonexistent/x >"$WORK/j5.txt" 2>/dev/null; then ok "J5 不可读文件运行退出码 0（上游语义）"; else ng "J5 不可读文件运行退出码非 0"; fi
grep -Fq "File /nonexistent/x is not readable" "$WORK/j5.txt" && ok "J6 输出文件不可读告警" || ng "J6 文件不可读告警缺失"

echo "== K. 端到端完整消费者用例：配置生成→落盘→重载→视图渲染→标记回读闭环（11） =="

# —— 步骤 1：生成经期配置并真实落盘（上游 -h：f,file=FILE filename to save configuration to）——
if mencal -n -c "n=carol,s=20260305,d=4,l=30,c=violet,f=$WORK/carol.rc" -y 2026 >"$WORK/k1.txt" 2>/dev/null; then
  ok "K1 配置生成并落盘运行退出码 0"
else
  ng "K1 配置生成并落盘运行退出码非 0"
fi
grep -Fq "Configuration for 'carol' saved to $WORK/carol.rc" "$WORK/k1.txt" \
  && ok "K2 stdout 含保存确认与真实落盘路径" || ng "K2 保存确认缺失"
[ -s "$WORK/carol.rc" ] && ok "K3 配置文件 carol.rc 非空（落盘产物实存）" || ng "K3 配置文件缺失或为空"
grep -Fxq "start 20260305" "$WORK/carol.rc" && ok "K4 落盘文件含 start 20260305（供下一步重载的真实输入）" || ng "K4 落盘 start 行缺失"

# —— 步骤 2：以上一步落盘的文件为输入重载并渲染年视图（上游 -h：位置参数 file1 file2 … = 配置文件）——
if mencal -n -y 2026 "$WORK/carol.rc" >"$WORK/k2.txt" 2>/dev/null; then
  ok "K5 用落盘配置文件重载渲染年视图退出码 0"
else
  ng "K5 重载渲染退出码非 0"
fi
grep -Fq "Calendar for carol" "$WORK/k2.txt" && ok "K6 年视图含 Calendar for carol（name 经文件闭环回读）" || ng "K6 name 未从文件回读"
grep -Fq "**" "$WORK/k2.txt" && ok "K7 年视图含经期日标记 **（start/duration 经文件闭环回读到渲染）" || ng "K7 经期日标记未回读"

# —— 步骤 3：同一落盘文件渲染三月视图（上游 -h：-3 previous, current and next month）——
if mencal -n -3 "$WORK/carol.rc" >"$WORK/k3.txt" 2>/dev/null; then
  ok "K8 用落盘配置文件渲染三月视图退出码 0"
else
  ng "K8 三月视图渲染退出码非 0"
fi
if [ -s "$WORK/k3.txt" ] && grep -Fq "Calendar for carol" "$WORK/k3.txt"; then
  ok "K9 三月视图非空且含 Calendar for carol（配置头在月视图回读）"
else
  ng "K9 三月视图产物为空或配置头缺失"
fi

# —— 步骤 4：内联同参数路径 vs 「落盘→重载」路径，产物必须逐字节一致（数据真传递的等价证明）——
mencal -n -c "n=carol,s=20260305,d=4,l=30,c=violet" -y 2026 >"$WORK/k4.txt" 2>/dev/null
cmp -s "$WORK/k2.txt" "$WORK/k4.txt" && ok "K10 落盘→重载路径与内联配置路径年视图逐字节一致" || ng "K10 两条路径年视图不一致"

# —— 末步：对全流程产物做真判定（非空 + 含配置名 + 含预期标记，缺一即 NG）——
if [ -s "$WORK/k2.txt" ] && grep -Fq "Calendar for carol" "$WORK/k2.txt" && grep -Fq "**" "$WORK/k2.txt"; then
  ok "K11 端到端全流程产物终判：重载年视图非空且同时含配置名与经期标记"
else
  ng "K11 端到端全流程产物终判失败"
fi

echo "[summary] mencal/3.0 test_package: PASS=$PASS FAIL=$FAIL（合计 $((PASS + FAIL)) 条断言）"
[ "$FAIL" -eq 0 ] || exit 1
echo "[summary] all assertions passed"
