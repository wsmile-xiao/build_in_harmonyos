#!/data/service/hnp/bin/bash
# test_package/test.sh -- sma 1.4 往返断言（消费者视角，真跑 PATH 上的已安装 sma）
#
# 被测面：CLI 选项、默认配置查找路径、-DUSE_REGEXP 的正则过滤路径、报告文本与计数。
# 不测面（本代码根本不触碰，故意不编造探针）：设备节点、/proc、/sys、socket、显示。
# 两条实测约束（B 机 2026-09-25）：
#   * sma 的 "opening file X" 一类提示全走 stderr => 报告比对只用 stdout；
#   * conan test() 里 getcwd 不可靠（`pwd` 返空、工作目录解析失败）且 /tmp 只读
#     => 工作目录一律取 ${TMPDIR:-$HOME/tmp}，绝不使用 $(pwd)。
#   * 默认 ASCII 报告的第 2 行是 "Generated at <asctime(当前时刻)> by SMA, version 1.4"
#     （ascii.c:52-59 取 time(2)+localtime，秒粒度；仅当配置项 HeaderText 置了 htchar 时
#      该行整体被替换掉）=> 凡"跨两次进程调用把 stdout 逐字节对比"的断言（A12/A22/A23）
#     都先经 hdr.conf 的 HeaderText 去掉时钟行，否则结果取决于两臂之间是否跨过一秒边界。
set -uo pipefail

BIN=sma
WORK="${TMPDIR:-$HOME/tmp}"
mkdir -p "$WORK" 2>/dev/null || WORK="$HOME"
TMPD="$WORK/_sma_tp.$$"
rm -rf "$TMPD"; mkdir -p "$TMPD" || { echo "FATAL: 无法建工作目录 $TMPD"; exit 1; }
cd "$TMPD" || exit 1

PASS=0
FAILN=0
ok()   { PASS=$((PASS+1)); echo "  [PASS] $*"; }
bad()  { FAILN=$((FAILN+1)); echo "  [FAIL] $*"; }
need() {  # need <描述> <固定串> <文件>
    if grep -Fq "$2" "$3" 2>/dev/null; then ok "$1"; else bad "$1 (缺串: $2)"; fi
}
needit() {  # needit <描述> <固定串> <文件>  -- 必须**不**出现
    if grep -Fq "$2" "$3" 2>/dev/null; then bad "$1 (不应出现: $2)"; else ok "$1"; fi
}

echo "[test] which $BIN -> $(command -v "$BIN" || echo MISSING)"
command -v "$BIN" >/dev/null 2>&1 || { echo "FATAL: sma not on PATH"; exit 1; }

# ---- 自造最小 sendmail 日志：2 个 envelope 发件人、2 个收件人、Sent 与 User unknown 各 1
cat > mail.log <<'EOF'
Oct 29 10:15:32 mailhost sendmail[12001]: b9T8FZa012001: from=<alice@example.com>, size=1024, class=0, nrcpts=1, msgid=<a1@mailhost>, proto=ESMTP, daemon=MTA, relay=client1.example.com[192.0.2.10]
Oct 29 10:16:33 mailhost sendmail[12002]: b9T8FZa012001: to=<bob@example.org>, delay=00:01, mailer=esmtp, pri=131072, relay=mx.example.org[198.51.100.7], dsn=2.0.0, stat=Sent (OK id=1Pz2Q3-0005Hv-QQ)
Oct 29 11:20:04 mailhost sendmail[12010]: b9T8K4b012010: from=<carol@example.com>, size=2048, class=0, nrcpts=1, msgid=<b4@mailhost>, proto=ESMTP, daemon=MTA, relay=client2.example.com[192.0.2.11]
Oct 29 11:21:05 mailhost sendmail[12011]: b9T8K4b012010: to=<dave@example.org>, delay=00:01, mailer=esmtp, pri=132048, relay=mx.example.org[198.51.100.7], dsn=5.1.1, stat=User unknown
EOF

cat > tp.conf <<'EOF'
Comment		"sma-testpackage-header"
EnvelopeSenderFilter		^alice@
EOF

# 三条"跨进程逐字节比对"的断言（A12/A22/A23）共用：HeaderText 让 ascii.c 打印固定抬头、
# 不再打印当前时刻那一行 => 两臂才存在逐字节可比的前提（判据本身一字未改）。
cat > hdr.conf <<'EOF'
HeaderText "sma-testpackage-fixed-header"
EOF

# A1..A4  -h：退出码 + 版本横幅 + 语法行 + -F 说明（上游 usage() 走 exit(0)）
"$BIN" -h > u.out 2>&1; rc=$?
[ "$rc" -eq 0 ] && ok "A1 -h rc=0" || bad "A1 -h rc=$rc"
need "A2 -h 打印版本横幅" "SMA version 1.4" u.out
need "A3 -h 含 usage 语法" "usage: sma [OPTIONS] [files...]" u.out
need "A4 -h 说明 -F 不读默认配置" "do not use default configuration file" u.out

# A5  -c 版权文案
"$BIN" -c </dev/null > c.out 2>&1
need "A5 -c 打印版权声明" "Jarkko Turkulainen" c.out

# A6..A9  默认 ASCII 报告：抬头 / 主机 / 发件人 / 收件人 逐字回读（stdout 与 stderr 分开存）
"$BIN" -f hdr.conf mail.log > r.out 2> r.err || { echo "FATAL: 分析日志失败"; cat r.err; exit 1; }
need "A6 默认抬头取 conf.h 的 COMMENT" "Sendmail Log Analysis Report" r.out
need "A7 从日志解析出主机名" "Server: mailhost" r.out
need "A8 envelope 发件人榜单含 alice" "alice@example.com" r.out
need "A9 envelope 收件人榜单含 dave" "dave@example.org" r.out

