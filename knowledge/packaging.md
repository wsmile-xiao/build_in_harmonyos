# HarmonyOS 可移植打包指南

在鸿蒙系统上制作可移植的软件包，需要处理 RPATH、ELF 签名、软链接限制、权限修复等鸿蒙特有问题。

## 1. 核心问题

| 问题 | 根因 | 影响 | 解决方案 |
|------|------|------|----------|
| 修改 ELF 后无法执行 | adhoc 签名失效 | patchelf/strip 后二进制被内核拒绝 | 移除旧签名 → 重新签名 |
| 签名工具报 "section already exists" | 无法覆盖已有 .codesign 段 | 直接调用 binary-sign-tool 失败 | 先 llvm-objcopy 移除 |
| **tar 解压后无执行权限** | **binary-sign-tool 签名后重置权限位** | **解压后 Permission denied** | **tar 打包前统一 chmod +x（必做）** |
| 软链接不可靠 | SELinux 策略限制 | ln -s 创建的链接无法访问 | 用 wrapper 脚本或 cp 替代 |
| ln -sf 创建随机后缀文件 | toybox bug | ln -sf link → link_GdinNM | rm -f && ln -s 替代 |
| 运行时找不到共享库 | LD_LIBRARY_PATH 未设置或 RPATH 错误 | ImportError / 动态链接失败 | patchelf --set-rpath '$ORIGIN/...' |

---

## 2. 标准化可移植包制作流程（完整 10 步）

> 本流程综合 Python 3.9.25（strip+debug 分离）和 Python 3.12.9（独立安装+缓存清理）的最佳实践。
> **适用于所有 C/C++/Python 软件的可移植打包。**

### 流程概览

```
Step 1: 安装到独立目录
Step 2: 清理缓存和非必要文件
Step 3: 符号链接替换（wrapper/cp）
Step 4: 收集外部依赖库到 lib/external/
Step 5: 设置 RPATH（$ORIGIN 相对路径）
Step 6: Strip debug 符号 + 分离保存
Step 7: ELF 签名（adhoc self-sign）
Step 8: ⭐ 统一修复执行权限（必做！）
Step 9: 创建 activate.sh / README.md
Step 10: 打包 tar.gz（主包 + debug 包）
```

### Step 1: 安装到独立目录

```bash
# 从源码 make install 到全新目录（不污染系统）
PKGDIR="/path/to/output/${PACKAGE_NAME}"
rm -rf "$PKGDIR"
mkdir -p "$PKGDIR"

cd /path/to/source
MAKEFLAGS="-j1" make install prefix="$PKGDIR"
```

**要点**：使用独立前缀，不使用系统 `/usr/local`，确保纯净。

### Step 2: 清理缓存和非必要文件

```bash
# 2a. 清除 Python 字节码缓存（__pycache__ / *.pyc）
find "$PKGDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
find "$PKGDIR" -name '*.pyc' -delete 2>/dev/null || true
find "$PKGDIR" -name '*.pyo' -delete 2>/dev/null || true

# 2b. 删除 .bak 备份文件
find "$PKGDIR" -name '*.bak' -delete 2>/dev/null || true

# 2c. （可选）删除 pip 等非标准库内容（如需纯净版）
rm -rf "$PKGDIR/lib/python*/site-packages/pip"* 2>/dev/null || true
rm -f "$PKGDIR/bin/pip"* "$PKGDIR/bin/easy_install"* 2>/dev/null || true

# 2d. （可选）删除测试套件（节省空间，但保留 ensurepip wheel）
# find "$PKGDIR/lib/python*/test" -type d -exec rm -rf {} + 2>/dev/null || true
```

### Step 3: 符号链接替换

鸿蒙 SELinux 限制用户进程创建和访问软链接。

```bash
# 3a. bin/ 下的可执行文件别名 → wrapper 脚本
for alias in python3 python3-config pip3; do
    target_file="$PKGDIR/bin/${alias}.12"  # 实际目标文件名按实际情况调整
    if [ -L "$PKGDIR/bin/$alias" ]; then
        rm -f "$PKGDIR/bin/$alias"
        cat > "$PKGDIR/bin/$alias" << EOF
#!/bin/sh
SELF_DIR="\$(cd "\$(dirname "\$0")" && pwd)"
exec "\$SELF_DIR/$(basename $(readlink -f $target_file 2>/dev/null || echo ${alias}.12))" "\$@"
EOF
        chmod +x "$PKGDIR/bin/$alias"
    fi
done

# 3b. lib/ 下的共享库别名 → cp 复制
while IFS= read -r symlink; do
    target=$(readlink "$symlink")
    rm -f "$symlink"
    cp -p "$(dirname "$symlink")/$target" "$symlink"
done < <(find "$PKGDIR/lib" -type l ! -path '*/lib-dynload/*')

# 3c. pkgconfig/man 等其他位置 → cp 复制
find "$PKGDIR" -type l | while read link; do
    target=$(readlink "$link")
    rm -f "$link"
    cp -p "$(dirname "$link")/$target" "$link"
done
```

