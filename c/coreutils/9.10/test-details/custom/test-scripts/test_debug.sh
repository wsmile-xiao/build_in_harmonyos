#!/bin/sh
# 详细调试脚本 - 每步输出日志

LOG="/tmp/test_debug.log"
echo "=== 开始测试 $(date) ===" > "$LOG"

log() {
    echo "[$(date +%H:%M:%S)] $1" >> "$LOG"
    echo "$1" >&2
}

log "步骤1: 设置环境变量"
export srcdir=. builddir=. built_programs="cat"
export PATH="$(pwd)/src:$PATH"
log "PATH=$PATH"

log "步骤2: source init.sh 开始"
. ./tests/init.sh 2>&1 | head -20 >> "$LOG"
log "步骤2: source init.sh 完成"

log "步骤3: path_prepend_ 开始"
path_prepend_ ./src
log "步骤3: path_prepend_ 完成"

log "步骤4: which cat 开始"
which cat
log "步骤4: which cat 完成: $(which cat)"

log "步骤5: print_ver_ cat 开始"
print_ver_ cat
log "步骤5: print_ver_ cat 完成"

log "步骤6: echo which cat"
echo which cat

log "步骤7: 创建测试文件"
echo x > out
echo x > out1
log "步骤7完成"

log "步骤8: returns_ 1 cat out >>out 开始"
returns_ 1 cat out >> out
ret=$?
log "步骤8完成, 返回值=$ret"

log "步骤9: compare out out1"
compare out out1
log "步骤9完成"

log "=== 所有测试完成 ==="
echo "测试完成"
