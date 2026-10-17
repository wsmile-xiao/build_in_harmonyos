#!/bin/sh
# dmenu 5.4 consumer smoke test: 真实执行被测包安装的 dmenu 与 stest 二进制并断言行为。
# conanrun env 的 PATH 首位为包内 bin/，命令名解析到被测二进制（L1e 口径）。
# 用 set -eu 而非 set -euo pipefail：设备 toybox sh 无 pipefail，加了会直接报错退出。
set -eu

echo "--- dmenu 5.4 consumer verification ---"

# 1. dmenu -v 输出版本串（无显示环境可跑，dmenu.c:729 对 -v 直接 puts 后 exit 0）
v=$(dmenu -v)
echo "$v" | grep -q "^dmenu-5\.4$" || { echo "FAIL: dmenu -v unexpected output [$v]"; exit 1; }
echo "PASS 1: dmenu -v -> $v"

# 2. 伴生脚本/工具已安装且在 PATH 可解析（dmenu_path 运行期依赖 stest）
command -v dmenu_run  >/dev/null || { echo "FAIL: dmenu_run not installed";  exit 1; }
command -v dmenu_path >/dev/null || { echo "FAIL: dmenu_path not installed"; exit 1; }
command -v stest      >/dev/null || { echo "FAIL: stest not installed";      exit 1; }
echo "PASS 2: dmenu_run/dmenu_path/stest installed and resolvable"

# 3. stest 谓词断言：-f 对普通文件（stest 自身二进制）匹配，退出码 0（stest.c:108 return match?0:1）
b=$(command -v stest)
if stest -f "$b"; then
    echo "PASS 3: stest -f regular-file -> match(0)"
else
    echo "FAIL: stest -f rc=$?"
    exit 1
fi

# 4. stest 谓词断言：-d 对普通文件必须不匹配，退出码 1
if stest -d "$b"; then
    echo "FAIL: stest -d unexpectedly matched a regular file"
    exit 1
else
    echo "PASS 4: stest -d regular-file -> no-match(1)"
fi

echo "test dmenu 5.4: 4/4 checks PASS"
