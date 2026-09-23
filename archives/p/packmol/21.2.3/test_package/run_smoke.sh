#!/bin/sh
# packmol 冒烟测试（Conan L1 / 本地上游 shell 测试的可复现子集）。
# 用法: sh run_smoke.sh /path/to/packmol
#
# 注：packmol 不提供 --version/-h（未知命令行参数以码 174 退出，上游
#     test_cli.sh 同样只测 stdin/-i/-o 调用），因此以真实打包作为功能冒烟：
#     固定 seed 输入 -> 生成 PDB -> 断言标题/原子行/Success 标记。
set -e

pm="$1"
if [ -z "$pm" ] || [ ! -x "$pm" ]; then
    echo "ERROR: packmol executable not found: $pm"
    exit 1
fi

# 真实打包：固定 seed，stdin 输入 -> 当前目录生成 water_smoke.pdb
"$pm" < smoke.inp > smoke.log 2>&1 || {
    echo "ERROR: packmol run failed"
    tail -30 smoke.log
    exit 1
}

if [ ! -f water_smoke.pdb ]; then
    echo "ERROR: output water_smoke.pdb was not generated"
    cat smoke.log
    exit 1
fi
grep -q "TITLE     Built with Packmol" water_smoke.pdb || {
    echo "ERROR: PDB title header missing"; exit 1; }
grep -q "HETATM" water_smoke.pdb || {
    echo "ERROR: PDB contains no atoms"; exit 1; }
grep -q "Success!" smoke.log || {
    echo "ERROR: packmol did not report Success"; tail -30 smoke.log; exit 1; }

echo "SMOKE_OK"