#!/bin/sh
# test.sh — iroffer 1.4.b03 消费者测试（R34/PF3/L0c/L0e）
#
# 16 条断言，逐条实测于 B 机（HarmonyOS PC / clang 15.0.4 / aarch64）对**包目录产物**的读数：
#   iroffer 走 5 条确定性命令行分支（版本 / 缺配置 / 未知选项 / 配置不完整）
#   convertxdccfile 走一次**真实的数据往返**（.xdcc → .state），并**按上游写 state 的那段
#   代码逐字节校验**产物头部（magic / 格式版本 / 版本条目的 tag + length / 版本串所在偏移）
#   ——这是本包最有分量的功能证据，不是打印字符串的空壳。
#
# ⚠ 断言 13、14 的**形态**在 2026-09-27 改过，原因不是判据错了，而是判据曾经借道 grep：
#   旧形态是 `grep -a -q "iroffer v1\.4\.b03" conv.state`。实测同一枚二进制产出的同一份
#   252 B 产物上（本机读数见 notes.md「CI 复现与断言形态整改」节）：
#     GNU grep 3.12（/data/service/hnp/bin/grep） -a -q  ⇒ rc=0（命中）
#     toybox 0.8.12（/usr/bin、/system/bin、/bin 的 grep） -a -q ⇒ rc=1（不命中，且不报错）
#   ⇒ 旧断言把结论押在"PATH 上恰好是 GNU grep 且 -a 认二进制文件"这一**环境属性**上：
#     本地 W3 的 PATH 含 /data/service/hnp/bin 所以 16/16，CI worker 的 test 阶段（VirtualRunEnv
#     只带包目录进 PATH，profile 的 hnp 路径挂在 [buildenv]）落到 toybox grep，于是第 14 条红。
#   新形态只用 `od -An -tx1/-tu1`（读文本列，两侧输出一致）与 `head -c | tail -c`（纯文本切片），
#   **不再对二进制文件用 grep**，判据本身仍与上游源码逐行对应（见下 12-14 段引用行号）。
#
# 有意排除的一条：`iroffer -c`（口令加密生成分支）。它经 getpass 类例程读口令，
#   实测退出码随有无控制终端而变：有 tty 时 1、无 tty（管道或 </dev/null）时阻塞到
#   timeout 124。既然不可复现就不写进断言（放宽成"1 或 124"等于没断言）。
#
# 计数口径：N_ASSERT=16；任何一条不命中即 FAIL 并退出非 0；最后核 PASS 数 == N_ASSERT。

: "${IROFFER_BIN:?IROFFER_BIN not set}"
: "${CONVERTXDCCFILE_BIN:?CONVERTXDCCFILE_BIN not set}"

N_PASS=0
N_ASSERT=16

fail() {
    echo "FAIL: $1" >&2
    if [ -n "$2" ] && [ -f "$2" ]; then
        echo "---- 实际输出 ----" >&2
        sed -n '1,14p' "$2" >&2
    fi
    exit 1
}

ok() {
    N_PASS=$((N_PASS + 1))
    echo "PASS[$N_PASS]: $1"
}

chk_rc() {  # $1=实际rc $2=期望rc $3=说明 $4=可选日志文件
    [ "$1" -eq "$2" ] || fail "$3：退出码 $1，期望 $2" "$4"
}

# 工作目录：$TMPDIR 或 $HOME/tmp（鸿蒙 /tmp 只读，E002）
WORK="${TMPDIR:-$HOME/tmp}/iroffer-test-$$"
mkdir -p "$WORK" || fail "无法创建工作目录 $WORK" ""
cd "$WORK" || fail "无法进入工作目录 $WORK" ""

# ---------- 1-2) iroffer -v：版本分支 ----------
"$IROFFER_BIN" -v > v.txt 2>&1; RC=$?
chk_rc "$RC" 0 "iroffer -v 退出码"
ok "iroffer -v 退出码 0"
grep -q "iroffer v1\.4\.b03" v.txt || fail "iroffer -v 未报告版本串 1.4.b03" "v.txt"
ok "iroffer -v 输出含 \"iroffer v1.4.b03\"（版本串逐字，非 1.4b03 / 1.4.03）"

