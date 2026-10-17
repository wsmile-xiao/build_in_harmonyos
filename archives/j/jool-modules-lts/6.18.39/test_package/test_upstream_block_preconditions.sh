#!/usr/bin/env bash
# test_upstream_block_preconditions.sh — jool-modules-lts 6.18.39
# 上游 36 个测试脚本的逐脚本阻塞前置 fail-closed 审计 + 2 个 root 门禁脚本真实执行。
#
# 背景：上游 Jool 的 test/ 共 36 个 .sh，被测对象是 Linux 内核模块（Kbuild obj-m
# + DKMS）——全部脚本的前置条件（root / insmod / modprobe / netns / 预编译内核树）
# 在 OHOS 用户态沙箱（USER=100，无内核构建树）不存在。本审计做两件事：
#
# A. **逐脚本前置审计（34 个）**：对 block-map 中的每个脚本，验证其源码仍命中
#    对应的阻塞模式串。这是 fail-closed 的：若上游某脚本形态变为用户态可执行
#    （模式串未命中），审计立即失败——强制重新评估该脚本是否应转为真实执行，
#    而不是沿用旧结论。
# B. **真实执行（2 个）**：client-test.sh 与 graybox/test-suite/run.sh 的第一道
#    语句是非 root 门禁（`$UID != 0` / `id -u`），可安全真实执行——预期以
#    "Please start the script as root or sudo." + 退出码 1 阻塞。这为「上游
#    用例 0/36 通过」提供第一手执行证据：脚本真的跑过，真的阻塞在 root 前置。
#    门禁断言仅在非 root 语义下成立：root 环境会越过门禁继续执行。故 root 下
#    用 setpriv 降权到 uid 65534 真实执行（退回 runuser -u nobody）；两者皆
#    不可用时显式 skip（不判失败）。两脚本门禁均为首语句，先于任何 $0 相对
#    路径生效，故拷贝到临时目录执行不影响门禁语义，同时规避 conan 缓存目录
#    对降权身份不可读的问题。
#
# OHOS id 工具缺陷处置（CI #56279 实证）：OHOS CI worker 的运行账户是超界 uid
# （实测 2002010133），系统 toybox `id -u` 对其报 "bad uid" 且无数值输出——
# ①本脚本自身的 root 自检改用 bash 内建 EUID（geteuid(2) 直读，无查表/无范围
#   限制，任意 uid 下恒为真值）；
# ②上游 run.sh 的门禁是未加引号的 `[ $(id -u) != 0 ]`：在坏 id 下退化为
#   `[ != 0 ]`（unary operator expected）→ 门禁失效、脚本跑到缺文件退出 127
#   ——这是平台工具缺陷，非上游形态变化。为此在 B2 的 PATH 前列放置仅实现
#   `id -u` 的 shim（同样用 $EUID 返回真实数值 uid），让上游门禁拿到真实
#   uid 做出真实判断：非 root → 门禁照常触发。断言语义不变（仍是真实执行 +
#   真实门禁决策）；若上游删除门禁，脚本会继续执行并以 127 失败，本审计
#   仍然 fail-closed。
set -u

MAP="${1:?usage: test_upstream_block_preconditions.sh <map.tsv> <upstream_test_dir>}"
TESTDIR="${2:?usage: test_upstream_block_preconditions.sh <map.tsv> <upstream_test_dir>}"

PASS=0
FAIL=0
ok()  { PASS=$((PASS + 1)); echo "  [ok] $1"; }
bad() { FAIL=$((FAIL + 1)); echo "  [FAIL] $1"; }

echo "== A. 上游 36 脚本逐条阻塞前置审计 =="

AUDITED=0
while IFS=$'\t' read -r rel pattern reason; do
    case "$rel" in ''|'#'*) continue ;; esac
    AUDITED=$((AUDITED + 1))
    f="$TESTDIR/${rel#test/}"
    if [ ! -f "$f" ]; then
        bad "$rel：快照中缺失"
        continue
    fi
    if grep -Fq -- "$pattern" "$f"; then
        ok "$rel：命中阻塞前置（$reason）"
    else
        bad "$rel：未命中阻塞模式 '$pattern'——上游形态可能已变为用户态可执行，须重评（$reason）"
    fi
done < "$MAP"

[ "$AUDITED" -eq 36 ] && ok "审计覆盖全部 36 个上游脚本" \
    || bad "审计覆盖 $AUDITED 个脚本（期望 36）"

