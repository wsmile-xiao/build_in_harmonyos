#!/bin/sh
# test_cif_tools.sh — cif-tools 消费者验证脚本（L0c 真实测试源文件）
#
# 验证 cif-tools 产物可用（真实执行，R34 反空壳）：
#   ① 6 个可执行文件存在
#   ② 6 个工具 `--version` 均成功执行（rc=0）
#      —— 这是本包最关键的断言：工具为**动态链接**，能运行即证明
#         其全部共享库依赖（libcifpp / libmcfp / libfmt / libstdc++ 等）
#         在运行环境中可解析。实测该断言成功揪出过 libfmt.so.7 缺失
#         （Error loading shared library libfmt.so.7）问题。
#   ③ `--help` 输出用法文案（证明工具进入真实主流程，而非仅打印版本短路）
#
# 刻意**不**做真实 CIF 解析断言，理由（均实测）：
#   · cif-validate / mmcql 解析需要 mmcif_pdbx.dic 字典，该字典不在包内
#     （实测 `Could not load dictionary mmcif_pdbx.dic`, rc=1）；
#   · cif-diff 传两个文件会**启动 Vim 分页器**（实测 rc=124 挂起，
#     "Vim: Warning: Output is not to a terminal"）——CI 沙箱无 TTY，
#     不可作为断言。
# 用法：test_cif_tools.sh <pkg_dir>
set -euo pipefail

PKG="${1:-}"
if [ -z "$PKG" ] || [ ! -d "$PKG" ]; then
    echo "        [fail] 用法: test_cif_tools.sh <pkg_dir>（收到: '${PKG}'）"
    exit 1
fi

PROGS="pdb2cif cif2pdb cif-diff cif-merge cif-validate mmcql"

# ① 6 个可执行文件存在性
for p in $PROGS; do
    if [ ! -x "$PKG/bin/$p" ]; then
        echo "        [fail] $p 可执行文件缺失或不可执行"
        exit 1
    fi
done
echo "        [ok] 6 个可执行文件齐全（pdb2cif/cif2pdb/cif-diff/cif-merge/cif-validate/mmcql）"

# ② --version 真实执行（rc=0）——验证动态链接依赖全部可解析
#    stdin 接 /dev/null，避免任何工具等待输入
for p in $PROGS; do
    if ! out=$(timeout 15 "$PKG/bin/$p" --version </dev/null 2>&1); then
        echo "        [fail] $p --version 执行失败（共享库依赖可能缺失）"
        echo "        $out"
        exit 1
    fi
done
echo "        [ok] 6 个工具 --version 均成功执行（动态链接依赖可解析）"

# ③ --help 输出用法（进入真实主流程）
#    注意：cif2pdb 打印用法但退出码为 1（实测），故此处只校验**输出**
#    含用法关键字，不强制 rc=0。
for p in $PROGS; do
    out=$(timeout 15 "$PKG/bin/$p" --help </dev/null 2>&1 || true)
    case "$out" in
        *usage*|*"--help"*|*"[options"*) : ;;
        *)
            echo "        [fail] $p --help 未输出用法文案"
            echo "        $out"
            exit 1
            ;;
    esac
done
echo "        [ok] 6 个工具 --help 均输出用法文案"

echo "        [ok] cif-tools 消费者验证通过（6 可执行 + 真实执行 + 用法输出）"
exit 0
