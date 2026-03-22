#!/bin/sh
# 逐条测试 cat-self.sh 中的命令，每条都加日志和 timeout

WORKDIR="/storage/Users/currentUser/tmp/opendesk/coreutils-9.10-work"
LOGFILE="$WORKDIR/cat_self_debug.log"
TIMEOUT_CMD="timeout 5"

# 设置环境
export PATH="$WORKDIR/src:$PATH"
cd "$WORKDIR"

# 清空日志
> "$LOGFILE"

log() {
    echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOGFILE"
}

run_cmd() {
    local desc="$1"
    local cmd="$2"
    log "=== 测试: $desc ==="
    log "命令: $cmd"
    eval "$TIMEOUT_CMD $cmd" 2>&1 | tee -a "$LOGFILE"
    local ret=$?
    log "退出码: $ret"
    if [ $ret -eq 124 ]; then
        log "⚠️  命令超时！"
    fi
    echo "" >> "$LOGFILE"
    return $ret
}

# 准备测试目录
TESTDIR="$WORKDIR/gt-debug-$$"
mkdir -p "$TESTDIR"
cd "$TESTDIR"

log "测试目录: $TESTDIR"
log "PATH: $PATH"
log "使用的 cat: $(which cat)"

# 测试 1: 检查 cat 版本
run_cmd "cat --version" "cat --version | head -1"

# 测试 2: 基本文件创建
run_cmd "创建测试文件" "echo x > out && echo x > out1"

# 测试 3: cat out >> out (应该返回错误)
run_cmd "cat out >> out (期望返回1)" "cat out >> out; echo 退出码=\$?"

# 测试 4: compare out out1
run_cmd "compare out out1" "diff out out1; echo diff退出码=\$?"

# 测试 5: POSIX 示例
run_cmd "POSIX示例准备" "echo x > doc && echo y > doc.end"

# 测试 6: cat doc doc.end >doc
run_cmd "cat doc doc.end >doc" "cat doc doc.end > doc; echo 退出码=\$?"

# 测试 7: compare doc doc.end
run_cmd "compare doc doc.end" "diff doc doc.end; echo diff退出码=\$?"

# 测试 8: 准备 fx, fy, fxy
run_cmd "准备 fx fy fxy" "echo x > fx && echo y > fy && cat fx fy > fxy"

# 测试 9: 循环创建 fxy1, fxy2
run_cmd "创建 fxy1 fxy2" "cat fx > fxy1 && cat fx > fxy2"

# 测试 10: 循环创建 fx3-fx6
run_cmd "创建 fx3-fx6" "for i in 3 4 5 6; do cat fx > fx\$i; done"

# 测试 11: 关键测试 - cat - fy <fxy1 1<>fxy1
log "=== 测试 11: cat - fy <fxy1 1<>fxy1 (关键!) ==="
log "这个测试使用了 <> 读写模式"
run_cmd "cat - fy <fxy1 1<>fxy1" "sh -c 'cat - fy < fxy1 1<> fxy1' 2>&1"

# 测试 12: compare fxy fxy1
run_cmd "compare fxy fxy1" "diff fxy fxy1; echo diff退出码=\$?"

# 测试 13: cat fxy2 fy 1<>fxy2
run_cmd "cat fxy2 fy 1<>fxy2" "sh -c 'cat fxy2 fy 1<> fxy2' 2>&1"

# 测试 14: returns_ 1 cat fx fx3 1<>fx3
run_cmd "cat fx fx3 1<>fx3 (期望返回1)" "sh -c 'cat fx fx3 1<> fx3; echo 退出码=\$?' 2>&1"

# 测试 15: returns_ 1 cat - fx4 <fx 1<>fx4
run_cmd "cat - fx4 <fx 1<>fx4 (期望返回1)" "sh -c 'cat - fx4 < fx 1<> fx4; echo 退出码=\$?' 2>&1"

# 测试 16: returns_ 1 cat fx5 >>fx5
run_cmd "cat fx5 >>fx5 (期望返回1)" "cat fx5 >> fx5; echo 退出码=\$?"

# 测试 17: returns_ 1 cat <fx6 >>fx6
run_cmd "cat <fx6 >>fx6 (期望返回1)" "cat < fx6 >> fx6; echo 退出码=\$?"

# 测试 18: exec fd 操作
log "=== 测试 18: exec fd 操作 ==="
log "这个测试涉及文件描述符操作"
run_cmd "创建 file" "echo foo > file"
run_cmd "exec 3< file" "exec 3< file && echo 'fd3 打开成功'"
run_cmd "cat <&3" "timeout 3 cat <&3"
run_cmd "exec 4>> file" "exec 4>> file && echo 'fd4 追加模式打开成功'"
run_cmd "cat <&3 >&4" "timeout 3 cat <&3 >&4"
run_cmd "关闭 fd" "exec 3<&- 4>&- && echo 'fd 关闭成功'"

log "=== 测试完成 ==="
log "日志文件: $LOGFILE"

# 清理
cd "$WORKDIR"
rm -rf "$TESTDIR"
