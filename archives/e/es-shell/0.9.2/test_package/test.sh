#!/bin/sh
# es-shell smoke test: actually run the es binary (R34)
set -e
# 1) 简单命令执行
out=$(echo 'echo hello_from_es' | es)
[ "$out" = "hello_from_es" ] || { echo "FAIL: basic command"; exit 1; }
# 2) 变量 + 命令替换（es 语义：$x 展开 + `{...} 命令替换）
out=$(echo 'x = 40; echo $x `{echo 2}' | es)
[ "$out" = "40 2" ] || { echo "FAIL: var + cmd substitution"; exit 1; }
# 3) 函数定义与调用
out=$(echo 'fn f { echo fn_ok }; f' | es)
[ "$out" = "fn_ok" ] || { echo "FAIL: function"; exit 1; }
echo "es-shell smoke OK"
