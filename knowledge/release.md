# 鸿蒙适配发布流程

本文档定义鸿蒙适配软件的版本号命名、发布物结构、打包流程、安装脚本规范以及 GitCode Release 发布流程。

---

## §1 版本号命名规范

### 总体格式

```
{软件名}-{上游版本}-{适配版本}
```

### 适配版本格式

```
ohos{N}
  - ohos1: 首次适配
  - ohos2: 补丁更新/兼容性改进
  - ohos3: 重大变更
```

### 示例

```
python-3.9.0-ohos1.tar.gz        # Python 3.9.0 首次鸿蒙适配
python-3.9.0-ohos2.tar.gz        # 修复了补丁/改进了兼容性
openssl-1.1.1w-ohos1.tar.gz      # OpenSSL 首次适配
```

### 产物包命名

```
{软件名}-{上游版本}-ohos{N}-{arch}.tar.gz          # 产物包（按架构）
{软件名}-{上游版本}-ohos{N}-{arch}-debug.tar.gz    # Debug 符号包
{软件名}-{上游版本}-patches.tar.gz                  # 补丁包（源码分发）
```

其中 `{arch}` 为目标架构标识，例如 `aarch64`、`x86_64` 等。

---

## §2 发布物结构

### 产物包（二进制分发）

```
{软件名}-{版本}-ohos-{arch}/
├── bin/               # 可执行文件（wrapper 脚本替代软链接）
├── lib/               # 共享库
│   └── external/      # 外部依赖库
├── include/           # 头文件
├── README.md          # 使用说明
├── VERSION            # 版本信息文件
└── install.sh         # 一键安装脚本
```