# ---------- 3-4) iroffer 无参：参数校验分支 ----------
"$IROFFER_BIN" > na.txt 2>&1; RC=$?
chk_rc "$RC" 0 "iroffer 无参退出码"
ok "iroffer 无参退出码 0（上游即如此，不视为错误）"
grep -q "no configuration file specif" na.txt || fail "iroffer 无参未走缺配置分支" "na.txt"
ok "iroffer 无参输出含 \"no configuration file specifed\"（上游原拼写，不做拼写纠正）"

# ---------- 5-6) iroffer -h：未识别选项分支 ----------
"$IROFFER_BIN" -h > h.txt 2>&1; RC=$?
chk_rc "$RC" 0 "iroffer -h 退出码"
ok "iroffer -h 退出码 0（上游把未知选项只当告警）"
grep -q "unrecognized option" h.txt || fail "iroffer -h 未走未知选项分支" "h.txt"
ok "iroffer -h 输出含 \"unrecognized option\"（argv 解析代码确被执行）"

# ---------- 7-9) iroffer -d -n -s cfg：读配置 → 完整性校验 ----------
printf 'admin_nick = testadmin\n' > min.cfg
timeout 25 "$IROFFER_BIN" -d -n -s min.cfg > cfg.txt 2>&1; RC=$?
chk_rc "$RC" 1 "iroffer 配置不完整时退出码" ""
ok "iroffer -d -n -s 不完整配置 退出码 1"
grep -q "Starting up" cfg.txt || fail "iroffer 未进入启动流程" "cfg.txt"
ok "其输出含 \"Starting up\"（启动序列被执行，非提前退出）"
grep -q "Config File Missing" cfg.txt || fail "iroffer 未做配置完整性校验" "cfg.txt"
ok "其输出含 \"Config File Missing\"（配置解析器真的拒绝了不完整配置）"

# ---------- 10-11) convertxdccfile 无参：第二个交付二进制 ----------
"$CONVERTXDCCFILE_BIN" > cv.txt 2>&1; RC=$?
chk_rc "$RC" 1 "convertxdccfile 无参退出码"
ok "convertxdccfile 无参退出码 1"
grep -q "Usage:" cv.txt || fail "convertxdccfile 无参未打 usage" "cv.txt"
ok "convertxdccfile 输出含 \"Usage:\"（第二个二进制可执行且自带参数校验）"

# ---------- 12-14) convertxdccfile 真实数据往返：.xdcc → .state ----------
: > empty.xdcc
timeout 25 "$CONVERTXDCCFILE_BIN" -x empty.xdcc -s conv.state > conv.txt 2>&1; RC=$?
chk_rc "$RC" 0 "convertxdccfile 空表转换退出码" "conv.txt"
ok "convertxdccfile -x empty.xdcc -s conv.state 退出码 0（完成一次真实转换）"
[ -s conv.state ] || fail "未生成 .state 产物" "conv.txt"

# 上游写 state 的落点与字节形态（src/iroffer_statefile.c，逐行对应）：
#   :93   #define STATEFILE_MAGIC (('I'<<24)|('R'<<16)|('F'<<8)|'R')
#   :94   #define STATEFILE_VERSION 1
#   :49   STATEFILE_TAG_IROFFER_VERSION = 1 << 8
#   :223-224  ir_uint32 magic = htonl(STATEFILE_MAGIC); ir_boutput_write(...)   → off 0..3
#   :233-234  ir_uint32 version = htonl(STATEFILE_VERSION); ...                 → off 4..7
#   :246-253  data = mycalloc(sizeof(statefile_hdr_t) + maxtextlength);
#             hdr->tag = STATEFILE_TAG_IROFFER_VERSION; hdr->length = sizeof(*hdr);
#   :256-257  length = snprintf(next, maxtextlength-1,
#                               "iroffer v" VERSIONLONG ", %s", gdata.osstring);
#   :266-267  hdr->length += ceiling(length+1, 4); write_statefile_item(&bout, data);
#   ⇒ 版本条目是紧跟头部 8 字节的**第一个**条目：off 8..11 = tag、off 12..15 = 条目长度
#     （htonl，含头 8 字节且 4 对齐）、off 16 起 = "iroffer v" VERSIONLONG ", <osstring>"。
#     写入无条件，唯一的跳过分支是 :259 的 `length < 0 || length >= maxtextlength(512)`
#     （:127-128 iroffer_defines.h），触发时 :261 必打 "Version too long!" 告警。
#   VERSIONLONG 由 Configure 生成（Configure:8 VERSION=1.4.b03、:21 VERSIONLONG="$VERSION
#   [$CSET]"、:120 写入 src/iroffer_config.h）⇒ 无论 $CSET 取 .cset_number 还是 "Unknown"，
#   off 16 起的 18 个字节恒为 "iroffer v1.4.b03 ["。
#   尾部 ", %s" 的 gdata.osstring 在本工具里是 NULL（convertxdccfile.c:252 只 memset 过 gdata，
#   唯一赋值点是 iroffer_utilities.c:186-188 的 uname 分支，convertxdccfile 不调用它），
#   打印形态由 libc 决定 ⇒ **该校验位刻意停在偏移 16..33**，不碰这条环境相关的尾巴。
HDR8=$(od -An -tx1 -N 8 conv.state 2>/dev/null | tr -d ' \n')
[ "$HDR8" = "4952465200000001" ] \
    || fail ".state 头 8 字节不是上游 magic \"IRFR\" + htonl(STATEFILE_VERSION=1)（实测 ${HDR8:-读空}，期望 4952465200000001）" "conv.txt"
