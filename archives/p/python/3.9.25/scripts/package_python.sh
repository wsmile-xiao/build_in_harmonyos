#!/bin/env bash
# ============================================================
# Python 3.9.25 预编译版本打包脚本（HarmonyOS）
# ============================================================
#
# 功能：
#   1. 收集 Python 运行时和依赖库
#   2. 修改 rpath 使库路径可移植（使用 patchelf）
#   3. Strip debug 符号并分离保存（使用 llvm-objcopy）
#   4. 移除旧签名并重新签名（binary-sign-tool）
#   5. 创建自包含的打包目录（主包 + debug 包）
#
# 依赖工具：
#   - patchelf         (RPATH 修改)
#   - llvm-objcopy     (移除 .codesign 段、strip、debug 分离)
#   - binary-sign-tool (重新签名)
#   - llvm-readelf     (分析依赖)
#
# 使用方法：
#   chmod +x package_python.sh
#   ./package_python.sh
#
# 产物：
#   python-3.9.25-ohos-aarch64.tar.gz          # 主包（~207MB）
#   python-3.9.25-ohos-aarch64-debug.tar.gz     # Debug 符号包（~22MB）
#
# 注意事项：
#   - HarmonyOS 的 ELF 签名机制要求修改后的二进制必须重新签名
#   - binary-sign-tool 无法覆盖已有签名，必须先用 llvm-objcopy 移除
#   - 签名后权限会丢失，需要重新 chmod +x
#   - 首次运行需要用户在弹窗中确认
#   - 不能使用软链接（SELinux 限制），用 wrapper 脚本替代
#
# ============================================================

set -e

PYTHON_VERSION="3.9.25"
ARCH=$(uname -m)
PACKAGE_NAME="python-${PYTHON_VERSION}-ohos-${ARCH}"
INSTALL_DIR="$HOME/usr/local"
OUTPUT_DIR="$HOME/packages"
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME"

# 是否 strip（默认是）
STRIP_DEBUG="${STRIP_DEBUG:-1}"

# 工具路径

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================================"
echo "Python ${PYTHON_VERSION} 预编译版本打包工具 (HarmonyOS)"
echo "============================================================"

# ============================================================
# 修改 RPATH + Strip + 重新签名（完整流程）
#
# 关键流程：
#   1. patchelf --set-rpath              修改 RPATH（破坏签名）
#   2. llvm-objcopy --only-keep-debug   提取 debug info 到单独文件
#   3. llvm-objcopy --strip-debug       从主文件移除 debug sections
#   4. llvm-objcopy --add-gnu-debuglink 在主文件中添加指向 debug 文件的链接
#   5. llvm-objcopy --remove-section .codesign  移除旧签名段
#   6. binary-sign-tool sign -selfSign 1        重新签名
#   7. chmod +x                            恢复执行权限
#
# 说明：
#   - 步骤 2-4 仅在 STRIP_DEBUG=1 时执行
#   - .gnu_debuglink 使 GDB 能自动加载对应的 debug 文件
#   - debug 文件保存在 debug/ 子目录
#
# ============================================================
patch_strip_sign() {
    local quiet="${QUIET:-0}"
    local file="$1"
    local rpath="$2"
    local name=$(basename "$file")
    
    # Step 1: Set RPATH
    patchelf --set-rpath "$rpath" "$file" 2>/dev/null
    
    # Steps 2-4: Strip debug and extract (if enabled)
    if [ "$STRIP_DEBUG" = "1" ]; then
        # 确保 debug 目录存在（Bug 4 修复：避免写入不存在的目录导致静默失败）
        mkdir -p "$OUTPUT_DIR/${PACKAGE_NAME}.debug"
        local debug_file="$OUTPUT_DIR/${PACKAGE_NAME}.debug/${name}.debug"
        
        # Step 2: Extract debug info to separate file
        llvm-objcopy --only-keep-debug "$file" "$debug_file"
        
        # Step 3: Strip debug sections from main binary
        llvm-objcopy --strip-debug "$file" "$file.tmp"
        mv "$file.tmp" "$file"
        
        # Step 4: Add .gnu_debuglink section (GDB auto-load)
        llvm-objcopy --add-gnu-debuglink="$debug_file" "$file"
    fi
    
    # Step 5: Remove old .codesign section (required before re-signing)
    llvm-objcopy --remove-section .codesign "$file" 2>/dev/null || true
    
    # Step 6: Re-sign with adhoc self-sign
    binary-sign-tool sign -inFile "$file" -outFile "$file" -selfSign 1 >/dev/null 2>&1 || true
    
    # Step 7: Restore execute permission (signing removes it)
    chmod a+x "$file"
    
    if [ "$STRIP_DEBUG" = "1" ]; then
        local stripped_size=$(wc -c < "$file")
        if [ "$quiet" = "0" ]; then
            echo "  ✅ $name: $(numfmt --to=iec $stripped_size 2>/dev/null || echo $stripped_size) (stripped)"
        fi
    else
        if [ "$quiet" = "0" ]; then echo "  ✅ $name"; fi
    fi
}

