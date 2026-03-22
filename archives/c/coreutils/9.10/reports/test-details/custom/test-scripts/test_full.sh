#!/bin/sh
# 完整测试流程

LOG="$(pwd)/test_full.log"
echo "=== 开始完整测试 $(date) ===" > "$LOG"

log() {
    echo "[$(date +%H:%M:%S)] $1" >> "$LOG"
    echo "$1" >&2
}

log "步骤1: 设置环境"
export srcdir=. builddir=. built_programs="cat"
export PATH="$(pwd)/src:$PATH"

log "步骤2: source init.sh"
. ./tests/init.sh
log "init.sh 加载完成"

log "步骤3: path_prepend_"
path_prepend_ ./src

log "步骤4: which cat"
which cat > /dev/null

log "步骤5: print_ver_ cat"
print_ver_ cat
log "print_ver_ 完成"

log "步骤6: echo which cat"
echo which cat

log "步骤7: 创建测试文件"
echo x > out || framework_failure_
echo x > out1 || framework_failure_
log "测试文件创建完成"

log "步骤8: returns_ 1 cat out >>out"
log "检查 returns_ 函数: $(type returns_ 2>&1 | head -1)"
returns_ 1 cat out >>out || fail=1
log "returns_ 完成, fail=$fail"

log "步骤9: compare out out1"
compare out out1 || fail=1
log "compare 完成"

log "步骤10: 创建 doc 文件"
echo x > doc || framework_failure_
echo y > doc.end || framework_failure_
log "doc 文件创建完成"

log "步骤11: cat doc doc.end >doc"
cat doc doc.end >doc || fail=1
log "cat 完成"

log "步骤12: compare doc doc.end"
compare doc doc.end || fail=1
log "compare 完成"

log "=== 测试完成, fail=$fail ==="
echo "测试完成"