说明：
- **bin/** 下的可执行文件应直接放置，install.sh 负责创建 wrapper 脚本到用户 PATH 目录
- **lib/external/** 存放本软件依赖的外部共享库（非系统库），通过 patchelf 设置 `$ORIGIN` 相对 RPATH
- **VERSION** 文件内容示例：`python 3.9.0 ohos1 aarch64`
- **README.md** 包含安装步骤、已知限制、目录结构说明

### 补丁包（源码分发）

```
{软件名}-{版本}-patches/
├── series             # 补丁应用顺序
├── patches/
│   ├── 0001-xxx.patch
│   └── 0002-xxx.patch
├── BUILD_NOTES.md     # 编译说明（configure 参数、依赖要求）
└── apply-patches.sh   # 一键应用所有补丁的脚本
```

说明：
- **series** 文件每行一个补丁文件名（quilt 兼容格式），空行和 `#` 开头的行为注释
- **patches/** 目录下存放 git format-patch 或手动创建的补丁文件
- **BUILD_NOTES.md** 记录完整的编译步骤：configure 参数、环境变量、依赖库版本、已知问题
- **apply-patches.sh** 自动按 series 顺序应用所有补丁

---

## §3 打包流程（Phase 5: Release）

在 SKILL.md 的 Phase 4（编译验证）之后，进入 Phase 5：打包发布。

### Step 1：收集产物

从 `$DEFAULT_PREFIX`（默认为 `$HOME/build/_install/{软件名}`）收集安装好的文件：

```sh
SRC_DIR="$HOME/build/_install/$SOFTWARE_NAME"
DST_DIR="$HOME/build/_release/$SOFTWARE_NAME-$VERSION-ohos-$ARCH"

mkdir -p "$DST_DIR"/{bin,lib/external,include}
cp -a "$SRC_DIR/bin/"* "$DST_DIR/bin/"
cp -a "$SRC_DIR/lib/"* "$DST_DIR/lib/"
cp -a "$SRC_DIR/include/"* "$DST_DIR/include/" 2>/dev/null || true
```

### Step 2：依赖分析

用 `llvm-readelf -d` 收集所有 NEEDED 库：

```sh
echo "=== 依赖分析 ==="
find "$DST_DIR/bin" "$DST_DIR/lib" -type f \( -executable -o -name "*.so" -o -name "*.so.*" \) | while read elf; do
    echo "--- $elf ---"
    llvm-readelf -d "$elf" 2>/dev/null | grep NEEDED || true
done > "$DST_DIR/deps.txt"
```

### Step 3：外部依赖收集

将非系统库复制到 `lib/external/`：

```sh
EXTERNAL_DEPS=$(grep NEEDED "$DST_DIR/deps.txt" | awk '{print $NF}' | tr -d '[]"' | sort -u | while read lib; do
    # 跳过系统库和标准 C 库
    case "$lib" in
        libc.so*|libm.so*|libdl.so*|libpthread.so*|ld-musl-*) continue ;;
        libc++*|libclang*|libunwind*) continue ;;
    esac
    # 查找库文件位置
    found=$(find "$OHOS_NDK" -name "$lib" -type f 2>/dev/null | head -1)
    if [ -n "$found" ]; then
        echo "$found"
    fi
done)

for dep in $EXTERNAL_DEPS; do
    cp -a "$dep" "$DST_DIR/lib/external/"
    echo "  收集外部依赖: $(basename "$dep")"
done
```

### Step 4：RPATH 设置

用 patchelf 设置 `$ORIGIN` 相对路径：

```sh
# 设置 bin/ 下可执行文件的 RPATH
for elf in "$DST_DIR/bin/"*; do
    [ -f "$elf" ] || continue
    patchelf --set-rpath '$ORIGIN/../lib:$ORIGIN/../lib/external' "$elf" 2>/dev/null || true
done

# 设置 lib/ 下共享库的 RPATH
for elf in "$DST_DIR/lib/"*.so*; do
    [ -f "$elf" ] || continue
    patchelf --set-rpath '$ORIGIN:$ORIGIN/external' "$elf" 2>/dev/null || true
done
```

### Step 5：Strip + Debug 分离

可选步骤，减小包体积：

```sh
# 分离 debug 符号
DEBUG_DIR="$DST_DIR-debug"
mkdir -p "$DEBUG_DIR"
find "$DST_DIR" -type f \( -executable -o -name "*.so" -o -name "*.so.*" \) | while read elf; do
    debug_file="${elf#$DST_DIR/}.debug"
    mkdir -p "$DEBUG_DIR/$(dirname "$debug_file")"
    llvm-objcopy --only-keep-debug "$elf" "$DEBUG_DIR/$debug_file"
    llvm-strip --strip-debug "$elf"
done
```

### Step 6：ELF 签名

按照 packaging.md §2 的七步流程对 ELF 文件进行签名：

```sh
# 参考 packaging.md §2 ELF 签名七步流程
# 1. 生成签名密钥（首次）
# 2. 计算文件哈希
# 3. 生成签名
# 4. 将签名嵌入 ELF
# 5. 验证签名
# 6. 更新哈希表
# 7. 最终验证
```

### Step 7：生成 install.sh / uninstall.sh

从模板生成安装和卸载脚本：

```sh
# 替换模板变量
sed -e "s/{{SOFTWARE_NAME}}/$SOFTWARE_NAME/g" \
    -e "s/{{VERSION}}/$VERSION/g" \
    templates/install.sh > "$DST_DIR/install.sh"
chmod +x "$DST_DIR/install.sh"

sed -e "s/{{SOFTWARE_NAME}}/$SOFTWARE_NAME/g" \
    templates/uninstall.sh > "$DST_DIR/uninstall.sh"
chmod +x "$DST_DIR/uninstall.sh"
```

### Step 8：生成 README.md

```sh
cat > "$DST_DIR/README.md" << EOF
# $SOFTWARE_NAME $VERSION - HarmonyOS 适配版

## 安装

\`\`\`sh
tar -xzf $SOFTWARE_NAME-$VERSION-ohos${N}-$ARCH.tar.gz
cd $SOFTWARE_NAME-$VERSION-ohos-$ARCH
sh install.sh [安装路径]
\`\`\`

默认安装路径：\`~/usr/\`

## 环境变量

安装后请将以下内容添加到 \`~/.bashrc\`：

\`\`\`sh
export PATH="~/usr/bin:\$PATH"
export TMPDIR=/data/local/tmp
\`\`\`

## 目录结构

\`\`\`
$SOFTWARE_NAME-$VERSION-ohos-$ARCH/
├── bin/          # 可执行文件
├── lib/          # 共享库
│   └── external/ # 外部依赖库
├── include/      # 头文件
├── install.sh    # 安装脚本
├── uninstall.sh  # 卸载脚本
└── VERSION       # 版本信息
\`\`\`

## 已知限制

- 需要 HarmonyOS 3.0+ 或 OpenHarmony
- 部分功能可能受限（取决于上游软件对交叉编译的支持程度）
- 外部依赖库版本与 NDK 版本绑定

## 构建信息

- 构建日期：$(date -Iseconds)
- NDK 版本：${OHOS_NDK_VERSION:-unknown}
- 目标架构：$ARCH
EOF
```

### Step 9：打包

```sh
RELEASE_DIR="$HOME/build/_release"

# 产物包
tar -czf "$RELEASE_DIR/$SOFTWARE_NAME-$VERSION-ohos${N}-$ARCH.tar.gz" \
    -C "$RELEASE_DIR" "$SOFTWARE_NAME-$VERSION-ohos-$ARCH"

# Debug 包（如果进行了 debug 分离）
if [ -d "$DST_DIR-debug" ]; then
    tar -czf "$RELEASE_DIR/$SOFTWARE_NAME-$VERSION-ohos${N}-$ARCH-debug.tar.gz" \
        -C "$RELEASE_DIR" "$SOFTWARE_NAME-$VERSION-ohos-$ARCH-debug"
fi

# 补丁包
tar -czf "$RELEASE_DIR/$SOFTWARE_NAME-$VERSION-patches.tar.gz" \
    -C "$RELEASE_DIR" "$SOFTWARE_NAME-$VERSION-patches"

echo "=== 打包完成 ==="
ls -lh "$RELEASE_DIR"/*.tar.gz
```

### Step 10：验证

在干净目录解压验证可用性：

```sh
TEST_DIR=$(mktemp -d)
cd "$TEST_DIR"

# 解压
tar -xzf "$RELEASE_DIR/$SOFTWARE_NAME-$VERSION-ohos${N}-$ARCH.tar.gz"

# 检查结构
[ -d "$SOFTWARE_NAME-$VERSION-ohos-$ARCH/bin" ] || { echo "❌ 缺少 bin/"; exit 1; }
[ -d "$SOFTWARE_NAME-$VERSION-ohos-$ARCH/lib" ] || { echo "❌ 缺少 lib/"; exit 1; }
[ -f "$SOFTWARE_NAME-$VERSION-ohos-$ARCH/install.sh" ] || { echo "❌ 缺少 install.sh"; exit 1; }

# 检查 RPATH
find "$SOFTWARE_NAME-$VERSION-ohos-$ARCH/bin" -type f -executable | while read elf; do
    echo "RPATH of $(basename "$elf"): $(patchelf --print-rpath "$elf" 2>/dev/null)"
done

# 清理
rm -rf "$TEST_DIR"

echo "✅ 验证通过"
```

---

## §4 install.sh / uninstall.sh 模板规范

### install.sh 要求

| 要求 | 说明 |
|------|------|
| POSIX 兼容 | 使用 `#!/bin/sh`，仅使用 toybox ash 支持的语法 |
| 自定义安装路径 | 支持 `sh install.sh [路径]`，默认 `$HOME/usr/` |
| Wrapper 脚本 | 在 `$INSTALL_DIR/bin/` 创建 wrapper 脚本（不使用软链接，SELinux 限制） |
| 环境变量提示 | 安装完成后提示用户设置 PATH / TMPDIR / PKG_CONFIG_PATH 等 |
| 预触发弹窗 | 首次运行可执行文件，预触发 HarmonyOS 的安全弹窗确认 |
| 幂等性 | 重复安装不出错，覆盖已有文件 |

Wrapper 脚本模板：

```sh
#!/bin/sh
exec "/path/to/real/binary" "$@"
```

### uninstall.sh 要求

| 要求 | 说明 |
|------|------|
| POSIX 兼容 | 使用 `#!/bin/sh` |
| 删除安装目录 | 删除 `$INSTALL_DIR/$PACKAGE_NAME` |
| 清理 wrapper | 清理 `$INSTALL_DIR/bin/` 下的相关 wrapper 脚本 |
| 安全确认 | 不自动执行，需要用户手动确认 `y/N` |
| 环境变量提示 | 提示用户手动从 `~/.bashrc` 移除 PATH 配置 |

---

## §5 GitCode Release 发布流程

### Step 1：创建 Git Tag

```sh
git tag -a "v${SOFTWARE_NAME}-${VERSION}-ohos${N}" -m "${SOFTWARE_NAME} ${VERSION} HarmonyOS 适配版 ohos${N}"
git push origin "v${SOFTWARE_NAME}-${VERSION}-ohos${N}"
```

Tag 命名格式：`v{软件名}-{版本}-ohos{N}`

### Step 2：创建 Release

在 GitCode 上创建 Release，填写以下信息：

- **标题**：`{软件名} {版本} - HarmonyOS 适配版 ohos{N}`
- **附件**：
  - `{软件名}-{版本}-ohos{N}-{arch}.tar.gz`（产物包）
  - `{软件名}-{版本}-patches.tar.gz`（补丁包）
  - `{软件名}-{版本}-ohos{N}-{arch}-debug.tar.gz`（debug 包，可选）
- **Release Notes**：从 `manifest.yaml` 生成，包含：
  - 版本信息
  - 适配内容概述
  - 已知问题
  - 依赖说明
  - 编译环境信息

### Release Notes 模板

```markdown
## {软件名} {版本} - HarmonyOS 适配版 ohos{N}

### 适配内容
- 基于 {软件名} {上游版本} 进行鸿蒙适配
- 包含 {补丁数量} 个适配补丁

### 下载
| 文件 | 说明 |
|------|------|
| `{软件名}-{版本}-ohos{N}-{arch}.tar.gz` | 产物包（{架构}） |
| `{软件名}-{版本}-patches.tar.gz` | 补丁包（源码分发） |
| `{软件名}-{版本}-ohos{N}-{arch}-debug.tar.gz` | Debug 符号包 |

### 安装
\```sh
tar -xzf {软件名}-{版本}-ohos{N}-{arch}.tar.gz
cd {软件名}-{版本}-ohos-{arch}
sh install.sh
\```

### 已知限制
- {从 manifest.yaml 生成}

### 编译环境
- NDK: {版本}
- API Level: {级别}
- 构建日期: {日期}
```

---

## 参考

- [packaging.md](./packaging.md) — ELF 签名七步流程
- [SKILL.md](../SKILL.md) — 完整编译流程（Phase 1-4）
- Python 3.9.0 打包方式（业界参考）
