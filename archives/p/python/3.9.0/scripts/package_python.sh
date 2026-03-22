#!/bin/bash
# ============================================================
# Python 3.9.0 预编译版本打包脚本（带 rpath 处理）
# ============================================================
#
# 功能：
#   1. 收集 Python 运行时和依赖库
#   2. 修改 rpath 使库路径可移植
#   3. 创建自包含的打包目录
#
# 使用方法：
#   chmod +x package_python.sh
#   ./package_python.sh
#
# ============================================================

set -e

PYTHON_VERSION="3.9.0"
ARCH=$(uname -m)
PACKAGE_NAME="python-${PYTHON_VERSION}-harmonyos-${ARCH}"
INSTALL_DIR="$HOME/usr/local"
OUTPUT_DIR="$HOME/packages"
PACKAGE_DIR="$OUTPUT_DIR/$PACKAGE_NAME"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo "============================================================"
echo "Python ${PYTHON_VERSION} 预编译版本打包工具"
echo "============================================================"

# ============================================================
# 检查依赖工具
# ============================================================
check_tools() {
    local missing=()
    
    for tool in llvm-readelf llvm-objcopy llvm-strip patchelf; do
        if ! command -v $tool &> /dev/null; then
            missing+=($tool)
        fi
    done
    
    if [ ${#missing[@]} -gt 0 ]; then
        log_warn "缺少以下工具: ${missing[*]}"
        log_info "将尝试使用替代方案..."
    fi
}

# ============================================================
# 修改 rpath（使库路径可移植）
# ============================================================
set_rpath() {
    local file="$1"
    local rpath="$2"
    
    if command -v patchelf &> /dev/null; then
        patchelf --set-rpath "$rpath" "$file" 2>/dev/null || true
    else
        # 备用方案：使用 llvm-objcopy（需要更复杂的操作）
        log_warn "patchelf 不可用，跳过 rpath 设置: $file"
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
    for dir in /usr/lib /usr/lib64 /lib /lib64 $HOME/usr/local/lib; do
        if [ -f "$dir/$lib" ]; then
            echo "$dir/$lib"
            return 0
        fi
    done
    return 1
}

# ============================================================
# 收集依赖库
# ============================================================
collect_all_deps() {
    local deps=()
    local processed_libs=""
    
    # 处理一个文件的所有依赖
    process_file() {
        local file="$1"
        for lib in $(get_deps "$file"); do
            # 跳过系统库
            case "$lib" in
                libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*|libutil.so*)
                    continue
                    ;;
            esac
            
            # 跳过已处理的库
            if echo "$processed_libs" | grep -q "^$lib$"; then
                continue
            fi
            
            processed_libs="$processed_libs\n$lib"
            
            local lib_path=$(find_lib "$lib")
            if [ -n "$lib_path" ]; then
                deps+=("$lib_path")
                # 递归处理依赖的依赖
                process_file "$lib_path"
            fi
        done
    }
    
    # 处理 Python 可执行文件
    if [ -f "$PACKAGE_DIR/bin/python3.9" ]; then
        process_file "$PACKAGE_DIR/bin/python3.9"
    fi
    
    # 处理 libpython
    if [ -f "$PACKAGE_DIR/lib/libpython3.9.so.1.0" ]; then
        process_file "$PACKAGE_DIR/lib/libpython3.9.so.1.0"
    fi
    
    # 处理所有扩展模块
    find "$PACKAGE_DIR/lib/python3.9" -name "*.so" 2>/dev/null | while read so; do
        process_file "$so"
    done
    
    # 去重输出
    printf '%s\n' "${deps[@]}" | sort -u
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

# 复制并设置 rpath
cp "$INSTALL_DIR/bin/python3.9" "$PACKAGE_DIR/bin/"
chmod +x "$PACKAGE_DIR/bin/python3.9"

# 设置可执行文件的 rpath 指向相对路径
set_rpath "$PACKAGE_DIR/bin/python3.9" '$ORIGIN/../lib:$ORIGIN/../lib/external'

log_info "复制 Python 库文件..."
cp -P "$INSTALL_DIR/lib/libpython3.9.so"* "$PACKAGE_DIR/lib/" 2>/dev/null || true
cp -P "$INSTALL_DIR/lib/libpython3.so" "$PACKAGE_DIR/lib/" 2>/dev/null || true

# 设置共享库的 rpath
for lib in "$PACKAGE_DIR/lib"/libpython*.so*; do
    if [ -f "$lib" ]; then
        set_rpath "$lib" '$ORIGIN:$ORIGIN/external'
    fi
done

log_info "复制 Python 标准库..."
cp -r "$INSTALL_DIR/lib/python3.9" "$PACKAGE_DIR/lib/"

log_info "复制头文件..."
cp -r "$INSTALL_DIR/include/python3.9" "$PACKAGE_DIR/include/"

# ============================================================
# 处理扩展模块的 rpath
# ============================================================
log_info "处理扩展模块的 rpath..."
find "$PACKAGE_DIR/lib/python3.9" -name "*.so" | while read so; do
    set_rpath "$so" '$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
done

# ============================================================
# 收集并复制依赖库
# ============================================================
log_info "分析依赖库..."

copied_libs=""
copy_lib() {
    local lib_path="$1"
    local lib_name=$(basename "$lib_path")
    
    if echo "$copied_libs" | grep -q "$lib_name"; then
        return
    fi
    
    echo "  复制: $lib_name"
    cp -L "$lib_path" "$PACKAGE_DIR/lib/external/"
    copied_libs="$copied_libs $lib_name"
    
    # 设置依赖库的 rpath
    set_rpath "$PACKAGE_DIR/lib/external/$lib_name" '$ORIGIN'
}

# 分析 Python 可执行文件的依赖
for lib in $(get_deps "$PACKAGE_DIR/bin/python3.9"); do
    case "$lib" in
        libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*)
            continue
            ;;
    esac
    
    lib_path=$(find_lib "$lib")
    if [ -n "$lib_path" ]; then
        copy_lib "$lib_path"
    fi
done

# 分析 libpython 的依赖
if [ -f "$PACKAGE_DIR/lib/libpython3.9.so.1.0" ]; then
    for lib in $(get_deps "$PACKAGE_DIR/lib/libpython3.9.so.1.0"); do
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*)
                continue
                ;;
        esac
        
        lib_path=$(find_lib "$lib")
        if [ -n "$lib_path" ]; then
            copy_lib "$lib_path"
        fi
    done