# ============================================================
# 获取依赖库列表
# ============================================================
get_deps() {
    local file="$1"
    llvm-readelf -d "$file" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/' || true
}

# ============================================================
# 查找库文件
# ============================================================
find_lib() {
    local lib="$1"
    for dir in "$INSTALL_DIR/lib" /data/service/hnp/lib /usr/lib /usr/lib64 /lib /lib64; do
        if [ -f "$dir/$lib" ]; then
            echo "$dir/$lib"
            return 0
        fi
    done
    return 1
}

# ============================================================
# 主流程
# ============================================================

# 检查 Python 是否已安装
if [ ! -f "$INSTALL_DIR/bin/python3.9" ]; then
    log_error "Python 未安装到 $INSTALL_DIR"
    log_info "请先完成 Python 编译和安装"
    exit 1
fi


# 创建打包目录
log_info "创建打包目录: $PACKAGE_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"/{bin,lib/external,include}
mkdir -p "$OUTPUT_DIR/${PACKAGE_NAME}.debug"

# ============================================================
# 复制 Python 运行时
# ============================================================
log_info "复制 Python 可执行文件..."
cp "$INSTALL_DIR/bin/python3.9" "$PACKAGE_DIR/bin/"
cp "$INSTALL_DIR/bin/python3.9-config" "$PACKAGE_DIR/bin/"

# ⚠️ HarmonyOS: 不使用软链接（SELinux 限制），用 wrapper 脚本替代
for alias in python python3; do
    cat > "$PACKAGE_DIR/bin/$alias" << WEOF
#!/bin/sh
SELF_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec "\$SELF_DIR/python3.9" "\$@"
WEOF
    chmod +x "$PACKAGE_DIR/bin/$alias"
done

for alias in python-config python3-config; do
    cat > "$PACKAGE_DIR/bin/$alias" << WEOF
#!/bin/sh
SELF_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec "\$SELF_DIR/python3.9-config" "\$@"
WEOF
    chmod +x "$PACKAGE_DIR/bin/$alias"
done

log_info "复制 Python 共享库..."
# ⚠️ HarmonyOS: 复制为真实文件，不使用软链接
cp "$INSTALL_DIR/lib/libpython3.9.so.1.0" "$PACKAGE_DIR/lib/"
cp "$INSTALL_DIR/lib/libpython3.9.so.1.0" "$PACKAGE_DIR/lib/libpython3.9.so"

log_info "复制 Python 标准库..."
cp -r "$INSTALL_DIR/lib/python3.9" "$PACKAGE_DIR/lib/"

log_info "复制头文件..."
cp -r "$INSTALL_DIR/include/python3.9" "$PACKAGE_DIR/include/" 2>/dev/null || true

# ============================================================
# 收集并复制外部依赖库
# ============================================================
log_info "分析外部依赖库..."

copied_libs=""
copy_lib() {
    local lib_path="$1"
    local lib_name=$(basename "$lib_path")
    
    if echo "$copied_libs" | grep -q "^$lib_name$"; then
        return
    fi
    
    log_info "  复制外部依赖: $lib_name"
    cp -L "$lib_path" "$PACKAGE_DIR/lib/external/"
    copied_libs="$copied_libs $lib_name"
}