echo "== B. root 门禁脚本真实执行（预期阻塞） =="

# root 自检：EUID 是 bash 内建（geteuid 直读），在 OHOS toybox id 报
# "bad uid"（超界 uid 无数值输出）的环境下依然可靠；异常兜底按非 root 处理。
CUR_UID="${EUID:-1}"
case "$CUR_UID" in
    ''|*[!0-9]*) CUR_UID=1 ;;
esac

RUNNER=""
SKIP_B="no"
if [ "$CUR_UID" -eq 0 ]; then
    if command -v setpriv >/dev/null 2>&1; then
        RUNNER="setpriv --reuid=65534 --regid=65534 --clear-groups"
    elif command -v runuser >/dev/null 2>&1 && grep -q '^nobody:' /etc/passwd 2>/dev/null; then
        RUNNER="runuser -u nobody --"
    else
        SKIP_B="yes"
    fi
fi

if [ "$SKIP_B" = "yes" ]; then
    echo "  [skip] root 环境且无 setpriv/runuser 降权工具：root 门禁仅非 root 语义可验证"
else
    SANDBOX="$(mktemp -d 2>/dev/null || echo "${TMPDIR:-/tmp}/jool-blk-sandbox.$$")"
    chmod 755 "$SANDBOX"
    cp "$TESTDIR/client-test.sh" "$SANDBOX/client-test.sh"
    cp "$TESTDIR/graybox/test-suite/run.sh" "$SANDBOX/graybox-run.sh"
    chmod 644 "$SANDBOX/client-test.sh" "$SANDBOX/graybox-run.sh"

    # B1. test/client-test.sh：首语句 UID 门禁
    OUT_FILE="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/jool-blk-test.$$")"
    RC=0
    $RUNNER bash "$SANDBOX/client-test.sh" >"$OUT_FILE" 2>&1 || RC=$?
    OUT="$(cat "$OUT_FILE")"
    rm -f "$OUT_FILE"
    [ "$RC" -eq 1 ] && ok "client-test.sh 真实执行并以预期退出码 1 阻塞" \
        || bad "client-test.sh 退出码 $RC（期望 1：root 门禁）"
    case "$OUT" in
        *"Please start the script as root or sudo."*)
            ok "client-test.sh 打印预期的 root 门禁提示" ;;
        *) bad "client-test.sh 输出异常: $OUT" ;;
    esac

    # B2. test/graybox/test-suite/run.sh：首语句 id -u 门禁。
    #     OHOS worker 的系统 id 对超界 uid 报 "bad uid" 输出空（见文件头注释），
    #     PATH 前列放 id shim 让门禁拿到真实 uid；shim 只修环境工具，不改被测
    #     脚本——门禁决策仍是 run.sh 自己做的真实判断。
    mkdir -p "$SANDBOX/bin"
    cat > "$SANDBOX/bin/id" <<'SHIM_EOF'
#!/usr/bin/env bash
# id shim — 仅实现 `id -u`：OHOS toybox id 对超界 uid（如 CI worker 的
# 2002010133）报 "bad uid" 且无数值输出；bash 内建 EUID 由 geteuid(2)
# 直读，对任意 uid 恒为真值。其余用法回绝（本审计只需 -u）。
case "${1-}" in
    -u) echo "${EUID:-1}" ;;
    *)  echo "id shim: only -u supported" >&2; exit 1 ;;
esac
SHIM_EOF
    chmod 755 "$SANDBOX/bin/id"
    OUT_FILE="$(mktemp 2>/dev/null || echo "${TMPDIR:-/tmp}/jool-blk-test2.$$")"
    RC=0
    ( cd "$SANDBOX" && PATH="$SANDBOX/bin:$PATH" $RUNNER bash ./graybox-run.sh ) >"$OUT_FILE" 2>&1 || RC=$?
    OUT="$(cat "$OUT_FILE")"
    rm -f "$OUT_FILE"
    [ "$RC" -eq 1 ] && ok "graybox run.sh 真实执行并以预期退出码 1 阻塞" \
        || bad "graybox run.sh 退出码 $RC（期望 1：root 门禁）"
    case "$OUT" in
        *"Please start the script as root or sudo."*)
            ok "graybox run.sh 打印预期的 root 门禁提示" ;;
        *) bad "graybox run.sh 输出异常: $OUT" ;;
    esac

    rm -rf "$SANDBOX"
fi

echo "== test_upstream_block_preconditions.sh 结果: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