fi

# 分析扩展模块的依赖
log_info "分析扩展模块依赖..."
find "$PACKAGE_DIR/lib/python3.9" -name "*.so" | while read so; do
    for lib in $(get_deps "$so"); do
        case "$lib" in
            libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*|librt.so*|libpython*)
                continue
                ;;
        esac
        
        lib_path=$(find_lib "$lib")
        if [ -n "$lib_path" ]; then
            # 检查是否已复制
            if [ ! -f "$PACKAGE_DIR/lib/external/$lib" ]; then
                echo "  复制扩展依赖: $lib"
                cp -L "$lib_path" "$PACKAGE_DIR/lib/external/"
                set_rpath "$PACKAGE_DIR/lib/external/$lib" '$ORIGIN'
            fi
        fi
    done
done

# ============================================================
# 创建启动脚本
# ============================================================
log_info "创建启动脚本..."

cat > "$PACKAGE_DIR/bin/python-wrapper.sh" << 'EOF'
#!/bin/bash
# Python 启动脚本 - 自动设置库路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
export LD_LIBRARY_PATH="$PACKAGE_DIR/lib:$PACKAGE_DIR/lib/external${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec "$SCRIPT_DIR/python3.9" "$@"
EOF
chmod +x "$PACKAGE_DIR/bin/python-wrapper.sh"

# 创建符号链接
cd "$PACKAGE_DIR/bin"
ln -sf python-wrapper.sh python
ln -sf python-wrapper.sh python3
ln -sf python3.9 python-config
cd - > /dev/null

# ============================================================
# 创建环境配置脚本
# ============================================================
cat > "$PACKAGE_DIR/activate.sh" << 'EOF'
#!/bin/bash
# 激活 Python 环境
PYTHON_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="$PYTHON_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$PYTHON_DIR/lib:$PYTHON_DIR/lib/external${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
alias python='python3.9'
echo "Python 3.9.0 环境已激活"
echo "使用 'deactivate' 退出环境（需要手动实现）"
EOF
chmod +x "$PACKAGE_DIR/activate.sh"

# ============================================================
# 创建使用说明
# ============================================================
cat > "$PACKAGE_DIR/README.md" << 'EOF'
# Python 3.9.0 预编译版本（HarmonyOS）

## 快速使用

```bash
# 解压
tar -xzf python-3.9.0-harmonyos-aarch64.tar.gz
cd python-3.9.0-harmonyos-aarch64

# 方法1：直接运行
./bin/python3.9 --version

# 方法2：激活环境（推荐）
source activate.sh
python --version
```

## 添加到系统

编辑 `~/.zshrc`：

```bash
# Python 3.9
export PATH=/path/to/python-3.9.0-harmonyos-aarch64/bin:$PATH
export LD_LIBRARY_PATH=/path/to/python-3.9.0-harmonyos-aarch64/lib:$LD_LIBRARY_PATH
```

## 目录结构

```
python-3.9.0-harmonyos-aarch64/
├── bin/           # 可执行文件
├── lib/           # Python 库
│   ├── python3.9/ # 标准库
│   └── external/  # 依赖库
├── include/       # 头文件
├── activate.sh    # 环境激活脚本
└── README.md
```

## 特性

- 内置 HarmonyOS 子进程兼容层
- 相对路径设计，可移植到任意目录
- 包含常用依赖库
EOF

# ============================================================
# 打包
# ============================================================
log_info "打包..."
mkdir -p "$OUTPUT_DIR"
cd "$OUTPUT_DIR"

tar -czf "${PACKAGE_NAME}.tar.gz" "$PACKAGE_NAME"
SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)

echo ""
echo "============================================================"
echo "打包完成！"
echo "============================================================"
echo ""
echo "输出文件: $OUTPUT_DIR/${PACKAGE_NAME}.tar.gz"
echo "文件大小: $SIZE"
echo ""
echo "验证方法："
echo "  cd $OUTPUT_DIR"
echo "  tar -xzf ${PACKAGE_NAME}.tar.gz"
echo "  cd ${PACKAGE_NAME}"
echo "  ./bin/python3.9 --version"
echo ""