# 分析所有 ELF 文件的依赖
for elf_file in "$PACKAGE_DIR/bin/python3.9" "$PACKAGE_DIR/lib/libpython3.9.so.1.0"; do
    for lib in $(get_deps "$elf_file"); do
        # 跳过系统库和 libpython
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*|libutil.so*|libpython*)
                continue
                ;;
        esac
        
        lib_path=$(find_lib "$lib")
        if [ -n "$lib_path" ]; then
            copy_lib "$lib_path"
        fi
    done
done

# 分析扩展模块的依赖（Bug 1+2+3+5 修复：
#   - 使用 $OUTPUT_DIR/.needed_tmp_$$ 替代 mktemp（/tmp 只读问题）
#   - 使用 find -exec 替代 find | while read（避免管道子 shell 变量丢失）
#   - 内联 ELF 魔数检测（避免函数在子 shell 中不可见）
#   - 使用精确文件存在检查替代 find 搜索（避免误匹配）
#）
NEEDED_TMP="$OUTPUT_DIR/.needed_tmp_$$"
trap 'rm -f "$NEEDED_TMP"' EXIT

find "$PACKAGE_DIR/lib/python3.9/lib-dynload" -name "*.so" -type f -exec sh -c '
    # 内联 ELF 魔数检测（Bug 3 修复：不依赖 is_elf 函数）
    magic=$(head -c 4 "$1" 2>/dev/null | od -A n -t x1 | tr -d " ")
    [ "$magic" = "7f454c46" ] || exit 0
    llvm-readelf -d "$1" 2>/dev/null | grep NEEDED | sed "s/.*\[\(.*\)\].*/\1/"
' _ {} \; 2>/dev/null | sort -u > "$NEEDED_TMP"

# 在主 shell 中处理（变量作用域安全，无子 shell 问题）
while IFS= read -r lib; do
    [ -z "$lib" ] && continue
    # 跳过系统库和 libpython
    case "$lib" in
        libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*|libutil.so*|libpython*)
            continue
            ;;
    esac
    # 跳过已收集的外部依赖
    [ -f "$PACKAGE_DIR/lib/external/$lib" ] && continue
    # 跳过包内已有库（Bug 5 修复：使用精确文件存在检查替代 find -maxdepth）
    [ -f "$PACKAGE_DIR/lib/$lib" ] && continue

    lib_path=$(find_lib "$lib")
    if [ -n "$lib_path" ]; then
        log_info "  复制扩展依赖: $lib"
        cp -L "$lib_path" "$PACKAGE_DIR/lib/external/"
    fi
done < "$NEEDED_TMP"
rm -f "$NEEDED_TMP"
unset NEEDED_TMP

# ============================================================
# 设置 RPATH 并重新签名所有 ELF 文件
# ============================================================
log_info "设置 RPATH 并重新签名 ELF 文件..."
log_warn "每个文件首次运行需要用户在弹窗中确认"

echo "  1. bin/python3.9"
patch_strip_sign "$PACKAGE_DIR/bin/python3.9" '$ORIGIN/../lib:$ORIGIN/../lib/external'

echo "  2. lib/libpython3.9.so.1.0"
patch_strip_sign "$PACKAGE_DIR/lib/libpython3.9.so.1.0" '$ORIGIN:$ORIGIN/external'

echo "  3. lib/libpython3.9.so"
patch_strip_sign "$PACKAGE_DIR/lib/libpython3.9.so" '$ORIGIN:$ORIGIN/external'

# 外部依赖库
ext_count=3
for ext_lib in "$PACKAGE_DIR/lib/external/"*.so*; do
    [ -f "$ext_lib" ] || continue
    ext_count=$((ext_count + 1))
    echo "  $ext_count. lib/external/$(basename $ext_lib)"
    patch_strip_sign "$ext_lib" '$ORIGIN'
done

# 扩展模块（设置 RPATH 以确保外部依赖库能被正确找到）
EXT_DYNLOAD_TOTAL=$(find "$PACKAGE_DIR/lib/python3.9/lib-dynload" -name "*.so" -type f 2>/dev/null | wc -l | tr -d " ")
EXT_DYNLOAD_COUNT=0
log_info "扩展模块: 0 / $EXT_DYNLOAD_TOTAL ..."
for dynload_so in "$PACKAGE_DIR/lib/python3.9/lib-dynload/"*.so; do
    [ -f "$dynload_so" ] || continue
    EXT_DYNLOAD_COUNT=$((EXT_DYNLOAD_COUNT + 1))
    printf "\r  处理扩展模块: %d / %d (%s)   " "$EXT_DYNLOAD_COUNT" "$EXT_DYNLOAD_TOTAL" "$(basename $dynload_so)"
    QUIET=1
    patch_strip_sign "$dynload_so" '$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