# A10 榜单计数：alice 只有 1 条 from= 记录 => 计数必须是 1（换日志这就会变红）
grep -E "^[[:space:]]*1[[:space:]]+alice@example\.com" r.out >/dev/null \
    && ok "A10 alice 计数=1" || bad "A10 alice 计数!=1"

# A11 -C 覆写抬头后默认抬头消失（证明 -C 真生效，而非两处并存）
"$BIN" -F -C "Custom-Report-Title" mail.log > c1.out 2>/dev/null
need "A11a -C 覆写抬头生效" "Custom-Report-Title" c1.out
needit "A11b -C 覆写后默认抬头消失" "Sendmail Log Analysis Report" c1.out

# A12 -o 写文件与 stdout 逐字节一致（本包唯一写路径就是 fopen(ochar,"w")）
"$BIN" -f hdr.conf -o f.out mail.log >/dev/null 2>&1
if [ -s f.out ] && cmp -s f.out r.out; then ok "A12 -o 文件与 stdout 逐字节一致"; else bad "A12 -o 输出与 stdout 不一致"; fi

# A13 -p 打印生效配置（stdin 一律关闭，防上游把 -p 之后继续读 stdin）
"$BIN" -p -F </dev/null > p.out 2>&1
need "A13 -p 打印配置表" "PrintGeneralInfo yes" p.out

# A14/A15 默认配置查找路径 = conf.h 的 DEFAULT_CONF（相对当前目录的 ./sma.conf）
"$BIN" -p </dev/null > nconf.out 2> nconf.err
grep -Fq "cannot open configuration file, using defaults" nconf.err \
    && ok "A14 缺 ./sma.conf 时回落默认值并留痕" || bad "A14 缺默认配置提示"
"$BIN" -p -F </dev/null > /dev/null 2> Fconf.err
needit "A15 -F 时完全不查默认配置" "cannot open configuration file" Fconf.err

# A16 -f 显式指定文件时错误文案逐字回显路径
"$BIN" -F -f ./nope.conf mail.log > /dev/null 2> f16.err
need "A16 -f 缺文件时回显原样路径" "cannot open ./nope.conf" f16.err

# A17..A19 -DUSE_REGEXP 那条正则路径真被走到：^ 锚点是子串匹配做不到的
"$BIN" -f tp.conf mail.log > rx.out 2>/dev/null
need "A17a 配置文件里的 Comment 生效" "sma-testpackage-header" rx.out
need "A17b 榜单抬头回显正则过滤器" "(filter: ^alice@)" rx.out
need "A18 正则命中的发件人在榜" "alice@example.com" rx.out
needit "A19 未被正则命中的发件人不在榜" "carol@example.com" rx.out

# A20 非法输出格式：上游 exit(1)
"$BIN" -F -O bogus mail.log > /dev/null 2> o20.err; rc=$?
if [ "$rc" -ne 0 ] && grep -Fq "illegal output format" o20.err; then
    ok "A20 -O 非法格式 rc=$rc + 文案"; else bad "A20 -O 非法格式 rc=$rc"; fi

# A21 日志文件打不开：文案带原样路径，且上游以 rc=1 退出（实测，不是静默）
"$BIN" -F /definitely/not/here.log > a21.out 2> a21.err; rc=$?
if [ "$rc" -eq 1 ] && grep -Fq "cannot open /definitely/not/here.log" a21.err; then
    ok "A21 缺日志文件 rc=1 + 路径文案"; else bad "A21 缺日志文件 rc=$rc"; fi

# A22 stdin 通道（不给文件参数时读 stdin）与文件通道逐字节同结果
# 三条 [diag] 只打印、不判定（合计判定点仍是 25）：红的时候先给 CWD / 输入哈希 / 环境
echo "[diag] TMPD=$TMPD pwd=[$(pwd 2>/dev/null)] pwdP=[$(pwd -P 2>/dev/null)]"
echo "[diag] mail.log sha256=$(sha256sum mail.log 2>/dev/null | cut -d' ' -f1)"
echo "[diag] TZ=${TZ:-unset} LANG=${LANG:-unset} LC_ALL=${LC_ALL:-unset} TMPDIR=${TMPDIR:-unset}"
"$BIN" -f hdr.conf < mail.log > s22.out 2>/dev/null
if cmp -s s22.out r.out; then ok "A22 stdin 与文件通道逐字节一致"
else bad "A22 stdin 通道结果不同"; diff r.out s22.out | head -12; fi

# A23 可证伪性自检：同一份二进制换日志 => 报告必须变化
sed 's/carol@example\.com/frank@example\.net/' mail.log > mail2.log
"$BIN" -f hdr.conf mail2.log > a23.out 2>/dev/null
if ! cmp -s a23.out r.out && grep -Fq "frank@example.net" a23.out; then
    ok "A23 换日志后报告变化（断言可证伪）"; else bad "A23 换日志报告未变化"; fi

echo "[test] 断言通过 $PASS 项，失败 $FAILN 项（合计 25 个判定点）"
cd "$HOME" 2>/dev/null || cd / || exit 1
rm -rf "$TMPD"
[ "$FAILN" -eq 0 ] || exit 1
echo "[test] all OK"
