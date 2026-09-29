#!/usr/bin/env bash
# -*- coding: utf-8 -*-
# 翻译面 + 端到端消费者测试（pgpgpg 0.13 / HarmonyOS PC）
#
# argv: $1 = 打包后的 pgpgpg 绝对路径（R34），$2 = 依赖 gnupg 提供的 gpg 绝对路径。
#
# 为什么分 T / E 两组（一手读数全部由本脚本打印）：
#   * pgpgpg 的全部功能就是"把 PGP 2.6 风格选项翻译成 gpg 参数再 execv"。T 组只要求
#     "产物能被 exec 起来 + 被 exec 的 gpg 能读 stdin"，不依赖密钥、agent、网络，
#     因此任何机器上都必须成立。
#   * T 组的 argv 记录接缝取自内核侧的 /proc/<pid>/cmdline：pgpgpg 在 main.c:147
#     fork 后 execv(GPG_PATH, gpg_argv)；把它的 stdin 接到一根 held 管道（sleep 占住
#     写端、不写数据），被 exec 的 gpg 就阻塞在 read() 上，此时读该子进程的 cmdline
#     拿到的就是 execve 实际传入的 argv。这比"让产物打印自己的 argv"更硬，也不要求
#     为测试改构建配置（上游只有 --enable-debug 才打印，本包不采用）。
#   * 私钥腿（keygen / 解密 / 带有效收件人的加密）要 gpg-agent 绑 AF_UNIX socket，
#     而且**只有收件人能在本地 pubring 解析开之后**，gpg 才会去打开明文 —— 这一条同时
#     决定了"多收件人的 argv 断言只能放在 E 组"（见下方 t07 位置的说明）。
#     设备侧取证已定性：/storage/Users/**（hmdfs）对路径型 socket inode 与 mkfifo
#     一律 EPERM，/data/storage/el*/base/**（hmfs）可用。⇒ E 组按候选根逐个探测，
#     全部不可用时**逐条显式 SKIP 并打印原因原文**，不静默、不并入 pass 数。
#   * 产物一律写到分址 $OUT（绝对路径、按 pid 唯一），正反两轮不复用同一份文件
#     （框架 L1e 会移走包产物后再对同一 test_package 起第二次 conan test）。
#
# 第 4 棒（本轮整改）动过的两处，口径先写在这里：
#   1) 采集块不再"空臂套壳"：t06 / e4 两块的本职是"跑一次命令、把 rc 与 stderr 备好"，
#      整改前它们的断言写在壳外（ck_rc 自开一个臂），于是壳内 0 条读数被 arm_end 的
#      "逐臂必须有读数"自检判成 <arm>/accounting FAIL —— 那是脚手架自己跟自己打架。
#      现在把 ck_rc 调进壳内，同一臂里既有采集也有真断言（断"采到的 rc = 期望值"），
#      arm_end 的判据一个字没放宽。
#   2) 多收件人（原 T 组 t07）的证据通道换掉：整改前拿 gpg 的 stderr 回显当"每个收件人
#      都被转发"的证据。B 机实拍本机 dirmngr 不存在（`error running '/bin/dirmngr':
#      probably not installed`），绕开 pgpgpg 直调 gpg 传两个收件人时 gpg 只对**末位**
#      回显（count_a=0 / count_b=2）⇒ 这条通道无论 pgpgpg 对不对都不可信。现在用本脚本
#      已有的 /proc execve argv 采集通道断"两条 --recipient 都在 argv 里、且顺序与命令行
#      一致"，环境无关，并正面覆盖"pgpgpg 有没有丢收件人"。
# pipefail: :352/:535/:569 三处管道必须整体判失败（W4 P2）
set -euo pipefail

PGP="${1:-}"
GPG_BIN="${2:-}"
if [ -z "$PGP" ] || [ ! -x "$PGP" ]; then
    echo "pgpgpg binary not found: $PGP" >&2
    exit 127
fi
if [ -z "$GPG_BIN" ] || [ ! -x "$GPG_BIN" ]; then
    echo "gpg binary not found: $GPG_BIN" >&2
    exit 127
fi

GPG_DIR=$(dirname "$GPG_BIN")
GPG_AGENT_BIN="$GPG_DIR/gpg-agent"
GPG_CONNECT_BIN="$GPG_DIR/gpg-connect-agent"
export PATH="$GPG_DIR:$PATH"

HOLD=4                 # 每次记录把 stdin / 输入管道 held 住的秒数
SCAN_TRIES=30          # /proc 采样轮数上限
TAGP="pgpgpg-r3-$$"    # 本轮唯一标记：只采自己的子进程、只写自己的目录