**验证**：`find "$PKGDIR" -type l | wc -l` 应为 0。

### Step 4: 收集外部依赖库到 lib/external/（⭐ 必做）

这是最关键的一步。ELF 文件的 NEEDED 库如果不在系统默认路径中，必须打包进去。

```bash
# 工具定义
READELF="/data/service/hnp/bin/llvm-readelf"

# 搜索路径（按优先级）
LIB_SEARCH_DIRS=(
    "/storage/Users/currentUser/usr/local/lib"
    "/data/service/hnp/lib"
    "/usr/lib" "/usr/lib64"
    "/lib" "/lib64"
)

# 排除的系统 musl 库（不需要打包）
SKIP_LIBS="^libc\.so|^libm\.so|^libdl\.so|^libpthread\.so|^ld-.*\.so|^librt\.so|^libutil\.so|^libpython"

mkdir -p "$PKGDIR/lib/external"

# 分析主可执行文件的依赖
collect_deps() {
    local elf_file="$1"
    local depth="${2:-0}"

    for lib in $($READELF -d "$elf_file" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/'); do
        # 跳过系统库
        echo "$lib" | grep -qE "$SKIP_LIBS" && continue
        # 跳过已收集的
        [ -f "$PKGDIR/lib/external/$lib" ] && continue
        # 跳过包内已有的（libpython 等）
        [ -f "$PKGDIR/lib/$lib" ] && continue
        [ -f "$PKGDIR/lib/python"*/"$lib" ] && continue

        # 在搜索路径中查找
        for search_dir in "${LIB_SEARCH_DIRS[@]}"; do
            if [ -f "$search_dir/$lib" ]; then
                echo "  📦 收集外部依赖: $lib"
                cp -L "$search_dir/$lib" "$PKGDIR/lib/external/"
                # 递归分析该依赖库自身的依赖（depth<2 防止循环）
                if [ "$depth" -lt 2 ]; then
                    collect_deps "$PKGDIR/lib/external/$lib" $((depth+1))
                fi
                break
            fi
        done
    done
}

echo "=== 收集外部依赖库 ==="
# 主程序
collect_deps "$PKGDIR/bin/main_executable"
# 主共享库
collect_deps "$PKGDIR/lib/libmain.so"
# 扩展模块
find "$PKGDIR" -path '*/lib-dynload/*.so' -type f | while read so; do collect_deps "$so"; done

echo "=== 外部依赖清单 ==="
ls -lh "$PKGDIR/lib/external/"
```

**常见外部依赖示例**：

| 库名 | 用途 | 来源软件 |
|------|------|---------|
| libffi.so.* | ctypes FFI 支持 | libffi |
| libgdbm.so.* | dbm/gdbm 数据库 | gdbm |
| liblzma.so.* | lzma/xz 压缩 | xz-utils |
| libreadline.so.* | 交互式命令行输入 | readline |
| libncursesw.so.* | 终端 UI (curses) | ncurses |
| libssl.so.* / libcrypto.so.* | SSL/TLS 支持 | openssl |
| libsqlite3.so.* | SQLite 数据库 | sqlite |
| libbz2.so.* | bzip2 压缩 | bzip2 |

### Step 5: 设置 RPATH（$ORIGIN 相对路径）

```bash
PATCHELF="/data/service/hnp/bin/patchelf"

set_rpath() {
    local file="$1"
    local rpath="$2"
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null
}

# RPATH 规则表
set_rpath "$PKGDIR/bin/main_executable"       '$ORIGIN/../lib:$ORIGIN/../lib/external'
set_rpath "$PKGDIR/lib/libmain.so"             '$ORIGIN:$ORIGIN/external'
set_rpath "$PKGDIR/lib/libmain.so.versioned"   '$ORIGIN:$ORIGIN/external'

# 扩展模块
find "$PKGDIR" -path '*/lib-dynload/*.so' -type f | while read so; do
    set_rpath "$so" '$ORIGIN:$ORIGIN/..:$ORIGIN/../external'
done

# 外部依赖库
find "$PKGDIR/lib/external" -type f | while read ext; do
    set_rpath "$ext" '$ORIGIN'
done
```

