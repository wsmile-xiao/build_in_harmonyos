#!/bin/sh
# test_package/test.sh — vor 0.5.8 消费者功能测试
# 用法: test.sh <vor 可执行路径> <包内 share/vor 目录>
#
# 上游无测试套件（Makefile.in 全文没有 check/TESTS 目标，configure.ac 无
# AC_CONFIG_TESTDIR），所以本包的可执行测试全部由这份消费者脚本承担。
# 断言数以 "ASSERTIONS=" 行机器可读地打在 stdout，供 notes.md 五维账本对齐。
#
# 口径：
#   · --version/--help/选项错误路径由上游 args.c 提供，且在 main() 里先于任何
#     SDL 调用 ⇒ 无显示/无声卡环境也能真跑（没有为过门放宽任何断言）。
#   · 数据定位用「藏起来 / 放回去」双向证明，钉死"包内 share/vor 就是二进制运行时
#     真正使用的那个目录"（file.c find_data_dir 第三候选 = 编译期烧进的 DATA_PREFIX）。
#   · 显示/音频层不断言可用：那是环境能力，探测输出原样打在日志里，见 notes.md。
#   · 设备 /tmp 只读 ⇒ 所有中间输出写进 $TMPDIR（回退 ~/tmp）。

VOR="$1"
DATADIR="$2"

if [ ! -f "$VOR" ]; then
    echo "[fail] vor not found at $VOR"
    exit 1
fi
if [ ! -d "$DATADIR" ]; then
    echo "[fail] packaged data dir not found at $DATADIR"
    exit 1
fi

WORK="${TMPDIR:-$HOME/tmp}/z75v-test-$$"
mkdir -p "$WORK" || exit 1

TOTAL=0
PASSED=0
FAILED=0

check() {
    # check <编号说明> <0=通过 非0=失败>
    label="$1"
    ok="$2"
    TOTAL=$((TOTAL + 1))
    if [ "$ok" -eq 0 ]; then
        PASSED=$((PASSED + 1))
        echo "[pass] $label"
    else
        FAILED=$((FAILED + 1))
        echo "[fail] $label"
    fi
}

run_cap() {
    # run_cap <输出文件> <命令...> —— 捕获 stdout+stderr，退出码写进 $RC
    out="$1"
    shift
    "$@" > "$out" 2>&1
    RC=$?
}

guard_run() {
    # guard_run <输出文件> <命令...> —— 最多等 20 秒，超时 kill（防 worker 有显示时卡死）
    out="$1"
    shift
    "$@" > "$out" 2>&1 &
    pid=$!
    ticks=0
    while kill -0 "$pid" 2>/dev/null; do
        ticks=$((ticks + 1))
        if [ "$ticks" -ge 20 ]; then
            kill -9 "$pid" 2>/dev/null
            echo "[info] watchdog: vor still running after 20s, killed" >> "$out"
            GUARD_RC=124
            return 0
        fi
        sleep 1
    done
    wait "$pid"
    GUARD_RC=$?
    return 0
}

HIDDEN=""
restore_data() {
    if [ -n "$HIDDEN" ] && [ -d "$HIDDEN" ]; then
        mv "$HIDDEN" "$DATADIR" 2>/dev/null
    fi
}
trap 'restore_data; rm -rf "$WORK"; exit 130' INT
trap 'restore_data; rm -rf "$WORK"; exit 143' TERM

# ───────────────────────── 1. CLI 面（无头即可跑） ─────────────────────────
run_cap "$WORK/version.out" "$VOR" --version
check "1. 'vor --version' exits 0 (rc=$RC)" "$RC"
check "2. 'vor --version' prints the upstream banner line verbatim" \
      $(grep -qx "Variations on Rockdodger 0.5.8" "$WORK/version.out" && echo 0 || echo 1)

run_cap "$WORK/help.out" "$VOR" --help
HELP_RC=$RC
check "3. 'vor --help' exits non-zero by upstream design (rc=$HELP_RC)" \
      $([ "$HELP_RC" -ne 0 ] && echo 0 || echo 1)
