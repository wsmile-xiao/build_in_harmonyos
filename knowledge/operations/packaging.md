# HarmonyOS 可移植打包指南

> **定位**：本文档是 SKILL.md Phase 4 Step 5.5（制作预编译分发包）的**详细操作手册**。
> 编译智能体在执行预编译包制作时，以本文档为 10 步流程的权威参考。
> 触发条件见 SKILL.md §Phase 4 Step 5.5。

在鸿蒙系统上制作可移植的软件包，需要处理 RPATH、ELF 签名、软链接限制、权限修复等鸿蒙特有问题。

<!-- ~~## 1. 核心问题~~ → 已迁移至各对应条目：E077(ELF签名), E042(RPATH), E046(签名后权限归零), E050/E018(软链接), E073(.so运行时) -->

---

## 1.5 tar.gz 内部结构规范（⭐ 必须遵守）

所有预编译包的 tar.gz **必须为扁平结构**：

```
{name}-{ver}-ohos-aarch64.tar.gz   ← 解压后顶层就是这些目录
├── bin/           # 可执行文件 (ELF, 已签名, 已 strip, 有执行权限)
│   ├── {name}     # 主二进制
│   └── ...
├── share/         # 文档和数据
│   └── man/
└── lib/           # 外部依赖库 (如有)
```

**禁止嵌套结构**（如 `pkg-config-0.29.2/bin/`）。打包命令必须从包含 `bin/` 的目录执行：
```bash
cd "$PKGDIR" && tar czf "output.tar.gz" *   # ✅ 扁平（自动包含 bin share lib）
# 而非: tar czf "output.tar.gz" "$PKGDIR"              # ❌ 可能多一层目录
```

**公共安装脚本依据此规范**：直接 `cp -r $TMP/bin $DST/`，无需检测嵌套结构。

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

> **⚠️ 签名工具稳定性问题**：`binary-sign-tool` 在某些情况下可能失败（权限不足、文件被占用、内部状态异常）。
> **必须使用 fallback 策略**，不能因签名失败而中断整个打包流程。

```bash
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"

sign_elf() {
    local file="$1"
    local max_retries=3
    local retry=0

    # 移除旧签名段（必须先做，否则 sign 报错）
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true

    while [ $retry -lt $max_retries ]; do
        retry=$((retry + 1))
        if $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null; then
            return 0  # 成功
        fi
        echo "  ⚠️ 签名失败 (尝试 $retry/$max_retries): $(basename $file)"
        sleep 1
    done

    # 所有重试都失败 → 标记为 unsigned 但不中断打包流程
    echo "  ❌ 签名最终失败（已重试 $max_retries 次）: $(basename $file)"
    touch "${file}.unsigned"
}

# 批量签名 + 统计结果
sign_success=0
sign_failed=0
for elf in $(find "$PKGDIR" -type f -exec file {} \; | grep 'ELF' | cut -d: -f1); do
    sign_elf "$elf"
    if [ -f "${elf}.unsigned" ]; then
        sign_failed=$((sign_failed + 1))
    else
        sign_success=$((sign_success + 1))
    fi
done

echo "  签名结果: ✅ $sign_success 成功 / ❌ $sign_failed 失败(标记unsigned)"
if [ "$sign_failed" -gt 0 ]; then
    echo "  ⚠️ 有 $sign_failed 个文件未签名。包可用但非正式签名版本。"
fi
```

**签名失败的后续处理策略**：

| 场景 | 处理方式 | 用户侧操作 |
|------|---------|-----------|
| 少数文件签名失败 | 标记 `.unsigned`，继续打包 | 解压后手动 `binary-sign-tool sign -inFile xxx -selfSign 1` |
| 全部签名失败 | 打包但 README 标注 `UNSIGNED` | 用户需自行签名或从源码编译 |
| 权限错误 | 检查 SELinux 上下文和文件权限 | `ls -Z` 检查，可能需 `restorecon` |

**Step 8 中增加签名完整性检查（在权限修复后执行）**：
```bash
echo "=== 签名完整性检查 ==="
unsigned_count=$(find "$PKGDIR" -name "*.unsigned" | wc -l | tr -d ' ')
if [ "$unsigned_count" -gt 0 ]; then
    echo "  ⚠️ $unsigned_count 个文件未签名（见 *.unsigned 标记）"
else
    echo "  ✅ 所有 ELF 文件已签名"
fi
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

### Step 9: 打包 tar.gz（install.sh 由 cmd-pkgs 公共安装脚本提供，不包含在 tar.gz 中）

> **⚠️ 重要变更（v2.4）**：不再为每个软件生成独立的 install.sh。
> 使用 cmd-pkgs 公共安装脚本，托管在 cmd-pkgs 的 `pkgs` release tag 下。
> 用户通过 `curl | sh -s -- <name> <version>` 安装。

```bash
# 9a. 无需手动创建 install.sh，使用 cmd-pkgs 公共安装脚本
#     公共脚本: templates/universal-install.sh
#     托管位置: cmd-pkgs releases → pkgs tag

