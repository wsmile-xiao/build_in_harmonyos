# Conan 打包技术参考

> **当前打包方式**：使用 `conan create` + `conan upload`（R19 铁律）。
> 手动 tar.gz 打包已废弃。本文档保留 ELF 处理技术细节，供 Conan 配方编写参考。

---

## 1. RPATH 设置原则

### 使用 `$ORIGIN` 相对路径

RPATH 使用 `$ORIGIN` 相对于文件自身位置查找库，使包可放在任意目录：

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

### RPATH 设置命令

```bash
PATCHELF="/data/service/hnp/bin/patchelf"

set_rpath() {
    local file="$1"
    local rpath="$2"
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null
}

# 示例
set_rpath "$PKGDIR/bin/main_executable"   '$ORIGIN/../lib:$ORIGIN/../lib/external'
set_rpath "$PKGDIR/lib/libmain.so"         '$ORIGIN:$ORIGIN/external'
```

> **Conan 方式**：Conan 配方中可通过 `package_info()` 的 `cpp_info` 自动设置 RPATH，上述手动设置仅在特殊场景使用。

---

## 2. 外部依赖检查与收集

ELF 文件的 NEEDED 库如果不在系统默认路径中，需在 Conan 配方中声明为依赖。

### 依赖分析

```bash
READELF="/data/service/hnp/bin/llvm-readelf"

# 分析 ELF 文件的 NEEDED 依赖
$READELF -d "$ELF_FILE" 2>/dev/null | grep NEEDED | sed 's/.*\[\(.*\)\].*/\1/'
```

### 可跳过的系统库（musl 提供，不需打包）

```
libc.so, libm.so, libdl.so, libpthread.so, ld-musl-*.so, librt.so, libutil.so
```

### 常见外部依赖

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

> **Conan 方式**：上述依赖应在 `conanfile.py` 的 `requirements()` 中声明 `@ohpcd/stable` 引用，Conan 自动管理依赖链。

---

## 3. Strip Debug 符号

### 一体化处理（RPATH + Strip + Sign）

```bash
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"
PATCHELF="/data/service/hnp/bin/patchelf"
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"

process_elf() {
    local file="$1"
    local rpath="$2"
    local debug_dir="${3:-}"

    # 1. Set RPATH
    $PATCHELF --set-rpath "$rpath" "$file" 2>/dev/null

    # 2. Strip + debug extract
    if [ -n "$debug_dir" ]; then
        local name=$(basename "$file")
        $OBJCOPY --only-keep-debug "$file" "${debug_dir}/${name}.debug"
        $OBJCOPY --strip-debug "$file" "${file}.tmp"
        mv "${file}.tmp" "$file"
        $OBJCOPY --add-gnu-debuglink="${debug_dir}/${name}.debug" "$file"
    fi

    # 3. Remove old sign + re-sign
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true
    $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null || true
}
```

### Strip 效果参考

| 软件 | Strip 前 | Strip 后 | 节省率 |
|------|---------|---------|--------|
| Python 3.9.0 | 14.4 MB | 4.7 MB | 67% |
| Python 3.12.9 | 64.6 MB | 30.1 MB | 53% |
| libpython3.x.so | 6.9 MB | 3.4 MB | 50-64% |

---

## 4. ELF 签名

> **⚠️ 签名工具稳定性**：`binary-sign-tool` 可能失败（权限不足/文件占用/内部异常），必须使用 fallback 策略。

```bash
SIGNTOOL="/data/service/hnp/bin/binary-sign-tool"
OBJCOPY="/data/service/hnp/bin/llvm-objcopy"

sign_elf() {
    local file="$1"
    local max_retries=3
    local retry=0

    # 移除旧签名段（必须先做，否则 sign 报错）
    $OBJCOPY --remove-section .codesign "$file" 2>/dev/null || true

    while [ $retry -lt $max_retries ]; do
        retry=$((retry + 1))
        if $SIGNTOOL sign -inFile "$file" -outFile "$file" -selfSign 1 2>/dev/null; then
            return 0
        fi
        sleep 1
    done

    # 所有重试失败 → 标记 unsigned 但不中断流程
    touch "${file}.unsigned"
    return 1
}
```

**签名失败处理策略**：

| 场景 | 处理方式 | 用户侧操作 |
|------|---------|-----------|
| 少数文件失败 | 标记 `.unsigned`，继续 | 手动 `binary-sign-tool sign -inFile xxx -selfSign 1` |
| 全部失败 | 标注 `UNSIGNED` | 自行签名或源码编译 |
| 权限错误 | 检查 SELinux 上下文 | `ls -Z` / `restorecon` |

> **CI 签名**：正式发布由 `ci/artifacts/sign.sh` 执行 GPG 签名。

---

## 5. 权限修复（⭐ 签名后必做）

### 根因

`binary-sign-tool` 签名后将文件权限重置为 `rw-rw----`（660），即使之前 `chmod a+x` 也会被覆盖。

### 解决方案

```bash
# ✅ 正确：所有 ELF 处理完毕后，统一批量 chmod
find "$PKGDIR" -type f -exec file {} \; | grep -i ELF | cut -d: -f1 | xargs chmod +x
find "$PKGDIR/bin" -type f ! -executable -exec chmod +x {} \;

# 验证
find "$PKGDIR" -type f -exec file {} \; | grep -i ELF | cut -d: -f1 | while read f; do
    [ -x "$f" ] || echo "❌ 缺少权限: $f"
done
```

> **顺序铁律**：RPATH → Strip → Sign → chmod。chmod 必须在签名之后。

---

## 6. 软链接替代方案

鸿蒙 SELinux 限制用户进程创建和访问软链接。

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

> **Conan 方式**：Conan 配方中可通过 `package_info()` 的 `cpp_info.libs` 和 `build_dirs` 自动管理库路径，减少手动处理软链接的需求。

---

## 7. 静态库打包注意事项

当目标软件使用 `--without-shared` / `--disable-static` 时（见 `dependencies.md` 静态编译要求表），打包流程需调整：

| 场景 | 软链接替换 | 依赖收集 | RPATH | Strip |
|------|-----------|---------|-------|-------|
| 纯静态（.a） | 跳过（无 .so 链接） | 不触发（已静态链接） | 仅处理可执行文件 | .a 已 stripped，跳过 |
| 混合（部分静态+动态） | 仅处理 .so | 仅收集动态依赖 | 处理可执行文件+动态库 | 正常 strip |

---

## 8. Conan 打包流程（当前方式）

### 生成配方

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-init <软件名> <版本>
```

生成 `conanfile.py` + `conandata.yml` + `test_package/`。

### 验证配方

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify <软件名> <版本>
```

8 道门禁：G0(风险评估) → G1(配方完整性) → G2(conan create) → G3(系统同名库隔离) → G4(产物完整性) → L2/L4/L5(smoke test/安全扫描/基线对比)。

### CI 发布

PR 合并到 main 后，CI 流水线自动执行：
1. `setup.sh` — Conan 环境初始化
2. `build_and_test.sh` — `conan create` + L4/L5 检查
3. `upload.sh` — `conan upload` 到 CNB 制品仓
4. `sign.sh` — GPG 签名

> 详见 SKILL.md §3 Step 4-5。

---

*文档版本: 3.0 · Conan 体系适配*
*最后更新: 2026-06-27*
