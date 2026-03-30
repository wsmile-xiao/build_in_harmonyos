# HarmonyOS 可移植打�
指南

在鸿蒙系统上制作可移植的软件�
，需要处理 RPATH、ELF 签名、软链接限制等鸿蒙特有问题。

## 1. 核心问题

| 问题 | 根因 | 影响 | 解决方案 |
|------|------|------|----------|
| 修改 ELF 后无法执行 | adhoc 签名失效 | patchelf/strip 后二进制被�
核拒绝 | 移除旧签名 → 重新签名 |
| 签名工�
�报 "section already exists" | 无法覆盖已有 .codesign 段 | 直接调用 binary-sign-tool 失败 | �
� llvm-objcopy 移除 |
| 软链接不可靠 | SELinux 策略限制 | ln -s 创建的链接无法访问 | 用 wrapper 脚本或 cp 替代 |
| ln -sf 创建随机后缀文件 | toybox bug | ln -sf link → link_GdinNM | rm -f && ln -s 替代 |
| 运行时找不到�
�享库 | LD_LIBRARY_PATH 未设置或 RPATH 错误 | ImportError / 动态链接失败 | patchelf --set-rpath '$ORIGIN/...' |

## 2. ELF 文件修改 + 签名完整流程

任何修改 ELF 文件的操作（patchelf、strip 等）都需要遵循以下流程：

### 2.1 基本流程（三步）

```bash
# 1. 移除旧签名
llvm-objcopy --remove-section .codesign binary

# 2. 重新签名（adhoc self-sign）
binary-sign-tool sign -inFile binary -outFile binary -selfSign 1

# 3. 恢复权限（签名会�
除权限位）
chmod a+x binary
```

### 2.2 发布流程（patchelf + strip + 签名，七步）

```bash
BINARY="myprogram"
RPATH='$ORIGIN/../lib:$ORIGIN/../lib/external'

# 1. 修改 RPATH
patchelf --set-rpath "$RPATH" "$BINARY"

# 2. 提取 debug info
llvm-objcopy --only-keep-debug "$BINARY" "${BINARY}.debug"

# 3. Strip debug sections
llvm-objcopy --strip-debug "$BINARY" "${BINARY}.tmp"
mv "${BINARY}.tmp" "$BINARY"

# 4. 添加 .gnu_debuglink（GDB 自动加载 debug 文件）
llvm-objcopy --add-gnu-debuglink="${BINARY}.debug" "$BINARY"

# 5. 移除旧签名
llvm-objcopy --remove-section .codesign "$BINARY"

# 6. 重新签名
binary-sign-tool sign -inFile "$BINARY" -outFile "$BINARY" -selfSign 1

# 7. 恢复权限
chmod a+x "$BINARY"
```

### 2.3 封�
函数

```bash
PATCHELF="/data/service/hnp/bin/patchelf"
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"

patch_strip_sign() {
    local file="$1"
    local rpath="$2"
    local do_strip="${3:-1}"

    # Set RPATH
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null

    if [ "$do_strip" = "1" ]; then
        # Extract debug
        $OBJCOPY --only-keep-debug "$file" "${file}.debug"
        # Strip
        $OBJCOPY --strip-debug "$file" "${file}.tmp"
        mv "${file}.tmp" "$file"
        # Add debuglink
        $OBJCOPY --add-gnu-debuglink="${file}.debug" "$file"
    fi

    # Remove old sign + re-sign
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true
    $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null

    # Restore permissions
    chmod a+x "$file"
}
```

## 3. RPATH 设置原则

### 3.1 使用 $ORIGIN 相对路径

RPATH 使用 `$ORIGIN` 相对于文件自身位置查找库，使�
可以放在任意目录：

```
python-3.9.0-harmonyos-aarch64/
├── bin/
│   └── python3.9          RPATH: $ORIGIN/../lib:$ORIGIN/../lib/external
├── lib/
│   ├── libpython3.9.so     RPATH: $ORIGIN:$ORIGIN/external
│   ├── python3.9/
│   │   └── lib-dynload/
│   │       └── *.so        RPATH: $ORIGIN:$ORIGIN/..:$ORIGIN/../external
│   └── external/
│       ├── libgdbm.so.6    RPATH: $ORIGIN
│       └── liblzma.so.5    RPATH: $ORIGIN
```

### 3.2 RPATH 设置建议

| 文件类型 | 推荐 RPATH | 说明 |
|----------|-----------|------|
| 可执行文件 (bin/) | `$ORIGIN/../lib:$ORIGIN/../lib/external` | 向上查找 lib/ |
| 主�
�享库 (lib/libxxx.so) | `$ORIGIN:$ORIGIN/external` | 同级和 external/ |
| 扩展模块 (lib/python3.x/lib-dynload/) | `$ORIGIN:$ORIGIN/..:$ORIGIN/../external` | 找 libpython 和 external |
| 外部依赖 (lib/external/) | `$ORIGIN` | 只找同级 |

### 3.3 分析依赖

```bash
# 查看 NEEDED 库
llvm-readelf -d binary | grep NEEDED

# 排除系统库，只收集非 libc/musl 的依赖
llvm-readelf -d binary | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/' | grep -v '^libc\.so'
```

### 3.4 可跳过的系统库

以下库由 musl libc 或动态链接器提供，不需要打�
：

```
libc.so      — musl libc（系统自带）
libm.so      — 数学库（musl �
建）
libdl.so     — 动态链接（musl �
建）
libpthread.so — 线程库（musl �
建）
librt.so     — 实时扩展（musl �
建）
libutil.so   — 工�
�库（musl �
建）
ld-musl-*.so — 动态链接器（绝对不可打�
）
```