### Step 6: Strip Debug 符号 + 分离保存

```bash
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
DEBUG_DIR="/path/to/output/${PACKAGE_NAME}.debug"
rm -rf "$DEBUG_DIR"; mkdir -p "$DEBUG_DIR"

strip_debug() {
    local file="$1"
    local name=$(basename "$file")
    local debug_file="$DEBUG_DIR/${name}.debug"

    # 提取 debug 信息到单独文件
    $OBJCOPY --only-keep-debug "$file" "$debug_file"

    # 从主文件移除 debug sections
    $OBJCOPY --strip-debug "$file" "${file}.tmp"
    mv "${file}.tmp" "$file"

    # 添加 .gnu_debuglink（GDB 自动加载 debug 文件）
    $OBJCOPY --add-gnu_debuglink="$debug_file" "$file"
}

# 对所有 ELF 文件执行 strip
elf_count=0
for elf in $(find "$PKGDIR" -type f -exec file {} \; | grep 'ELF' | cut -d: -f1); do
    elf_count=$((elf_count + 1))
    printf "\r  Strip [%d] %s" "$elf_count" "$(basename "$elf")"
    strip_debug "$elf"
done
echo ""
echo "  共处理 $elf_count 个 ELF 文件"
```

### Step 7: ELF 签名（adhoc self-sign）

```bash
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"

sign_elf() {
    local file="$1"
    # 移除旧签名段（必须先做，否则 sign 报错）
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true
    # 重新签名
    $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null || true
}

for elf in $(find "$PKGDIR" -type f -exec file {} \; | grep 'ELF' | cut -d: -f1); do
    sign_elf "$elf"
done
```

### Step 8: ⭐ 统一修复执行权限（必做！）

> **⚠️ 关键发现**：HarmonyOS 的 `binary-sign-tool` 签名后会将文件权限重置为 `rw-rw----`（660），即使之前 `chmod a+x` 也会被覆盖。因此 **必须在签名完成后、tar 打包前，统一对所有 ELF 文件恢复执行权限**。否则用户解压 tar.gz 后会遇到 `Permission denied`。

```bash
# ============================================================
# Step 8: 统一修复执行权限（必做！不可跳过！）
# ============================================================
# 根因：binary-sign-tool 签名后重置权限位为 660（无执行权限）
# 如果跳过此步，用户解压 tar.gz 后所有 ELF 文件都无法执行

echo "=== 修复执行权限 ==="
fixed_count=0
missing_count=0

# 8a. 所有 ELF 文件添加执行权限
for elf in $(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -i 'ELF.*shared\|ELF.*executable\|ELF.*relocatable' | cut -d: -f1); do
    if [ -x "$elf" ]; then
        :  # 已有执行权限
    else
        chmod +x "$elf"
        fixed_count=$((fixed_count + 1))
    fi
done

# 8b. bin/ 下的脚本也确保有执行权限
find "$PKGDIR/bin" -type f ! -executable -exec chmod +x {} \; 2>/dev/null || true

echo "  修复了 $fixed_count 个文件的执行权限"

# 8c. 验证（必做检查项）
echo "=== 权限验证 ==="
no_exe=$(find "$PKGDIR" -type f -exec file {} \; 2>/dev/null | grep -i ELF | cut -d: -f1 | while read f; do
    [ -x "$f" ] || echo "$(basename $f)"
done | wc -l | tr -d ' ')

if [ "$no_exe" = "0" ]; then
    echo "  ✅ 所有 ELF 文件均有执行权限"
else
    echo "  ❌ 仍有 $no_exe 个 ELF 文件缺少执行权限！"
    exit 1
fi
```

### Step 9: 创建激活脚本和使用说明

