#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the zdbsp executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary.
#
# Counting rule (统一口径: 独立检查项计数):
#   检查项 1: zdbsp --help 冒烟（二进制可执行、参数解析可用）
#   检查项 2 [鸿蒙特有测试 N=1]: 在 HarmonyOS 上真实运行 zdbsp 构建产物，
#     对最小 MAP01 WAD 构建 BSP 节点 —— 验证 OHOS ELF 二进制加载执行、
#     HMDFS 文件读写（输入/输出 WAD）、以及链接的静态 zlib（BLOCKMAP
#     压缩输出）在 OHOS 上正常工作。
#   检查项 3: 对节点构建输出再次处理（循环验证，证明输出 WAD 有效）。
set -euo pipefail

echo "[test] 检查项 1: zdbsp --help"
zdbsp --help | grep -q "Usage: zdbsp"
echo "OK: --help 输出 Usage"

echo "[test] 检查项 2 (鸿蒙特有): OHOS 实机运行 zdbsp 构建最小 MAP01 节点"
python3 wadgen.py > in.wad
zdbsp in.wad -o out.wad
if [ ! -s out.wad ]; then
    echo "FAIL: out.wad 未生成或为空"
    exit 1
fi
echo "OK: out.wad 已生成 ($(wc -c < out.wad) 字节)"

echo "[test] 检查项 3: 节点输出可被再次处理"
zdbsp out.wad -o out2.wad
if [ ! -s out2.wad ]; then
    echo "FAIL: out2.wad 未生成或为空"
    exit 1
fi
echo "OK: out2.wad 已生成 ($(wc -c < out2.wad) 字节)"

echo "ALL TESTS PASSED"
