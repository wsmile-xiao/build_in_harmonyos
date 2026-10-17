#!/bin/sh
# test.sh — kinect-audio-setup 0.5 消费者断言
# 用法: sh test.sh <kinect_upload_fw-binary> <writable-workdir>
#
# 上游无测试套件（R51：Makefile 无 check 目标、无 tests/），此处对打包后的
# 真实二进制做实跑断言：
#   (a) 二进制在 OHOS 上可执行（ELF 解析、动态链接正常）；
#   (b) 程序逻辑路径完整——kinect_upload_fw 以 argv[1] 为固件文件名，
#       无文件时报错退出（-errno 路径），有文件但无 Kinect 硬件时走
#       libusb 打开失败路径；两者均证明依赖 libusb 已静态链入且符号可解析。
set -e

BIN="$1"
WORK="$2"
fail=0

check() {
    # check <描述> <文件> <grep 模式>
    if grep -q "$3" "$2"; then
        echo "ok - $1"
    else
        echo "FAIL - $1"
        fail=1
    fi
}

cd "$WORK"

# 0) 二进制存在且可执行
if [ -x "$BIN" ]; then
    echo "ok - sbin/kinect_upload_fw 存在且可执行"
else
    echo "FAIL - sbin/kinect_upload_fw 不存在或不可执行"
    fail=1
fi

# 1) 无参数/伪参数：按固件文件名处理，打开失败报错退出（证明 argc 解析路径完整）
"$BIN" --help > help.out 2> help.err || true
check "--help 触发固件打开错误路径（argc==2 分支）" help.err "Failed to open --help"

# 2) 真实固件文件（空文件即可触发 libusb_init/打开设备流程）：
#    沙箱内无 USB 权限时 libusb_init 直接报 LIBUSB_ERROR_IO；设备无连接时
#    libusb_open_device_with_vid_pid 返回 NULL → libusb_open failed。
#    两种路径任一出现即证明 libusb 已静态链入、符号可解析（若静态链接
#    失败，程序启动即崩，以下断言可捕获）。
printf '\x00' > dummy_fw.bin
"$BIN" dummy_fw.bin > dev.out 2> dev.err || true
if grep -qE "libusb_init failed|libusb_open failed" dev.err; then
    echo "ok - libusb 符号可解析（沙箱内 USB 不可用时报错路径正常）"
else
    echo "FAIL - libusb 报错路径异常（dev.err: $(cat dev.err | head -1)）"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "kinect-audio-setup test_package: FAILED"
    exit 1
fi
echo "kinect-audio-setup test_package: all 3 checks passed"