#!/bin/sh
# dropbear test_package 冒烟测试（真实执行被测产物，无需网络与特权端口）:
#   1. 四个可执行文件存在;
#   2. dropbearkey 生成 ed25519 密钥并导出公钥;
#   3. dropbearconvert dropbear->openssh->dropbear 往返后与原私钥逐字节一致;
#   4. dropbear/dropbearkey/dbclient usage 路径退出码为 0。
# 用法: sh test_dropbear.sh <package_folder> <scratch_dir>
set -eu

PACKAGE_FOLDER="$1"
SCRATCH="$2"
TEST_DIR="$SCRATCH/dropbear-tp-$$"

mkdir -p "$TEST_DIR"
trap 'rm -rf "$TEST_DIR"' EXIT HUP INT TERM

# 拷贝到可写目录再执行（HMDFS 上对包目录内直执行更可靠的做法）
for sub in bin sbin; do
    for bin in dropbear dropbearkey dropbearconvert dbclient; do
        src="$PACKAGE_FOLDER/$sub/$bin"
        if [ -f "$src" ]; then
            cp "$src" "$TEST_DIR/$bin"
            chmod 755 "$TEST_DIR/$bin"
        fi
    done
done

# 1. 存在性
for bin in dropbear dropbearkey dropbearconvert dbclient; do
    if [ ! -f "$TEST_DIR/$bin" ]; then
        echo "ERROR: missing packaged command: $bin" >&2
        exit 1
    fi
done
echo "tp1: all four packaged commands present: OK"

# 2. ed25519 密钥生成 + 公钥导出
"$TEST_DIR/dropbearkey" -t ed25519 -f "$TEST_DIR/key_ed25519" > "$TEST_DIR/keygen.log" 2>&1
if [ ! -s "$TEST_DIR/key_ed25519" ]; then
    echo "ERROR: dropbearkey did not produce a key file" >&2
    exit 1
fi
"$TEST_DIR/dropbearkey" -y -f "$TEST_DIR/key_ed25519" > "$TEST_DIR/pubkey.txt" 2>/dev/null
grep -q "ssh-ed25519" "$TEST_DIR/pubkey.txt"
echo "tp2: dropbearkey ed25519 generate + public key export: OK"

# 3. 密钥格式双向转换往返（私钥逐字节一致）
"$TEST_DIR/dropbearconvert" dropbear openssh "$TEST_DIR/key_ed25519" "$TEST_DIR/key.ossh" > /dev/null 2>&1
"$TEST_DIR/dropbearconvert" openssh dropbear "$TEST_DIR/key.ossh" "$TEST_DIR/key.back" > /dev/null 2>&1
cmp "$TEST_DIR/key_ed25519" "$TEST_DIR/key.back"
echo "tp3: dropbearconvert dropbear<->openssh roundtrip byte-identical: OK"

# 4. usage/帮助路径
"$TEST_DIR/dropbear" -h > /dev/null 2>&1
"$TEST_DIR/dropbearkey" -h > /dev/null 2>&1
"$TEST_DIR/dbclient" -h > /dev/null 2>&1
echo "tp4: dropbear/dropbearkey/dbclient usage exit codes: OK"

echo "dropbear test_package smoke: OK"