```bash
# 9a. activate.sh（兼容 toybox ash，不用 ${BASH_SOURCE}）
cat > "$PKGDIR/activate.sh" << 'ACTEOF'
#!/bin/sh
# Portable activation script for HarmonyOS (toybox ash compatible)
if [ -n "$_OLD_PORTABLE_PATH" ]; then
    echo "Already activated."
    return 2>/dev/null || exit 0
fi
_PORTABLE_DIR="$(cd "$(dirname "$0")" && pwd)"
_OLD_PORTABLE_PATH="$PATH"
_OLD_LD_PATH="${LD_LIBRARY_PATH:-}"
export PATH="$_PORTABLE_DIR/bin:$PATH"
export LD_LIBRARY_PATH="$_PORTABLE_DIR/lib${_OLD_LD_PATH:+:$_OLD_LD_PATH}"
export PYTHONHOME="$_PORTABLE_DIR"  # Python 特有
[ -n "$PS1" ] && _OLD_PS1="$PS1" && export PS1="(portable) $PS1"
deactivate_portable() {
    export PATH="$_OLD_PORTABLE_PATH"
    export LD_LIBRARY_PATH="$_OLD_LD_PATH"
    unset PYTHONHOME
    [ -n "$_OLD_PS1" ] && export PS1="$_OLD_PS1" && unset _OLD_PS1
    unset _PORTABLE_DIR _OLD_PORTABLE_PATH _OLD_LD_PATH
    unset -f deactivate_portable
    echo "Deactivated."
}
echo "Activated: $_PORTABLE_DIR"
ACTEOF
chmod +x "$PKGDIR/activate.sh"

# 9b. README.md（含安装说明中的权限提示）
cat > "$PKGDIR/README.md" << REOF
# ${PACKAGE_NAME} for HarmonyOS

## Quick Start
\`\`\`bash
tar xzf ${PACKAGE_NAME}.tar.gz -C ~/usr/
find ${PACKAGE_NAME}/ -type f -name '*.so*' -exec chmod +x {} \;
chmod +x ${PACKAGE_NAME}/bin/*
. ~/${PACKAGE_NAME}/activate.sh
\`\`\`

> ⚠️ **解压后必须 chmod +x**（HarmonyOS 签名机制导致 tar 包内丢失执行权限）
REOF
```

### Step 10: 打包 tar.gz

```bash
OUTPUT_DIR="/path/to/output"
cd "$OUTPUT_DIR"

# 10a. 主包（不含 debug 目录）
tar -czf "${PACKAGE_NAME}.tar.gz" "$PKGDIR_NAME"
MAIN_SIZE=$(du -h "${PACKAGE_NAME}.tar.gz" | cut -f1)
echo "📦 主包: ${PACKAGE_NAME}.tar.gz ($MAIN_SIZE)"

# 10b. Debug 符号包（仅 debug 文件）
if [ -d "$DEBUG_DIR" ] && [ "$(ls -A "$DEBUG_DIR")" ]; then
    tar -czf "${PACKAGE_NAME}-debug.tar.gz" -C "$(dirname "$DEBUG_DIR")" "$(basename "$DEBUG_DIR")"
    DEBUG_SIZE=$(du -h "${PACKAGE_NAME}-debug.tar.gz" | cut -f1)
    echo "🔧 Debug: ${PACKAGE_NAME}-debug.tar.gz ($DEBUG_SIZE)"
fi

# 10c. 最终统计
echo ""
echo "=== 打包统计 ==="
echo "  总文件数: $(find "$PKGDIR" -type f | wc -l | tr -d ' ')"
echo "  ELF 文件: $(find "$PKGDIR" -type f -exec file {} \; | grep -ci elf)"
echo "  外部依赖: $(ls "$PKGDIR/lib/external/" 2>/dev/null | wc -l | tr -d ' ')"
echo "  残留符号链接: $(find "$PKGDIR" -type l | wc -l | tr -d ' ')"
```

---

## 3. 封装函数（可直接复用）

```bash
#!/bin/bash
# ============================================================
# HarmonyOS 可移植打包 — 一体化函数库
# ============================================================

PATCHELF="/data/service/hnp/bin/patchelf"
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"
READELF="/data/service/hnp/bin/llvm-readelf"

# --- RPATH + Strip + Sign 一体化 ---
process_elf() {
    local file="$1"
    local rpath="$2"
    local do_strip="${3:-1}"
    local debug_dir="${4:-}"

    # 1. Set RPATH
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null

    # 2-4. Strip + debug extract
    if [ "$do_strip" = "1" ] && [ -n "$debug_dir" ]; then
        local name=$(basename "$file")
        $OBJCOPY --only-keep-debug "$file" "${debug_dir}/${name}.debug"
        $OBJCOPY --strip-debug "$file" "${file}.tmp"
        mv "${file}.tmp" "$file"
        $OBJCOPY --add-gnu_debuglink="${debug_dir}/${name}.debug" "$file"
    fi

    # 5. Remove old sign
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true

    # 6. Re-sign
    $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null || true

    # 注意：chmod a+x 不在此处做！统一在 Step 8 批量处理
}
```

---

## 4. RPATH 设置原则

### 使用 `$ORIGIN` 相对路径

RPATH 使用 `$ORIGIN` 相对于文件自身位置查找库，使包可以放在任意目录：

