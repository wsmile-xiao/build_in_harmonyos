#!/bin/sh
# test_run.sh — cbonsai 1.4.2 消费者测试（L0c 测试源文件）
# 由 test_package/conanfile.py 调用，$1 = 已安装 cbonsai 二进制路径。
# 四断言：help 输出、静态渲染尺寸、自定义叶子字符 '@' 渲染次数、同种子确定性。
# initscr() 需要 terminfo 数据库：TERMINFO 由主配方经 runenv_info 传播，
# 此处仅提供 TERM=xterm。
set -eu

bin="$1"
[ -x "$bin" ] || { echo "FAIL: $bin 不存在或不可执行"; exit 1; }

# 1. Help：usage 文本、退出码 0
help=$("$bin" -h 2>&1) || { echo "FAIL: cbonsai -h 退出码非零"; exit 1; }
echo "$help" | grep -q "Usage" || { echo "FAIL: -h 输出不含 Usage"; exit 1; }

# 2/3. 确定性静态渲染
tree1=$(TERM=xterm "$bin" -p -s 42 -c "@:." -b 0 2>&1) \
  || { echo "FAIL: 静态渲染退出码非零"; exit 1; }
[ "${#tree1}" -ge 100 ] || { echo "FAIL: 渲染输出异常小（${#tree1} 字节）"; exit 1; }
n=$(printf '%s' "$tree1" | tr -cd '@' | wc -c | tr -d ' ')
[ "$n" -ge 10 ] || { echo "FAIL: 自定义叶子字符 '@' 渲染仅 $n 次"; exit 1; }

# 4. 同种子两次运行输出一致（RNG 确定性）
tree2=$(TERM=xterm "$bin" -p -s 42 -c "@:." -b 0 2>&1) \
  || { echo "FAIL: 第二次渲染退出码非零"; exit 1; }
[ "$tree1" = "$tree2" ] || { echo "FAIL: 同种子两次输出不一致——RNG 不确定"; exit 1; }

echo "cbonsai tool consumer test PASSED"