# --- 工作目录与 GNUPGHOME 候选根：env 变量优先，不硬编码单一 el1/el2 -----------
cands=""
[ -n "${PGPGPG_E2E_ROOT:-}" ] && cands="$cands $PGPGPG_E2E_ROOT"
[ -n "${TMPDIR:-}" ] && cands="$cands ${TMPDIR%/}"
cands="$cands /data/storage/el2/base/cache /data/storage/el1/base/cache /data/storage/el2/base /data/storage/el1/base $HOME/tmp"

WORK=""
for b in $cands; do
    if mkdir -p "$b/$TAGP/out" 2>/dev/null && [ -w "$b/$TAGP/out" ]; then
        WORK="$b/$TAGP"
        break
    fi
done
if [ -z "$WORK" ]; then
    echo "FATAL: 所有候选根都无法创建工作目录（候选：$cands）" >&2
    exit 1
fi
OUT="$WORK/out"
EVID="$WORK/evidence"
mkdir -p "$EVID"
# T 组也要有自己的 GNUPGHOME：否则 gpg 会在运行账号家根造出 .gnupg（家根禁止落新散文件）
mkdir -p "$WORK/homet"
printf 'agent-program %s\n' "$GPG_AGENT_BIN" >"$WORK/homet/gpg.conf"
TGNUPGHOME="$WORK/homet"

# E 组（GNUPGHOME 与它上面的 fifo）的候选根 = cands 去掉 $HOME/tmp：hmdfs 族上私钥运算
# 根本跑不起来（bind AF_UNIX / mkfifo 一律 EPERM），拿它当落点只会产出一堆 SKIP。
# ⇒ 端到端腿只允许落在 hmfs base 一类（/data/storage/el1|el2/base/**）并被下方真 keygen 复核。
ecands=""
for b in $cands; do
    [ "$b" = "${HOME%/}/tmp" ] && continue
    ecands="$ecands $b"
done

# --- 计数器：discovered / passed / failed / skipped 全部由实际产出累加 ---------
PS=0
FS=0
SS=0
ARM_OUT=0
ARM_LEDGER=""
ARM_NAME=""
RECORDS=""

_note() { ARM_LEDGER="$ARM_LEDGER$1 $2
"; }

ok() {
    PS=$((PS + 1)); ARM_OUT=$((ARM_OUT + 1)); _note "$ARM_NAME/$1" PASS
    echo "ASSERT ok   : $1"
    [ -n "${2:-}" ] && echo "            -> $2"
    return 0
}

bad() {
    FS=$((FS + 1)); ARM_OUT=$((ARM_OUT + 1)); _note "$ARM_NAME/$1" FAIL
    echo "ASSERT FAIL : $1"
    [ -n "${2:-}" ] && echo "            -> $2"
    return 0
}

skip() {
    SS=$((SS + 1)); ARM_OUT=$((ARM_OUT + 1)); _note "$ARM_NAME/$1" SKIP
    echo "SKIP: $1 -- $2"
    return 0
}

arm_begin() { ARM_NAME="$1"; ARM_OUT=0; echo "== arm $ARM_NAME"; }

# 抓"某臂一条断言都没产出"的静默丢失。判据不放宽：套了 arm_begin 就必须有读数，
# 只出"备料"（跑命令、存 rc / stderr）的采集块一律不许套壳 —— 它的断言在 ck_* 里。
arm_end() {
    if [ "$ARM_OUT" -eq 0 ]; then
        bad accounting "该臂未产出任何断言读数（账本要求逐臂可核）"
    fi
    return 0
}

show() { [ -f "$1" ] && sed -e 's/^/            | /' "$1" | head -12; return 0; }

ck_rc() { # $1=断言id $2=期望 rc $3=实际 rc $4=说明
    # 注意：本函数**不自开臂**（第 4 棒整改）—— 它只在采集块已开的臂里补一条真断言，
    # 自己再开一个同名臂会让采集臂变成"零读数"、被 arm_end 判成 accounting FAIL。
    if [ "$2" = "$3" ]; then
        ok "$1" "$4：rc=$3（预期 $2）"
    else
        bad "$1" "$4：rc=$3（预期 $2）"
    fi
}

ck_has() { # $1=断言id $2=文件 $3=定串 [$4=上游读数缺失时的 SKIP 原因]
    arm_begin "$1"
    if [ "$#" -ge 4 ] && [ ! -s "$2" ]; then
        skip "$1" "$4"
    elif [ -s "$2" ] && LC_ALL=C grep -a -F -- "$3" "$2" >/dev/null 2>&1; then
        ok "$1" "$2 里记录了 [$3]"
    else
        bad "$1" "$2 中未找到 [$3]，该文件原文："
        show "$2"
    fi
    arm_end
}

ck_not() { # $1=断言id $2=文件 $3=不该出现的定串
    arm_begin "$1"
    if [ ! -f "$2" ]; then
        bad "$1" "$2 不存在，无从判定"
    elif LC_ALL=C grep -a -F -- "$3" "$2" >/dev/null 2>&1; then
        bad "$1" "$2 里出现了不该出现的 [$3]"
    else
        ok "$1" "确认 $2 中没有 [$3]"
    fi
    arm_end
}

# --- argv 记录器：record <tag> <pgpgpg 选项...> --------------------------------
# 先用 /proc/<pid>/comm 做零 fork 预筛（bash 内建），命中 gpg 才 tr 一次 cmdline，
# 否则每个 /proc 条目 fork 一次 tr 会把整轮采样拖到分钟级（本仓实测）。
scan_for() { # $1=tag  命中则把空格分隔的 argv 打到 stdout
    tag="$1"
    n=0
    while [ "$n" -lt "$SCAN_TRIES" ]; do
        n=$((n + 1))
        for d in /proc/[0-9]*; do
            cm=$(<"$d/comm") 2>/dev/null || continue
            [ "$cm" = "gpg" ] || continue
            cl=$(tr '\0' ' ' <"$d/cmdline" 2>/dev/null)
            case "$cl" in
                "$GPG_BIN "*"$tag"*) printf '%s' "$cl"; return 0 ;;
            esac
        done
        sleep 0.05 2>/dev/null || true  # 预热等待，超时无害
    done
    return 1
}

