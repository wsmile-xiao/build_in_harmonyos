#!/bin/bash
# ============================================================
# Python 3.9.0 预编译版本打包脚本（HarmonyOS）
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
#   python-3.9.0-harmonyos-aarch64.tar.gz          # 主包（~207MB）
#   python-3.9.0-harmonyos-aarch64-debug.tar.gz     # Debug 符号包（~22MB）
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

PYTHON_VERSION="3.9.0"
ARCH=$(uname -m)
PACKAGE_NAME="python-${PYTHON_VERSION}-harmonyos-${ARCH}"
INSTALL_DIR="$HOME/usr/local"
OUTPUT_DIR="$HOME/packages"
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME"

# 是否 strip（默认是）
STRIP_DEBUG="${STRIP_DEBUG:-1}"

# 工具路径
PATCHELF="${PATCHELF:-$(command -v patchelf || echo /data/service/hnp/bin/patchelf)}"
OBJCOPY="${OBJCOPY:-$(command -v llvm-objcopy || echo /data/service/hnp/bin/llvm-objcopy)}"
SIGNTOOL="${SIGNTOOL:-$(command -v binary-sign-tool || echo /data/service/hnp/bin/binary-sign-tool)}"
READELF="${READELF:-$(command -v llvm-readelf || echo /data/service/hnp/bin/llvm-readelf)}"

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
# 检查依赖工具
# ============================================================
check_tools() {
    local missing=()
    
    for tool in "$PATCHELF" "$OBJCOPY" "$SIGNTOOL" "$READELF"; do
        if [ ! -x "$tool" ]; then
            missing+=("$(basename $tool)")
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_error "缺少以下工具: ${missing[*]}"
        exit 1
    fi
    
    log_info "工具检查通过: patchelf, llvm-objcopy, binary-sign-tool, llvm-readelf"
}

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
    local file="$1"
    local rpath="$2"
    local name=$(basename "$file")
    
    # Step 1: Set RPATH
    "$PATCHELF" --set-rpath "$rpath" "$file" 2>/dev/null
    
    # Steps 2-4: Strip debug and extract (if enabled)
    if [ "$STRIP_DEBUG" = "1" ]; then
        local debug_file="$PACKAGE_DIR/debug/${name}.debug"
        
        # Step 2: Extract debug info to separate file
        "$OBJCOPY" --only-keep-debug "$file" "$debug_file"
        
        # Step 3: Strip debug sections from main binary
        "$OBJCOPY" --strip-debug "$file" "$file.tmp"
        mv "$file.tmp" "$file"
        
        # Step 4: Add .gnu_debuglink section (GDB auto-load)
        "$OBJCOPY" --add-gnu-debuglink="$debug_file" "$file"
    fi
    
    # Step 5: Remove old .codesign section (required before re-signing)
    "$OBJCOPY" --remove-section .codesign "$file" 2>/dev/null || true
    
    # Step 6: Re-sign with adhoc self-sign
    "$SIGNTOOL" sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null
    
    # Step 7: Restore execute permission (signing removes it)
    chmod a+x "$file"
    
    if [ "$STRIP_DEBUG" = "1" ]; then
        local stripped_size=$(wc -c < "$file")
        echo "  ✅ $name: $(numfmt --to=iec $stripped_size 2>/dev/null || echo $stripped_size) (stripped)"
    else
        echo "  ✅ $name"
    fi
}

# ============================================================
# 获取依赖库列表
# ============================================================
get_deps() {
    local file="$1"
    "$READELF" -d "$file" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/' || true
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

check_tools

# 创建打包目录
log_info "创建打包目录: $PACKAGE_DIR"
rm -rf "$PACKAGE_DIR"
mkdir -p "$PACKAGE_DIR"/{bin,lib/external,include}

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

# 分析扩展模块的依赖
find "$PACKAGE_DIR/lib/python3.9/lib-dynload" -name "*.so" 2>/dev/null | while read so; do
    for lib in $(get_deps "$so"); do
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*|libpython*)
                continue
                ;;
        esac
        
        lib_path=$(find_lib "$lib")
        if [ -n "$lib_path" ]; then
            lib_name=$(basename "$lib_path")
            if [ ! -f "$PACKAGE_DIR/lib/external/$lib_name" ]; then
                log_info "  复制扩展依赖: $lib_name"
                cp -L "$lib_path" "$PACKAGE_DIR/lib/external/"
            fi
        fi
    done
done

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
EXT_DYNLOAD_COUNT=0
EXT_DYNLOAD_TOTAL=$(find "$PACKAGE_DIR/lib/python3.9/lib-dynload" -name "*.so" -type f 2>/dev/null | wc -l)
for dynload_so in "$PACKAGE_DIR/lib/python3.9/lib-dynload/"*.so; do
    [ -f "$dynload_so" ] || continue
    EXT_DYNLOAD_COUNT=$((EXT_DYNLOAD_COUNT + 1))
    patch_strip_sign "$dynload_so" '$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
done
log_info "扩展模块: 已处理 $EXT_DYNLOAD_COUNT / $EXT_DYNLOAD_TOTAL 个"

# ============================================================
# 创建使用说明
# ============================================================
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Python 3.9.0 预编译版本（HarmonyOS aarch64）

## 快速使用

```bash
# 方式一：一键安装（推荐）
/bin/sh -c "$(curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/ohos-python-release/releases/download/python3.9/install.sh)"

# 方式二：手动安装
tar -xzf python-3.9.0-harmonyos-aarch64.tar.gz -C ~/usr/

# 将以下内容添加到 ~/.bashrc 和 ~/.zshrc
export PATH="$HOME/usr/python-3.9.0-harmonyos-aarch64/bin:$PATH"
export TMPDIR="${TMPDIR:-$HOME/tmp}"
export SSL_CERT_FILE="${SSL_CERT_FILE:-/etc/ssl/certs/ca-certificates.crt}"

source ~/.bashrc
python3.9 --version
```

## 目录结构

```
python-3.9.0-harmonyos-aarch64/
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
log_info "打包..."
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

# 主包（不含 debug）
tar -czf "${PACKAGE_NAME}.tar.gz" \
    --exclude="${PACKAGE_NAME}/debug" \
    "$PACKAGE_NAME"

if [ "$STRIP_DEBUG" = "1" ] && [ -d "$PACKAGE_DIR/debug" ]; then
    # Debug 符号包（单独分发）
    tar -czf "${PACKAGE_NAME}-debug.tar.gz" \
        "${PACKAGE_NAME}/debug"
    DEBUG_SIZE=$(du -h "${PACKAGE_NAME}-debug.tar.gz" | cut -f1)
fi

SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)

echo ""
echo "============================================================"
echo "打包完成！"
echo "============================================================"
echo ""
echo "产物:"
echo "  主包:   $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz ($SIZE)"
if [ -n "$DEBUG_SIZE" ]; then
echo "  Debug:  $OUTPUT_DIR/${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE)"
fi
echo ""
echo "使用方法："
echo "  tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "  # 安装脚本会自动配置 PATH 和环境变量"
echo "  ./bin/python3.9 --version    # 首次运行需确认弹窗"
echo "  source ~/.bashrc             # 或 source ~/.zshrc"
echo ""
echo "调试："
echo "  tar -xzf ${PACKAGE_NAME}-debug.tar.gz"
echo "  # debug/ 目录与主包目录同级，GDB 自动通过 .gnu_debuglink 加载"
echo ""
