#!/data/service/hnp/bin/bash
# test_package/test.sh — ceccomp 真实消费者冒烟测试
# 在 conanrun 环境执行（PATH 含已安装 bin/，LD_LIBRARY_PATH 含依赖库路径）
# 用例命令（version 输出、asm/disasm 往返）2026-09-08 已在鸿蒙设备实测通过
set -eu

echo "[test] ceccomp version"
ceccomp version
ceccomp version | grep -q "ceccomp 4.2.2" || {
    echo "❌ ceccomp version output mismatch"
    exit 1
}
echo "✅ version OK"

# 往返产物落 conan build_folder（conanfile 传入 $1；OHOS 设备 /tmp 不可写）
D="${1:-$PWD}/rt-ceccomp"
rm -rf "$D"
mkdir -p "$D"

cat > "$D/in.text" <<'EOF'
#Label  CODE  JT   JF      K
#---------------------------------
 L0001: 0x20 0x00 0x00 0x00000008 $A = $low_pc
 L0002: 0x07 0x00 0x00 0x00000000 $X = $A
 L0003: 0x06 0x00 0x00 0x00000000 return KILL
EOF

echo "[test] asm -> raw -> disasm -> asm roundtrip"
ceccomp asm -a aarch64 -f raw "$D/in.text" > "$D/p1.raw"
ceccomp disasm -a aarch64 "$D/p1.raw" > "$D/out.text"
ceccomp asm -a aarch64 -f raw "$D/out.text" > "$D/p2.raw"
cmp "$D/p1.raw" "$D/p2.raw" || {
    echo "❌ asm/disasm roundtrip mismatch"
    exit 1
}
echo "✅ asm/disasm roundtrip OK"

rm -rf "$D"
echo "✅ ceccomp test_package PASSED"