record() {
    tag="$1"
    shift
    rec="$EVID/argv.$tag"
    : >"$rec"
    GNUPGHOME="$TGNUPGHOME" "$PGP" "$@" < <(sleep "$HOLD") >"$EVID/stdout.$tag" 2>"$EVID/stderr.$tag" &
    job=$!
    scan_for "$tag" >"$rec" 2>/dev/null || true  # 后台采集失败只丢本轮读数，由 arm_end 的逐臂自检判 FAIL（不静默）
    wait "$job" 2>/dev/null || true  # 收后台任务，未起/已退都不影响断言
    line="$tag="
    if [ -s "$rec" ]; then
        line="$line$(cat "$rec")"
    else
        line="$line<未采到>"
    fi
    RECORDS="$RECORDS$line
"
    return 0
}

# E 组的断言 id 清单：环境不可用时按此清单逐条 SKIP，保证两条路径条数同源
E_IDS="e1_capable_root e2_keygen e3_ownertrust e4_armor_rc e4_armor_header e5_recorded e5_argv_encrypt e5_argv_recipient e5_argv_armor e6_armor_roundtrip e7_binary_roundtrip e8_recorded e8_argv_recipient_a e8_argv_recipient_b e8_argv_order"

skip_group() {
    for i in $E_IDS; do
        arm_begin "$i"
        skip "$i" "$1"
        arm_end
    done
}

echo "PGP=$PGP"
echo "GPG=$GPG_BIN"
echo "WORK=$WORK"
echo "OUT=$OUT"
echo "CANDIDATES=$cands"
echo "E_CANDIDATES=$ecands"

# =============================================================================
# T 组：PGP 2.6 选项 -> gpg 命令行的翻译面（必跑，不需要 agent / 密钥 / 网络）
# =============================================================================

# t01 产物里烧入的 GPG_PATH 必须是依赖提供的那个绝对路径（execv 不搜 PATH）
arm_begin t01_baked_gpg_path
if LC_ALL=C grep -a -F -- "$GPG_BIN" "$PGP" >/dev/null 2>&1; then
    ok baked_gpg_path "产物内烧入的 GPG_PATH = $GPG_BIN"
else
    bad baked_gpg_path "产物 $PGP 内未找到烧入路径 [$GPG_BIN]"
fi
arm_end

# t02 -a 单用 -> --armor --store，并核对 -o / --set-filename / --no-batch
record t02 -a -o "$OUT/t02.asc"
arm_begin t02_recorded
if [ -s "$EVID/argv.t02" ]; then
    ok recorded "采到 execve argv：$(cat "$EVID/argv.t02")"