## 4. 软链接替代方案

鸿蒙 SELinux 限制用户进程创建和访问软链接。

### 4.1 可执行文件别名：wrapper 脚本

```bash
# ❌ 不要用软链接
ln -s python3.9 python3

# �
 用 wrapper 脚本
cat > python3 << 'EOF'
#!/bin/sh
SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SELF_DIR/python3.9" "$@"
EOF
chmod +x python3
```

### 4.2 �
�享库别名：cp 复制

```bash
# ❌ 不要用软链接
ln -s libpython3.9.so.1.0 libpython3.9.so

# �
 直接复制（多占磁盘空间但可靠）
cp libpython3.9.so.1.0 libpython3.9.so
```

### 4.3 toybox ln -sf 的替代

```bash
# ❌ toybox ln -sf 会创建随机后缀文件
ln -sf target link   # → link_GdinNM

# �
 分步操作
rm -f link && ln -s target link
```

## 5. 分离打�
策略

### 5.1 主�
 vs Debug �


```bash
# 主�
（不含 debug）
tar -czf package.tar.gz --exclude=debug/ package/

# Debug �

tar -czf package-debug.tar.gz package/debug/
```

### 5.2 Python 3.9.0 实�
数据

| 文件 | Strip 前 | Strip 后 | 节省 | Debug Info |
|------|----------|----------|------|------------|
| python3.9 (解释器) | 84K | 74K | 12% | 6K |
| libpython3.9.so.1.0 | **9.6M** | **3.4M** | **64%** | 6.7M |
| 外部依赖库 (×3) | 436K | 410K | 6% | 18K |
| **总计** | **177MB** | **165MB** | **7%** | **14MB** |

> 注意：标准库 `.py` 文件占 203MB（87%），无法压缩。如需进一步减小体积，
> 可考虑编译为 `.pyc`（优化的字节码，但启动时无法自适应 Python 版本变化）。

### 5.3 .gnu_debuglink 工作原理

1. `llvm-objcopy --add-gnu-debuglink=file.debug binary` 在 binary 中嵌�
� debug 文件的文件名和 CRC
2. GDB 加载 binary 时，读取 `.gnu_debuglink` 段，在以下路径搜索 debug 文件：
   - 与 binary 同目录
   - binary 目录下的 `debug/` 子目录
   - `/usr/lib/debug/` �
�局目录
3. 通过 CRC 校验确保 debug 文件与 binary 匹�
�

## 6. 首次运行确认

鸿蒙的 adhoc 签名机制要求用户在弹窗中确认后才能首次运行。
这是系统级行为，无法绕过。每个新签名的二进制都需要一次确认。

**影响**：
- 从压缩�
解压后首次运行需要确认
- 更新二进制后需要重新确认
- wrapper 脚本（非 ELF）不需要确认

## 7. 完整打�
检查�
单

```bash
#!/bin/bash
# verify_package.sh - 验证可移植�
完整性

PKGDIR="$1"

echo "=== 1. RPATH 检查 ==="
find "$PKGDIR" -type f -executable | while read f; do
    if file "$f" | grep -q "ELF"; then
        rpath=$(patchelf --print-rpath "$f" 2>/dev/null)
        echo "  $(basename $f): RPATH=$rpath"
        if echo "$rpath" | grep -q '\$ORIGIN'; then
            echo "    �
 使用相对路径"
        else
            echo "    ❌ 未设置 RPATH 或使用绝对路径"
        fi
    fi
done

echo ""
echo "=== 2. 签名检查 ==="
find "$PKGDIR" -type f -executable | while read f; do
    if file "$f" | grep -q "ELF"; then
        if llvm-readelf -S "$f" 2>/dev/null | grep -q '.codesign'; then
            echo "  �
 $(basename $f): 已签名"
        else
            echo "  ❌ $(basename $f): 未签名"
        fi
    fi
done

echo ""
echo "=== 3. 依赖检查 ==="
find "$PKGDIR" -type f -executable | while read f; do
    if file "$f" | grep -q "ELF"; then
        missing=()
        for lib in $(llvm-readelf -d "$f" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/'); do
            case "$lib" in
                libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-*.so*) continue ;;
            esac
            # Check if lib exists in package
            if ! find "$PKGDIR" -name "$lib" -type f | grep -q .; then
                missing+=("$lib")
            fi
        done
        if [ ${#missing[@]} -gt 0 ]; then
            echo "  ❌ $(basename $f): 缺少 ${missing[*]}"
        else
            echo "  �
 $(basename $f): 依赖完整"
        fi
    fi
done

echo ""
echo "=== 4. debuglink 检查 ==="
find "$PKGDIR" -type f -executable | while read f; do
    if file "$f" | grep -q "ELF"; then
        if llvm-readelf -S "$f" 2>/dev/null | grep -q '.gnu_debuglink'; then
            echo "  �
 $(basename $f): 有 debuglink"
        fi
    fi
done

echo ""
echo "=== 5. 软链接检查 ==="
find "$PKGDIR" -type l | while read link; do
    if [ ! -e "$link" ]; then
        echo "  ⚠️ $link: 悬空软链接"
    fi
done
echo "  (无输出表示无悬空链接)"
```

---


## 8. 参考案例

| 软件 | 打�
文档 | �
�键特点 |
|------|----------|----------|
| Python 3.9.0 | `archives/p/python/3.9.0/scripts/package_python.sh` | 完整脚本，含 strip + debug 分离 |

---

*文档版本: 1.0*  
*最后更新: 2026-03-23*  
*基于 Python 3.9.0 打�
实战经验总结*
