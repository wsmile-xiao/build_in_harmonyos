#!/bin/bash
# test_package test.sh — bsd 3.3 (bsd-games) 消费者测试
# 21 项断言：18 个游戏二进制存在性 + caesar 频率分析/显式偏移 + wump 用法
set -euo pipefail

BIN_DIR="${1:-}"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "test.sh: usage: $0 <bindir>"
    exit 2
fi

# 1) 18 个游戏二进制存在且可执行
for g in adventure arithmetic atc battlestar caesar cribbage dab drop4 \
         gofish gomoku hangman klondike robots sail snake spirhunt worm wump; do
    test -x "$BIN_DIR/$g" || {
        echo "FAIL: $BIN_DIR/$g 不存在或不可执行"
        exit 1
    }
done

# 2) caesar 无参数频率分析（find_best_rotation 选中偏移 23）
out=$(printf 'Hello World' | "$BIN_DIR/caesar")
test "$out" = "Ebiil Tloia" || {
    echo "FAIL: caesar 无参数输出 '$out' != 'Ebiil Tloia'"
    exit 1
}

# 3) caesar 显式偏移 13
out=$(printf 'Hello' | "$BIN_DIR/caesar" 13)
test "$out" = "Uryyb" || {
    echo "FAIL: caesar 13 输出 '$out' != 'Uryyb'"
    exit 1
}

# 4) wump -h 输出 Usage 用法文本（-h 打印用法后以非零退出码返回，
#    pipefail 下须先捕获输出再断言，参照 nbsdgames test.sh）
out=$("$BIN_DIR/wump" -h 2>&1) || true
printf '%s\n' "$out" | grep -q "^Usage:" || {
    echo "FAIL: wump -h 未输出 Usage: 用法文本"
    exit 1
}

echo "bsd 3.3: 21/21 断言通过"
exit 0