done
echo ""
log_info "扩展模块: 完成，共 $EXT_DYNLOAD_COUNT 个"

# ============================================================
# 统一修复执行权限（Bug 6 修复：Step 8）
#
# ⚠️ 关键：binary-sign-tool 签名后会重置权限位为 umask 默认值
# 即使之前 chmod a+x 也会被覆盖。必须在所有签名完成后统一修复！
# 使用进程替代 < <() 避免管道子 shell 变量丢失问题
# ============================================================
log_info "统一修复 ELF 文件执行权限 ..."

FIXED_COUNT=0
MISSING_COUNT=0

# 对所有 ELF 文件添加执行权限（使用进程替代避免子 shell）
while IFS= read -r -d '' elf; do
    # 内联 ELF 魔数检测（Bug 3 修复：不依赖 is_elf 函数）
    magic=$(head -c 4 "$elf" 2>/dev/null | od -A n -t x1 | tr -d ' ')
    if [ "$magic" = "7f454c46" ] && [ ! -x "$elf" ]; then
        chmod +x "$elf"
        FIXED_COUNT=$((FIXED_COUNT + 1))
    fi
done < <(find "$PACKAGE_DIR" -type f -print0 2>/dev/null)

# bin/ 下的脚本也确保有执行权限
find "$PACKAGE_DIR/bin" -type f ! -executable -exec chmod +x {} \; 2>/dev/null || true

# 权限验证
log_info "验证执行权限 ..."
NO_EXE_COUNT=0
NO_EXE_LIST=""
while IFS= read -r -d '' elf; do
    magic=$(head -c 4 "$elf" 2>/dev/null | od -A n -t x1 | tr -d ' ')
    if [ "$magic" = "7f454c46" ] && [ ! -x "$elf" ]; then
        NO_EXE_COUNT=$((NO_EXE_COUNT + 1))
        NO_EXE_LIST="$NO_EXE_LIST $(basename "$elf")"
    fi
done < <(find "$PACKAGE_DIR" -type f -print0 2>/dev/null)

if [ "$NO_EXE_COUNT" -gt 0 ]; then
    log_error "仍有 $NO_EXE_COUNT 个 ELF 文件缺少执行权限:$NO_EXE_LIST"
    log_error "这将导致用户解压 tar.gz 后 Permission denied！"
    exit 1
else
    log_info "所有 ELF 文件均有执行权限（已修复 $FIXED_COUNT 个）"
fi

# ============================================================
# 创建使用说明
# ============================================================
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Python 3.9.25 预编译版本（HarmonyOS aarch64）

## 快速使用

```bash
# 方式一：一键安装（推荐）
CURL_CA_BUNDLE=/etc/ssl/certs/cacert.pem /bin/sh -c "$(curl -fsSL --cacert /etc/ssl/certs/cacert.pem https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release/releases/download/3.9.25/install.sh)"

# 方式二：手动安装
tar -xzf python-3.9.25-ohos-aarch64.tar.gz -C ~/usr/

# 将以下内容添加到 ~/.bashrc 和 ~/.zshrc
export PATH="$HOME/usr/python-3.9.25-ohos-aarch64/bin:$PATH"
export TMPDIR="${TMPDIR:-$HOME/tmp}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/cacert.pem}"

source ~/.bashrc
python3.9 --version
```

## 目录结构

```
python-3.9.25-ohos-aarch64/
├── bin/                    # 可执行文件
│   ├── python3.9           # Python 解释器（RPATH 已设置）
│   ├── python / python3    # Wrapper 脚本
│   └── python3.9-config    # 编译配置脚本
├── lib/                    # Python 库
│   ├── libpython3.9.so*    # 共享库（RPATH 已设置）
│   ├── python3.9/          # 标准库
│   │   ├── lib-dynload/    # 扩展模块（大部分静态链接）
│   │   └── _harmonyos_compat.py  # 子进程兼容层
│   └── external/           # 外部依赖库
│       ├── libgdbm.so.6
│       ├── libgdbm_compat.so.4
│       └── liblzma.so.5
├── include/                # 头文件
└── README.md
```