else
    bad recorded "未能从 /proc 采到被 exec 的 gpg argv；pgpgpg stderr："
    show "$EVID/stderr.t02"
fi
arm_end
ck_has t02_argv0 "$EVID/argv.t02" "$GPG_BIN "
ck_has t02_armor "$EVID/argv.t02" "--armor"
ck_has t02_store "$EVID/argv.t02" "--store"
ck_has t02_output "$EVID/argv.t02" "--output $OUT/t02.asc"
ck_has t02_setfilename "$EVID/argv.t02" "--set-filename stdin"
ck_has t02_nobatch "$EVID/argv.t02" "--no-batch"
ck_not t02_no_encrypt "$EVID/argv.t02" "--encrypt"
ck_not t02_no_symmetric "$EVID/argv.t02" "--symmetric"

# t05 不给 -o 时的输出名推导（build_output：输入名 + .asc）
PLAIN="$WORK/plain.txt"
printf 'pgpgpg round-trip payload\nline two\n' >"$PLAIN"
arm_begin t05_default_output_name
rc5=0
GNUPGHOME="$TGNUPGHOME" "$PGP" -a "$PLAIN" >"$EVID/t05.out" 2>"$EVID/t05.err" || rc5=$?
if [ -s "$PLAIN.asc" ]; then
    ok default_output_name "无 -o 时产物落在 $(basename "$PLAIN").asc（$(wc -c <"$PLAIN.asc") 字节，pgpgpg rc=$rc5）"
else
    bad default_output_name "未生成 $PLAIN.asc（pgpgpg rc=$rc5）；stderr："
    show "$EVID/t05.err"
fi
arm_end
ck_has t05_armor_header "$PLAIN.asc" "-----BEGIN PGP MESSAGE-----"

# t06 -e 的操作数映射与 PGP 退出码映射（收件人无公钥 ⇒ 不需要 agent）
arm_begin t06_encrypt_call
rc6=0
GNUPGHOME="$TGNUPGHOME" "$PGP" -e -o "$OUT/t06.bin" "$PLAIN" "z44nosuch+t06@example.invalid" >"$EVID/t06.out" 2>"$EVID/t06.err" || rc6=$?
echo "            -> 本轮 gpg stderr 原文："
show "$EVID/t06.err"
ck_rc t06_pgprc 11 "$rc6" "找不到收件人公钥时的 PGP 退出码（main.c 的 WEXITSTATUS 映射：gpg rc=2 => PGPERR_KEY_NOT_EXIST=11）"
arm_end
ck_has t06_recipient_slot "$EVID/t06.err" "z44nosuch+t06@example.invalid"
ck_has t06_input_slot "$EVID/t06.err" "$PLAIN"

# t07 多收件人：整改前的这条断言拿 gpg 的 stderr 回显当"operands[1..] 都被转发"的证据，
#     实测通道不可信（本机无 dirmngr，直调 gpg 传两收件人时 gpg 只回显末位：
#     count_z44a=0 / count_z44b=2）⇒ 与 pgpgpg 是否正确无关，无论跑几轮都只能得 FAIL。
#     T 组无法改采 argv：pgpgpg 把输入文件路径原样交给 gpg，gpg 只在**收件人可本地解析**
#     之后才去打开明文，明文一打开就立刻 rc=2 退出 ⇒ 没有窗口让 /proc 采到 execve 的 argv。
#     所以多收件人的正面覆盖挪到 E 组的 e8（有真密钥 ⇒ gpg 会阻塞在 fifo 明文上）。

# t08 -d 与 -d -f 的互斥差分（上游只在带 -f 时译出 --decrypt）
JUNK="$WORK/junk.pgp"
printf 'not openpgp data at all\n' >"$JUNK"
GNUPGHOME="$TGNUPGHOME" "$PGP" -d -o "$OUT/t08a.out" "$JUNK" >"$EVID/t08a.out" 2>"$EVID/t08a.err" || true  # 期望失败：t08 是垃圾数据解密差分，断言只比两侧 stderr，rc 不入账
GNUPGHOME="$TGNUPGHOME" "$PGP" -d -f -o "$OUT/t08b.out" "$JUNK" >"$EVID/t08b.out" 2>"$EVID/t08b.err" || true  # 期望失败：同上，带 -f 臂同样只比 stderr
arm_begin t08_decrypt_differential
echo "            -> 裸 -d 的 gpg stderr："
show "$EVID/t08a.err"
echo "            -> -d -f 的 gpg stderr："
show "$EVID/t08b.err"
if LC_ALL=C grep -a -F -- "no command supplied" "$EVID/t08a.err" >/dev/null 2>&1 &&
   LC_ALL=C grep -a -F -- "decrypt_message failed" "$EVID/t08b.err" >/dev/null 2>&1; then
    ok decrypt_differential "裸 -d 未译出命令（gpg 自行猜），-d -f 则显式 --decrypt ⇒ 差分成立"