# 9b. 用户安装命令
#     curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- <name> <version>
```

### Step 10: 打包干净的 release tar.gz

```bash
OUTPUT_DIR="/path/to/output"
cd "$OUTPUT_DIR"

# 10a. 主包（干净产物：bin/ + share/，不含 install.sh/README）
tar -czf "${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}.tar.gz" -C "$PKGDIR" *
echo "📦 主包: ${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}.tar.gz ($(du -h "${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}.tar.gz" | cut -f1))"

# 10b. Debug 符号包（⭐ 必须打包）
if [ -d "$DEBUG_DIR" ] && [ "$(ls -A "$DEBUG_DIR")" ]; then
    tar -czf "${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}-debug.tar.gz" -C "$(dirname "$DEBUG_DIR")" "$(basename "$DEBUG_DIR")"
    echo "🔧 Debug: ${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}-debug.tar.gz ($(du -h "${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}-debug.tar.gz" | cut -f1))"
fi

# 10c. 最终统计 + 安装验证
echo ""
echo "=== 打包统计 ==="
echo "  总文件数: $(find "$PKGDIR" -type f | wc -l | tr -d ' ')"
echo "  ELF 文件: $(find "$PKGDIR" -type f -exec file {} \; | grep -ci elf)"
echo "  外部依赖: $(ls "$PKGDIR/lib/external/" 2>/dev/null | wc -l | tr -d ' ')"
echo "  残留符号链接: $(find "$PKGDIR" -type l | wc -l | tr -d ' ')"

# 10d. 安装验证（模拟 install.sh 流程）
VERIFY_DIR="${TMPDIR:-$HOME/tmp}/pkg-verify-$$"
rm -rf "$VERIFY_DIR"; mkdir -p "$VERIFY_DIR"
tar xzf "${PKG_NAME}-${PKG_VERSION}-ohos-${ARCH}.tar.gz" -C "$VERIFY_DIR"
chmod +x "$VERIFY_DIR/bin/"* 2>/dev/null
"$VERIFY_DIR/bin/${PKG_NAME}" --version >/dev/null 2>&1 && echo "✅ 安装验证通过" || echo "❌ 安装验证失败"
rm -rf "$VERIFY_DIR"
```

---

## 10. 完整交付物清单

每个预编译软件的 `packaging/` 目录应包含：

```
archives/{首字母}/{软件名}/{版本}/packaging/
├── {name}-{ver}-ohos-aarch64.tar.gz        ← Release 制品（干净二进制，已 strip）
└── {name}-{ver}-ohos-aarch64-debug.tar.gz   ← Debug 符号包（必须）
```

### 发布到 gitcode 的步骤

1. 上传 `{name}-{version}-ohos-aarch64.tar.gz` 到 cmd-pkgs 的 `pkgs` release tag
2. （可选）上传 debug 包到同一 release tag
3. 用户安装命令：
   ```bash
   curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- {name} {ver}
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

*文档版本: 2.1*
*最后更新: 2026-04-04*
*v2.0 更新：*
*  - 综合 3.9.25 + 3.12.9 最佳实践，建立 10 步标准化流程*
*  - 新增 Step 4: 外部依赖收集（必做）*
*  - 新增 Step 8: 统一权限修复（必做），含根因分析*
*  - 新增 §6: 权限问题详解（binary-sign-tool 签名重置权限根因）*
*  - 新增 Python 缓存清理步骤*
*v2.1 更新：*
*  - 头部增加 SKILL.md Phase 4 Step 5.5 交叉引用定位*
*  - 新增 §8.5 静态库打包注意事项（对应 dependencies.md 静态编译要求表）*

---

## 8.5 静态库打包注意事项

> 当目标软件使用了 `--without-shared` / `--disable-static` 等选项时（见 `dependencies.md` 静态编译强制要求表），
> 打包流程需要相应调整。

### 静态库（.a）场景

```bash
# ncurses --without-shared → 只有 libncursesw.a，无 .so
# 打包时：
# 1. Step 3（符号链接替换）：跳过，没有 .so 符号链接
# 2. Step 4（外部依赖收集）：检查 NEEDED 时不会找到 ncurses（已静态链接）
# 3. Step 5（RPATH设置）：只需处理可执行文件，无需处理 .so
# 4. Step 6（Strip）：.a 文件已经是 stripped 状态，跳过或仅做验证
```

### 混合场景（部分静态 + 部分动态）