for needle in "-f, --full-screen" "-s, --silent" "-V, --version" "-?, --help"; do
    check "4. --help usage lists '$needle'" \
          $(grep -qF -- "$needle" "$WORK/help.out" && echo 0 || echo 1)
done

run_cap "$WORK/badshort.out" "$VOR" -Z
check "5. unknown short option exits non-zero (rc=$RC)" \
      $([ "$RC" -ne 0 ] && echo 0 || echo 1)
check "6. unknown short option reports 'unknown option -Z'" \
      $(grep -qF "unknown option -Z" "$WORK/badshort.out" && echo 0 || echo 1)

run_cap "$WORK/badlong.out" "$VOR" --bogus-option
check "7. unknown long option reports 'unknown long option --bogus-option'" \
      $(grep -qF "unknown long option --bogus-option" "$WORK/badlong.out" && echo 0 || echo 1)

run_cap "$WORK/arg.out" "$VOR" not-an-option
check "8. a bare argument is rejected with 'not an option'" \
      $(grep -qF "not an option" "$WORK/arg.out" && echo 0 || echo 1)

# ───────────────────────── 2. 打包数据资产 ─────────────────────────
PNG_COUNT=$(ls "$DATADIR" | grep -c '\.png$')
ALL_COUNT=$(ls "$DATADIR" | wc -l)
check "9. share/vor holds 59 PNG assets (got $PNG_COUNT)" \
      $([ "$PNG_COUNT" -eq 59 ] && echo 0 || echo 1)
check "10. share/vor holds 61 entries: 59 png + bang.wav + mph.xm (got $ALL_COUNT)" \
      $([ "$ALL_COUNT" -eq 61 ] && echo 0 || echo 1)
for f in b_variations.png font.png ship.png icon.png life.png rock00.png rock49.png bang.wav mph.xm; do
    check "11. packaged asset $f present" $([ -f "$DATADIR/$f" ] && echo 0 || echo 1)
done

# ─────────────── 3. 运行期数据定位（DATA_PREFIX 双向证明） ───────────────
# 显式指定不存在的视频驱动名，使断言与 worker 有没有显示无关：
#   数据缺失 ⇒ find_files() 先失败并打印 "Can't find VoR data!"，快速退出；
#   数据在位 ⇒ 必然越过数据检查，失败点只能在 SDL 视频层（或被看门狗收掉）。
export SDL_VIDEODRIVER=none

HIDDEN="${DATADIR}.z75v-hidden"
mv "$DATADIR" "$HIDDEN" 2>/dev/null
if [ -d "$DATADIR" ] || [ ! -d "$HIDDEN" ]; then
    check "12. packaged data dir can be renamed for the data-path probe" 1
    HIDDEN=""
else
    guard_run "$WORK/nodata.out" "$VOR" -s
    check "12. data hidden -> vor reports \"Can't find VoR data!\" (rc=$GUARD_RC)" \
          $(grep -qF "Can't find VoR data" "$WORK/nodata.out" && echo 0 || echo 1)
    restore_data
    HIDDEN=""
fi

guard_run "$WORK/data.out" "$VOR" -s
check "13. data in place -> same run resolves it (no 'Can't find VoR data')" \
      $(grep -qF "Can't find VoR data" "$WORK/data.out" && echo 1 || echo 0)
check "14. SDL 1.2 stack loads at run time (no dynamic-linker error)" \
      $(grep -qiE "CANNOT LINK|error loading shared library" "$WORK/data.out" && echo 1 || echo 0)
unset SDL_VIDEODRIVER

# 显示层实测原样留档（不作断言，只把真实输出交给日志/notes）
echo "----- 运行期探测实录（SDL_VIDEODRIVER=none, vor -s, rc=$GUARD_RC）-----"
sed -e 's/^/| /' "$WORK/data.out"
echo "-------------------------------------------------------------------"

restore_data
rm -rf "$WORK"

echo "ASSERTIONS=$TOTAL PASSED=$PASSED FAILED=$FAILED"
if [ "$FAILED" -ne 0 ] || [ "$TOTAL" -ne 25 ]; then
    echo "[result] FAIL (期望 25 条断言全过，实际 total=$TOTAL failed=$FAILED)"
    exit 1
fi
echo "[result] PASS"
exit 0