else
    bad decrypt_differential "两条 stderr 的差分与上游读码不符（见上方原文）"
fi
arm_end
ck_not t08_nocmd_on_bare "$EVID/t08a.err" "decrypt_message failed"

# =============================================================================
# E 组：真端到端（keygen -> 置信任 -> pgpgpg -e -> pgpgpg -d -> 明文逐字节回比）
# =============================================================================
GHOME=""
TRIED="（未进入候选根探测）"
if [ ! -x "$GPG_AGENT_BIN" ]; then
    skip_group "依赖包里没有可执行的 gpg-agent：$GPG_AGENT_BIN"
else
    for root in $ecands; do
        h="$root/$TAGP.home"
        rm -rf "$h" 2>/dev/null || true  # 清理失败无害（下次同名目录由 mktemp 类分址接管）
        if ! mkdir -p "$h" 2>/dev/null; then
            TRIED="$TRIED | ${root}: mkdir 失败"
            continue
        fi
        printf 'agent-program %s\n' "$GPG_AGENT_BIN" >"$h/gpg.conf"
        cat >"$h/keygen" <<KEYGENEOF
%echo pgpgpg-e2e-keygen
Key-Type: RSA
Key-Length: 2048
Name-Real: pgpgpg e2e
Name-Comment: temporary
Name-Email: pgpgpg-e2e@example.invalid
Expire-Date: 0
%no-protection
%commit
%echo pgpgpg-e2e-keygen-done
KEYGENEOF
        klog="$EVID/keygen.$(basename "$root").log"
        krc=0
        GNUPGHOME="$h" "$GPG_BIN" --batch --yes --generate-key "$h/keygen" >"$klog" 2>&1 || krc=$?
        if [ "$krc" -ne 0 ]; then
            first=$(LC_ALL=C grep -a -m1 -E "Operation not permitted|No agent running|error binding|failed to start|Configuration error" "$klog" || true)  # 找不到匹配即空串，是否命中由后续断言判定（不吞断言）
            TRIED="$TRIED | ${root}: keygen rc=${krc}: ${first:-见 $klog}"
            continue
        fi
        sec=$(GNUPGHOME="$h" "$GPG_BIN" --batch --with-colons --list-secret-keys 2>/dev/null | grep -c '^sec:' || true)  # gpg 失败计 0，后续 keygen/ownertrust 断言会因此变红（不吞断言）
        if [ "$sec" != "1" ]; then
            TRIED="$TRIED | ${root}: keygen rc=0 但 sec 计数=$sec"
            continue
        fi
        GHOME="$h"
        break
    done
    if [ -z "$GHOME" ]; then
        skip_group "E 组候选根（$ecands）上 gpg-agent 都起不来 ⇒ 私钥腿不可用；逐根一手读数：$TRIED"
    fi
fi

