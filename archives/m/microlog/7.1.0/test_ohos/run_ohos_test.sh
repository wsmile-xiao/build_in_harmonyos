#!/bin/sh
# test_ohos — microlog 7.1.0 HarmonyOS PC 专项验证（自包含，可单独执行）
#
# 在真实鸿蒙 PC（aarch64, OHOS）上对最终 Conan 包做独立专项检查：
#
#   T1  aarch64 ELF 验证（消费者可执行文件为 ELF64 AArch64，可在 OHOS 执行）
#   T2  OHOS 可执行位与宿主路径泄漏检查（无 /storage、/home 等宿主绝对路径）
#   T3  消费者程序真实编译链接运行：主题路由 + 文件输出 + 级别字符串 +
#       ulog_event_to_cstr 事件格式化，输出可观察结果并断言
#
# 用法：sh run_ohos_test.sh [work_dir]
# 前置：conan create 已完成（包在本地缓存），工具链取 OHOS SDK clang。
set -u
WORK="${1:-/storage/Users/currentUser/tmp/ohc-logs}"
mkdir -p "$WORK"

fail=0
chk() { # $1=name $2=result
    if [ "$2" = "0" ]; then echo "PASS: $1"; else echo "FAIL: $1"; fail=1; fi
}

echo "--- microlog 7.1.0 HarmonyOS 专项验证 (work=$WORK) ---"

# 动态解析已安装包路径（避免硬编码 package_id；配方/设置变更后仍可复跑）
PKG_ID=$(conan list "microlog/7.1.0@ohpcd/stable:*" --format=json 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); pkgs=list(d['Local Cache']['microlog/7.1.0@ohpcd/stable']['revisions'].values())[0]['packages']; print(next(iter(pkgs)))" 2>/dev/null)
if [ -n "$PKG_ID" ]; then
    PKG_PATH=$(conan cache path "microlog/7.1.0@ohpcd/stable:$PKG_ID" 2>/dev/null | head -1)
else
    PKG_PATH=""
fi
PKG_INC="${PKG_PATH}/include"
PKG_SHARE="${PKG_PATH}/share/microlog/src"
[ -f "$PKG_INC/ulog.h" ] || { echo "FAIL: package include not found ($PKG_INC)"; exit 2; }

# T1/T3: 编译消费者程序（公开头 + 安装的 ulog.c，模拟第三方使用者）
# 特性宏按上游消费者惯例在编译期配置 (与上游 tests/unit 相同的基础配置);
# -ffile-prefix-map 去除宿主绝对路径, 保证 T2 通过且产物可移植。
BIN="$WORK/consumer_test"
aarch64-unknown-linux-ohos-clang consumer_test.c \
    -I"$PKG_INC" "$PKG_SHARE/ulog.c" -o "$BIN" \
    -DULOG_BUILD_EXTRA_OUTPUTS=8 \
    -DULOG_BUILD_TIME=1 \
    -DULOG_BUILD_PREFIX_SIZE=16 \
    -DULOG_BUILD_TOPICS_MODE=ULOG_BUILD_TOPICS_MODE_STATIC \
    -DULOG_BUILD_TOPICS_STATIC_NUM=8 \
    -ffile-prefix-map="$PKG_INC"=microlog \
    -ffile-prefix-map="$PKG_SHARE"=microlog \
    2>"$WORK/consumer_build.log"
if [ $? -eq 0 ] && [ -f "$BIN" ]; then
    chk "T3a 消费者程序编译链接 (aarch64-unknown-linux-ohos-clang)" 0
else
    echo "  build log: $(tail -3 "$WORK/consumer_build.log")"
    chk "T3a 消费者程序编译链接" 1
fi

# T1: aarch64 ELF
readelf -h "$BIN" 2>/dev/null | grep -q "AArch64" && r=0 || r=1
chk "T1 aarch64 ELF (ELF64 AArch64)" "$r"

# T2: 宿主路径泄漏
if strings "$BIN" 2>/dev/null | grep -qE '/storage/|/home/|/Users/|\.conan2'; then
    leak=$(strings "$BIN" | grep -E '/storage/|/home/|/Users/|\.conan2' | head -1)
    echo "  leak: $leak"
    chk "T2 无宿主绝对路径泄漏" 1
else
    chk "T2 无宿主绝对路径泄漏" 0
fi

# T3: 实际运行（写入可写目录，不依赖 tmpfile）
if [ -f "$BIN" ]; then
    out=$(cd "$WORK" && timeout 30 "$BIN" "$WORK" 2>&1); rc=$?
    echo "  consumer output: $out"
    if [ "$rc" = "0" ] && echo "$out" | grep -q "PASS: consumer_test"; then
        chk "T3 消费者运行 (topics/file-output/level/event OK)" 0
    else
        chk "T3 消费者运行 (rc=$rc)" 1
    fi
else
    chk "T3 消费者运行" 1
fi

echo "--- microlog OHOS 专项: $([ $fail = 0 ] && echo ALL PASS || echo FAILED) ---"
exit $fail