ok ".state 头 8 字节逐字节 = \"IRFR\" + htonl(STATEFILE_VERSION=1)（iroffer_statefile.c:93-94/223-234）"

TAG4=$(od -An -tx1 -j 8 -N 4 conv.state 2>/dev/null | tr -d ' \n')
LEN3=$(od -An -tx1 -j 12 -N 3 conv.state 2>/dev/null | tr -d ' \n')
ITEMLEN=$(od -An -tu1 -j 15 -N 1 conv.state 2>/dev/null | tr -d ' \n')
VER18=$(head -c 34 conv.state 2>/dev/null | tail -c 18)
[ "$TAG4" = "00000100" ] \
    && [ "$LEN3" = "000000" ] \
    && [ -n "$ITEMLEN" ] \
    && [ "$ITEMLEN" -ge 28 ] \
    && [ "$ITEMLEN" -le 252 ] \
    && [ $((ITEMLEN % 4)) -eq 0 ] \
    || fail ".state 版本条目的头不合规（tag=${TAG4:-读空} 期望 00000100；长度高 3 字节=${LEN3:-读空} 期望 000000；长度低字节=${ITEMLEN:-读空} 期望 28..252 且为 4 的倍数，即 8+ceiling(len+1,4)）" "conv.txt"
[ "$VER18" = "iroffer v1.4.b03 [" ] \
    || fail ".state 偏移 16 起不是上游写入的版本串前缀（实测 ${VER18:-读空}，期望 \"iroffer v1.4.b03 [\"）" "conv.txt"
ok ".state 版本条目 tag/长度合规（len=${ITEMLEN}）且偏移 16 起逐字节为 \"iroffer v1.4.b03 [\"（iroffer_statefile.c:256-257 + Configure:8/21；判据不依赖 grep 对二进制文件的处理方式）"

# ---------- 15-16) convertxdccfile 语法错误路径 ----------
# 上游 .xdcc 的第一行是 "server port nick" 三元组，其后才是 offer 行；
# 只给一行 offer 会被当成"首行无效→全部归零"并**成功产出空表**（实测 rc=0），
# 所以这里必须用两行（首行三元组有效、第二行残缺）才走得到 syntax error 分支。
printf '192.168.1.1 6667 testnick\n1: test file /tmp/f 10 50\n' > bad.xdcc
timeout 25 "$CONVERTXDCCFILE_BIN" -x bad.xdcc -s bad.state > bad.txt 2>&1; RC=$?
chk_rc "$RC" 1 "convertxdccfile 坏输入退出码" "bad.txt"
ok "convertxdccfile 对语法错误的 .xdcc 返回退出码 1"
grep -q "syntax error" bad.txt || fail "convertxdccfile 未报语法错误" "bad.txt"
ok "其输出含 \"syntax error\"（解析器的失败分支被执行）"

cd "$HOME" || exit 1
rm -rf "$WORK" 2>/dev/null

echo "PASS ${N_PASS}/${N_ASSERT}"
[ "$N_PASS" -eq "$N_ASSERT" ] || fail "断言数 ${N_PASS} != 声明的 ${N_ASSERT}" ""
exit 0