## 特性

- ✅ RPATH 使用 $ORIGIN 相对路径，可移植到任意目录
- ✅ 所有 ELF 文件已重新签名（adhoc self-sign）
- ✅ 内置 HarmonyOS 子进程兼容层（subprocess 自动走 posix_spawn）
- ✅ 大部分扩展模块静态链接，外部依赖仅 3 个库
- ✅ 不使用软链接（用 wrapper 脚本替代，避免 SELinux 限制）

## 已知限制

- 首次运行每个二进制需要用户弹窗确认
- SSL 证书验证需要设置 SSL_CERT_FILE 环境变量
- ptrace 被 SELinux 禁止（调试受限）
- multiprocessing spawn 模式可用但不稳定，fork/forkserver 受限

## 打包信息

- 依赖库仅 3 个：libgdbm.so.6, libgdbm_compat.so.4, liblzma.so.5
- 其余扩展模块（ssl, hashlib, ctypes, zlib, readline, curses 等）均为静态链接
- 签名流程：patchelf → llvm-objcopy --remove-section .codesign → binary-sign-tool
EOF

# ============================================================
# 打包
# ============================================================
log_info "打包主包..."
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# 主包
tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)
log_info "  主包: ${PACKAGE_NAME}.tar.gz ($SIZE)"

# Debug 符号包（debug 目录在 output 下，独立于主包）
if [ "$STRIP_DEBUG" = "1" ] && [ -d "$OUTPUT_DIR/${PACKAGE_NAME}.debug" ]; then
    tar -czf "${PACKAGE_NAME}-debug.tar.gz" -C "$OUTPUT_DIR" "${PACKAGE_NAME}.debug"
    DEBUG_SIZE=$(du -h "${PACKAGE_NAME}-debug.tar.gz" | cut -f1)
    log_info "  Debug: ${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE)"
fi

echo ""
echo "============================================================"
echo "✅ 打包完成！"
echo "============================================================"
echo ""
echo "📦 产物:"
echo ""
echo "  主包:   $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz ($SIZE)"
if [ -n "$DEBUG_SIZE" ]; then
    echo "  Debug:  $OUTPUT_DIR/${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE)"
fi
echo ""
echo "📊 统计:"
echo ""
EXT_COUNT=$(find "$PACKAGE_DIR/lib/python3.9/lib-dynload" -name "*.so" -type f 2>/dev/null | wc -l | tr -d " ")
LIB_COUNT=$(find "$PACKAGE_DIR/lib/external" -name "*.so*" -type f 2>/dev/null | wc -l | tr -d " ")
DEBUG_COUNT=$(find "$OUTPUT_DIR/${PACKAGE_NAME}.debug" -type f 2>/dev/null | wc -l | tr -d " ")
ELF_TOTAL=$((3 + EXT_COUNT + LIB_COUNT))
echo "  ELF 文件:   $ELF_TOTAL 个（python3.9 + libpython3.9.so*2 + $EXT_COUNT 扩展模块 + $LIB_COUNT 外部依赖）"
echo "  Debug 符号: $DEBUG_COUNT 个"
echo "  扩展模块:   $EXT_COUNT 个（lib-dynload）"
echo "  外部依赖:   $LIB_COUNT 个（lib/external）"
echo ""
echo "📋 安装路径: ~/usr/${PACKAGE_NAME}/"
echo ""
echo "⚡ 快速安装:"
echo ""
echo "  tar -xzf ${PACKAGE_NAME}.tar.gz -C ~/usr/"
echo "  echo 'export PATH=\"\$HOME/usr/${PACKAGE_NAME}/bin:\$PATH\"' >> ~/.bashrc"
echo "  echo 'export PATH=\"\$HOME/usr/${PACKAGE_NAME}/bin:\$PATH\"' >> ~/.zshrc"
echo "  source ~/.bashrc && python3.9 --version"
echo ""
echo "🚀 一键安装（推荐）:"
echo ""
echo '  CURL_CA_BUNDLE=/etc/ssl/certs/cacert.pem /bin/sh -c "$(curl -fsSL --cacert /etc/ssl/certs/cacert.pem https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release/releases/download/3.9.25/install.sh)"'
echo ""