if [ -n "$GHOME" ]; then
    arm_begin e1_capable_root
    if [ -S "$GHOME/S.gpg-agent" ]; then
        ok capable_root "GNUPGHOME=$GHOME（候选根择优结果）；agent socket 已建成且节点类型是 socket：$(ls -l "$GHOME/S.gpg-agent" | awk '{print $1}')"
    else
        bad capable_root "keygen 已过但 $GHOME/S.gpg-agent 不是 socket 节点"
    fi
    arm_end

    arm_begin e2_keygen
    ok keygen "在 $GHOME 上 gpg --batch --generate-key rc=0，--list-secret-keys 计 1 把（第一把；e8 另生成第二把；逐根读数见 $EVID/keygen.*.log）"
    arm_end

    fpr=$(GNUPGHOME="$GHOME" "$GPG_BIN" --batch --with-colons --list-keys 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
    UID_E="pgpgpg-e2e@example.invalid"
    printf '%s:6:\n' "$fpr" | GNUPGHOME="$GHOME" "$GPG_BIN" --batch --yes --import-ownertrust >"$EVID/trust.log" 2>&1 || true  # 导入 ownertrust 的 rc 不入断言面，是否可信由后续 ownertrust 断言判定（不吞断言）
    arm_begin e3_ownertrust
    if GNUPGHOME="$GHOME" "$GPG_BIN" --batch --with-colons --list-keys 2>/dev/null | grep -q '^pub:u:'; then
        ok ownertrust "密钥已置为终极可信（--with-colons 的 pub 字段第 2 位是 u）"
    else
        bad ownertrust "import-ownertrust 后 pub 字段不是 u"
    fi
    arm_end

    # e4 armor 加密腿
    CASC="$OUT/e4.asc"
    arm_begin e4_armor_encrypt
    rc4=0
    GNUPGHOME="$GHOME" "$PGP" -e -a -o "$CASC" "$PLAIN" "$UID_E" >"$EVID/e4.out" 2>"$EVID/e4.err" || rc4=$?
    ck_rc e4_armor_rc 0 "$rc4" "pgpgpg -e -a 真加密（stderr 见 $EVID/e4.err）"
    arm_end
    ck_has e4_armor_header "$CASC" "-----BEGIN PGP MESSAGE-----"

    # e5 带有效收件人的 -e 的 execve argv 记录。
    #    pgpgpg 把 operands[0] 当输入文件 ⇒ 用一根 fifo 当输入文件把 gpg 阻塞在 read 上。
    #    fifo 必须开在 GHOME 所在的那个根上（EROOT）：$WORK 可能落在 hmdfs（本机 TMPDIR 就是），
    #    那里 mkfifo 直接 EPERM —— 整改前 e5 的四条读数就是这么全部降级成 SKIP 的。
    EROOT="$(dirname "$GHOME")"
    E5NOTE=""
    rec5="$EVID/argv.e5"
    : >"$rec5"
    arm_begin e5_recorded
    FIFO="$EROOT/$TAGP.e5.in"
    rm -f "$FIFO" 2>/dev/null || true  # 清理失败无害
    if mkfifo "$FIFO" 2>"$EVID/mkfifo.err"; then
        ( sleep "$HOLD" >"$FIFO" ) &
        GNUPGHOME="$GHOME" "$PGP" -e -a -o "$OUT/e5.bin" "$FIFO" "$UID_E" </dev/null >"$EVID/e5.out" 2>"$EVID/e5.err" &
        job5=$!
        scan_for e5.bin >"$rec5" 2>/dev/null || true  # 后台采集，失败由 arm_end 自检判 FAIL
        wait "$job5" 2>/dev/null || true  # 收后台任务，未起/已退都不影响断言
        rm -f "$FIFO" 2>/dev/null || true  # 清理失败无害
        if [ -s "$rec5" ]; then
            line="e5=$(cat "$rec5")"
            RECORDS="$RECORDS$line
"
            ok recorded "采到带有效收件人的 execve argv：$(cat "$rec5")"
        else
            bad recorded "未采到 argv（gpg 没阻塞在 fifo 上？）；stderr："
            show "$EVID/e5.err"
            E5NOTE="e5 的 argv 未采到，原因见上一臂"
        fi
    else
        skip recorded "mkfifo 在该根上不可用（与 hmdfs 同一类墙）：$(cat "$EVID/mkfifo.err" 2>/dev/null)"
        E5NOTE="mkfifo 不可用，e5 的 argv 记录无从取得"
    fi
    arm_end
    ck_has e5_argv_encrypt "$rec5" "--encrypt" "$E5NOTE"
    ck_has e5_argv_recipient "$rec5" "--recipient $UID_E" "$E5NOTE"
    ck_has e5_argv_armor "$rec5" "--armor" "$E5NOTE"

    # e6 armor 解密腿 + 逐字节回比
    DASC="$OUT/e6.txt"
    arm_begin e6_armor_roundtrip
    rc6d=0
    GNUPGHOME="$GHOME" "$PGP" -d -o "$DASC" "$CASC" >"$EVID/e6.out" 2>"$EVID/e6.err" || rc6d=$?
    if [ "$rc6d" = "0" ] && cmp "$PLAIN" "$DASC" >"$EVID/e6.cmp" 2>&1; then
        ok armor_roundtrip "pgpgpg -d 解回 $(wc -c <"$DASC") 字节，与明文 cmp 逐字节一致（-e rc=$rc4 / -d rc=$rc6d）"
    else
        bad armor_roundtrip "-d rc=$rc6d；cmp：$(cat "$EVID/e6.cmp" 2>/dev/null)；stderr："
        show "$EVID/e6.err"
    fi
    arm_end

    # e7 二进制（非 armor）往返
    CBIN="$OUT/e7.pgp"
    DBIN="$OUT/e7.txt"
    arm_begin e7_binary_roundtrip
    if GNUPGHOME="$GHOME" "$PGP" -e -o "$CBIN" "$PLAIN" "$UID_E" >"$EVID/e7e.out" 2>"$EVID/e7e.err" &&
       GNUPGHOME="$GHOME" "$PGP" -d -o "$DBIN" "$CBIN" >"$EVID/e7d.out" 2>"$EVID/e7d.err" &&
       cmp "$PLAIN" "$DBIN" >"$EVID/e7.cmp" 2>&1 &&
       ! LC_ALL=C grep -a -F -- "-----BEGIN PGP MESSAGE-----" "$CBIN" >/dev/null 2>&1; then
        ok binary_roundtrip "非 armor 腿：密文 $(wc -c <"$CBIN") 字节且无 ASCII 头，解回与明文 cmp 一致"
    else
        bad binary_roundtrip "非 armor 往返失败（密文 $(wc -c <"$CBIN" 2>/dev/null) 字节）"
        show "$EVID/e7e.err"
        show "$EVID/e7d.err"
    fi
    arm_end

    # e8 多收件人：正面覆盖"pgpgpg 有没有把 operands[1..] 全部译成 --recipient"。
    #    —— 取代整改前 T 组的 t07（它拿 gpg 的 stderr 回显当证据；本机 dirmngr 不存在，
    #    直调 gpg 传两个收件人时 gpg 只回显**末位**：count_a=0 / count_b=2 ⇒ 通道不可信）。
    #    这里用本脚本已有的 execve argv 采集：两条 --recipient 都必须在 argv 里，
    #    且前者位置在后者之前（顺序与命令行一致）。
    #    为什么只能在 E 组：收件人解析不过 gpg 就不会去开明文 ⇒ 没有阻塞窗口可采 argv，
    #    所以需要第二把本地可解析、终极可信的密钥（keygen2）。
    UID_E2="e8b+t07@example.invalid"
    E8NOTE=""
    rec8="$EVID/argv.e8"
    : >"$rec8"
    cat >"$GHOME/keygen2" <<KEYGEN2EOF
%echo pgpgpg-e2e-keygen2
Key-Type: RSA
Key-Length: 2048
Name-Real: pgpgpg e2e recipient b
Name-Comment: temporary
Name-Email: $UID_E2
Expire-Date: 0
%no-protection
%commit
%echo pgpgpg-e2e-keygen2-done
KEYGEN2EOF
    k2rc=0
    GNUPGHOME="$GHOME" "$GPG_BIN" --batch --yes --generate-key "$GHOME/keygen2" >"$EVID/keygen2.log" 2>&1 || k2rc=$?
    if [ "$k2rc" != "0" ]; then
        E8NOTE="第二把收件人密钥生成失败（rc=$k2rc，一手读数见 $EVID/keygen2.log）⇒ e8 的 argv 无从采集"
    else
        fpr2=$(GNUPGHOME="$GHOME" "$GPG_BIN" --batch --with-colons --list-keys "$UID_E2" 2>/dev/null | awk -F: '$1=="fpr"{print $10; exit}')
        printf '%s:6:\n' "$fpr2" | GNUPGHOME="$GHOME" "$GPG_BIN" --batch --yes --import-ownertrust >>"$EVID/trust.log" 2>&1 || true  # 导入 ownertrust 的 rc 不入断言面，是否可信由后续 ownertrust 断言判定（不吞断言）
        if ! GNUPGHOME="$GHOME" "$GPG_BIN" --batch --with-colons --list-keys "$UID_E2" 2>/dev/null | grep -q '^pub:u:'; then
            E8NOTE="第二把密钥没以终极可信落进 $GHOME 的 pubring（--with-colons 无 pub:u: 读数）⇒ e8 的 argv 无从采集"
        fi
    fi

    arm_begin e8_recorded
    if [ -n "$E8NOTE" ]; then
        skip recorded "$E8NOTE"
    else
        FIFO8="$EROOT/$TAGP.e8.in"
        rm -f "$FIFO8" 2>/dev/null || true  # 清理失败无害
        if ! mkfifo "$FIFO8" 2>"$EVID/mkfifo.e8.err"; then
            skip recorded "mkfifo 在端到端落点 $EROOT 上不可用：$(cat "$EVID/mkfifo.e8.err" 2>/dev/null)"
            E8NOTE="mkfifo 在 $EROOT 上不可用，e8 的 argv 记录无从取得"
        else
            ( sleep "$HOLD" >"$FIFO8" ) &
            GNUPGHOME="$GHOME" "$PGP" -e -a -o "$OUT/e8.bin" "$FIFO8" "$UID_E" "$UID_E2" </dev/null >"$EVID/e8.out" 2>"$EVID/e8.err" &
            job8=$!
            scan_for e8.bin >"$rec8" 2>/dev/null || true  # 后台采集，失败由 arm_end 自检判 FAIL
            wait "$job8" 2>/dev/null || true  # 收后台任务，未起/已退都不影响断言
            rm -f "$FIFO8" 2>/dev/null || true  # 清理失败无害
            if [ -s "$rec8" ]; then
                line="e8=$(cat "$rec8")"
                RECORDS="$RECORDS$line
"
                ok recorded "采到双收件人调用的 execve argv：$(cat "$rec8")"
            else
                bad recorded "未采到 argv（gpg 没阻塞在 fifo 上？）；pgpgpg stderr："
                show "$EVID/e8.err"
                E8NOTE="e8 的 argv 未采到，原因见上一臂"
            fi
        fi
    fi
    arm_end
    ck_has e8_argv_recipient_a "$rec8" "--recipient $UID_E" "$E8NOTE"
    ck_has e8_argv_recipient_b "$rec8" "--recipient $UID_E2" "$E8NOTE"
    arm_begin e8_argv_order
    if [ -n "$E8NOTE" ]; then
        skip e8_argv_order "$E8NOTE"
    else
        # 一次 awk 出三个一手读数：--recipient 出现次数 / A 的字节位置 / B 的字节位置
        e8r=$(LC_ALL=C awk -v a="--recipient $UID_E" -v b="--recipient $UID_E2" '
            {
                n = 0; s = $0
                while ((i = index(s, "--recipient")) > 0) { n++; s = substr(s, i + 13) }
                print n, index($0, a), index($0, b)
            }' "$rec8")
        e8n=${e8r%% *}
        e8rest=${e8r#* }
        e8a=${e8rest%% *}
        e8b=${e8rest##* }
        if [ -n "$e8r" ] && [ "$e8n" = "2" ] && [ "$e8a" -gt 0 ] && [ "$e8b" -gt "$e8a" ]; then
            ok e8_argv_order "argv 里 --recipient 恰 2 条，且 $UID_E（位置 $e8a）在 $UID_E2（位置 $e8b）之前 ⇒ 顺序与命令行一致，两个收件人操作数都没被丢"
        else
            bad e8_argv_order "一手读数：--recipient 条数=$e8n / A 位置=$e8a / B 位置=$e8b（期望 2 / >0 / 严格递增）；argv 原文："
            show "$rec8"
        fi
    fi
    arm_end

    # 收尾：别让本测试拉起的 agent 活过去
    if [ -x "$GPG_CONNECT_BIN" ]; then
        GNUPGHOME="$GHOME" "$GPG_CONNECT_BIN" KILLAGENT /bye >/dev/null 2>&1 || true  # 收尾动作，agent 未在跑即失败，不影响本轮断言（只在端到端腿跑过时才有意义）
        GNUPGHOME="$GHOME" "$GPG_CONNECT_BIN" KILLKEYBOXD /bye >/dev/null 2>&1 || true  # 收尾动作，同上
        GNUPGHOME="$GHOME" "$GPG_CONNECT_BIN" KILLDIRMNGR /bye >/dev/null 2>&1 || true  # 收尾动作，同上
    fi
fi

# =============================================================================
# 台账与总账
# =============================================================================
LEFT=0
for d in /proc/[0-9]*; do
    cm=$(<"$d/comm") 2>/dev/null || continue
    [ "$cm" = "gpg-agent" ] || continue
    echo "ORPHAN_AGENT $d $(tr '\0' ' ' <"$d/cmdline")"
    LEFT=$((LEFT + 1))
done
echo "AGENT_LEFT=$LEFT"
echo "--- execve argv 记录清单 ---"
printf '%s' "$RECORDS"
echo "--- 逐臂台账（id outcome） ---"
printf '%s' "$ARM_LEDGER"

DISC=$((PS + FS + SS))
echo "TEST_SUMMARY discovered=$DISC passed=$PS failed=$FS skipped=$SS"
if [ "$DISC" -eq 0 ]; then
    echo "FAIL: 一条断言都没产出，账本不可信"
    exit 1
fi
if [ "$PS" -eq 0 ]; then
    echo "FAIL: 没有任何断言通过（连翻译面都没成立）"
    exit 1
fi
if [ "$FS" -gt 0 ]; then
    exit 1
fi
exit 0