```bash
# readline --disable-shared + openssl 动态库
# 打包时：
# - readline 的 .a 已编入最终二进制，不需要单独打包
# - openssl 的 .so 仍需收集到 lib/external/ 并设置 RPATH
# - 最终可执行文件不依赖 libreadline.so，但依赖 libssl.so
```

---

## 9. cmd-pkgs 公共安装脚本

> **定位**：cmd-pkgs 仓库提供的统一公共安装脚本，接受 `<name> <version>` 参数。
> **重要（v2.4）**：不再为每个软件生成独立 install.sh，统一使用 cmd-pkgs 的 `pkgs` release tag 下的公共安装脚本。
> 用户通过 `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- <name> <version>` 安装，tar.gz 只包含干净二进制产物。

### 9.1 设计原则

| 原则 | 说明 |
|------|------|
| **极简依赖** | 只用 POSIX sh 内置 + tar + curl + cp + chmod（所有鸿蒙设备均有） |
| **纯 ASCII** | 禁止 emoji/颜色码/多字节字符（toybox ash 不支持） |
| **扁平释放** | bin/lib/share 直接落到 `~/usr/local/`，所有软件自然共存 |
| **管道安全** | 禁止 heredoc（与 `curl \| sh` 的 stdin 冲突），全部用 printf |
| **幂等** | 重复运行不重复写 .zshrc，PATH 已有则跳过 |

### 9.2 目录结构约定

```
~/usr/local/                          <-- 公共根（所有软件共享）
├── bin/                              <-- 所有命令汇聚
│   ├── pkg-config                    <-- 软件A 二进制
│   ├── aarch64-*-pkg-config          <-- triplet 别名
│   ├── sed                          <-- 软件B 二进制
│   └── ...
├── lib/
│   ├── pkgconfig/                   <-- 公共 .pc 池 (PKG_CONFIG_PATH)
│   └── external/                    <-- 外部依赖库
├── share/
│   ├── aclocal/
│   └── man/man1/
└── (无 README, 无 activate.sh)       <-- 不在包内
```

### 9.3 模板代码

完整模板见 cmd-pkgs 仓库的 `pkgs` release tag（64 行 / 2.2KB）。

每个软件只需修改两行：
```sh
PKG_NAME="${PKG_NAME:-pkg-config}"        # <-- 改这里
PKG_VERSION="${PKG_VERSION:-0.29.2}"      # <-- 改这里
```

4 步流程：
- **Step 1**: 获取 tarball（本地优先 → gitcode → gitee）
- **Step 2**: 解压到 `~/usr/local/`（兼容 toybox tar 无 --strip-components）
- **Step 3**: `chmod +x` bin/*
- **Step 4**: PATH 缺失时写入 `.zshrc`（已有则跳过）

### 9.4 使用 cmd-pkgs 公共安装脚本

安装脚本由 cmd-pkgs 仓库统一维护，不再需要为每个软件单独生成。

1. 公共脚本托管在 `cmd-pkgs` 仓库的 `pkgs` release tag 下
2. 通过 `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- <name> <version>` 安装
3. 脚本会自动从 gitcode 下载对应的 tar.gz 并解压到 `~/usr/local/`
4. 如需修改安装脚本，向 cmd-pkgs 仓库提交 PR

### 9.5 禁止事项

| 禁止项 | 原因 |
|--------|------|
| `set -e` | cp 遇系统保护文件报错中断后续步骤 |
| heredoc (`<< EOF`) | 与 `curl \| sh` stdin 冲突 → syntax error |
| emoji / Unicode | toybox ash 截断多字节 → function not found |
| `\033[...m` 颜色码 | 部分 echo 不支持转义序列 |
| `--strip-components` | toybox tar 不支持 |
| `source` / `.` | 非 POSIX 标准 |
| `[[ ]]` | bashism |
| README.md / activate.sh 放入 tar.gz | 用户要求不放包内 |
| 包名子目录 `~/usr/<name>-ver/` | 要求扁平释放到 `~/usr/local/` |

*文档版本: 2.3*
*最后更新: 2026-04-07*
*v2.0 更新：*
*  - 综合 3.9.25 + 3.12.9 最佳实践，建立 10 步标准化流程*
*  - 新增 Step 4: 外部依赖收集（必做）*
*  - 新增 Step 8: 统一权限修复（必做），含根因分析*
*v2.1 更新：头部增加 SKILL.md Phase 4 Step 5.5 交叉引用*
*v2.2 更新：新增 §9 install.sh 通用安装脚本模板（已废弃，改为 cmd-pkgs 公共脚本）*
*v2.3 更新：*
*  - Step 9 改为 install.sh（替代 activate.sh，已废弃），单独托管不打包进 tar.gz*
*  - Step 10 增加安装验证步骤 + §10 完整交付物清单和 gitcode 发布流程*
流程*
�*
��*
流程*
�*