```
package-name/
├── bin/
│   └── main_executable     RPATH: $ORIGIN/../lib:$ORIGIN/../lib/external
├── lib/
│   ├── libmain.so          RPATH: $ORIGIN:$ORIGIN/external
│   ├── package-name/       (Python 标准库等)
│   │   └── lib-dynload/
│   │       └── *.so        RPATH: $ORIGIN:$ORIGIN/..:$ORIGIN/../external
│   └── external/
│       ├── libffi.so.8     RPATH: $ORIGIN
│       └── liblzma.so.5    RPATH: $ORIGIN
```

| 文件类型 | 推荐 RPATH | 说明 |
|----------|-----------|------|
| 可执行文件 (bin/) | `$ORIGIN/../lib:$ORIGIN/../lib/external` | 向上查找 lib/ |
| 主共享库 (lib/libxxx.so) | `$ORIGIN:$ORIGIN/external` | 同级和 external/ |
| 扩展模块 (lib-dynload/*.so) | `$ORIGIN:$ORIGIN/..:$ORIGIN/../external` | 找 libpython 和 external |
| 外部依赖 (lib/external/) | `$ORIGIN` | 只找同级 |

### 可跳过的系统库（musl 提供，不需打包）

```
libc.so, libm.so, libdl.so, libpthread.so, ld-musl-*.so, librt.so, libutil.so
```

---

## 5. 软链接替代方案

### 可执行文件别名 → wrapper 脚本

```bash
cat > alias_name << 'EOF'
#!/bin/sh
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SELF_DIR/target_binary" "$@"
EOF
chmod +x alias_name
```

### 共享库别名 → cp 复制

```bash
cp real_library.so.1.0 library.so  # 多占磁盘但可靠
```

---

## 6. 权限问题详解

### 问题现象

```
$ ./python3.12
zsh: permission denied
$ ls -la python3.12
-rw-rw---- 1 user group 75520 ...   ← 无执行权限!
```

### 根因链

```
binary-sign-tool sign -inFile file -outFile file -selfSign 1
    ↓
签名工具内部操作:
    1. 写入 .codesign 段
    2. 调用内核签名接口
    3. 内核返回已签名文件
    ↓
副作用：文件权限被重置为 umask 默认值（通常是 0666 → rw-rw----）
    ↓
即使之前 chmod a+x 也被覆盖
```

### 解决方案

**不要在每个文件处理后单独 chmod**（会被后续签名覆盖），而是：

```bash
# ✅ 正确做法：所有 ELF 处理完毕后，统一批量 chmod
find "$PKGDIR" -type f -exec file {} \; | grep -i ELF | cut -d: -f1 | xargs chmod +x
find "$PKGDIR/bin" -type f ! -executable -exec chmod +x {} \;

# 然后（可选但推荐）验证
find "$PKGDIR" -type f -exec file {} \; | grep -i ELF | cut -d: -f1 | while read f; do
    [ -x "$f" ] || echo "❌ 缺少权限: $f"
done
```

### README 中必须告知用户

解压 tar.gz 后如果仍有问题：

```bash
# 用户侧兜底（写入 README.md Quick Start）
find package-dir/ -type f -name "*.so*" -exec chmod +x {} \;
chmod +x package-dir/bin/*
```

---

## 7. Strip 效果参考数据

| 软件 | Strip 前 (ELF) | Strip 后 (ELF) | 节省率 |
|------|----------------|----------------|--------|
| Python 3.9.0 | 14.4 MB | 4.7 MB | **67%** |
| Python 3.12.9 | 64.6 MB | 30.1 MB | **53%** |
| libpython3.x.so | 9.6→6.9 MB | 3.4→3.4 MB | **50-64%** |
| 外部依赖库 (~5个) | 1.0 MB | 0.94 MB | 6% |

> 标准 `.py` 文件占 87% 以上体积，无法通过 strip 减小。

---

## 8. 参考案例

| 软件 | 归档位置 | 特点 |
|------|----------|------|
| Python 3.9.25 | `archives/p/python/3.9.25/scripts/package_python.sh` | 首次建立流程（strip+debug） |
| Python 3.12.9 | `archives/p/python/3.12.9/manifest.yaml` → portable_package | 独立安装+缓存清理+纯净版 |

---

*文档版本: 2.0*
*最后更新: 2026-04-03*
*v2.0 更新：*
*  - 综合 3.9.25 + 3.12.9 最佳实践，建立 10 步标准化流程*
*  - 新增 Step 4: 外部依赖收集（必做）*
*  - 新增 Step 8: 统一权限修复（必做），含根因分析*
*  - 新增 §6: 权限问题详解（binary-sign-tool 签名重置权限根因）*
*  - 新增 Python 缓存清理步骤*
