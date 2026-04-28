# 鸿蒙适配发布流程

本文档定义鸿蒙适配软件的版本号命名、发布物结构、打包流程、安装脚本规范以及 GitCode Release 发布流程。

---

## §1 版本号命名规范

### 总体格式

```
{软件名}-{上游版本}-ohos-{arch}.tar.gz
```

### 适配版本格式

```
ohos-{arch}
  - {arch} 为目标架构标识，如 aarch64、x86_64
```

### 示例

```
python-3.9.0-ohos-aarch64.tar.gz        # Python 3.9.0 鸿蒙 aarch64 适配
openssl-1.1.1w-ohos-aarch64.tar.gz      # OpenSSL 鸿蒙 aarch64 适配
```

### 产物包命名

```
{软件名}-{上游版本}-ohos-{arch}.tar.gz          # 产物包（按架构）
{软件名}-{上游版本}-ohos-{arch}-debug.tar.gz    # Debug 符号包
{软件名}-{上游版本}-patches.tar.gz                  # 补丁包（源码分发）
```

其中 `{arch}` 为目标架构标识，例如 `aarch64`（与 packaging.md §1.5 一致）。

---

## §2 发布物结构

### 产物包（二进制分发）

> **⚠️ 与 packaging.md §1.5 保持一致**：tar.gz 内部为扁平结构，只含 bin/share/lib。

```
{name}-{ver}-ohos-aarch64.tar.gz   ← 解压后顶层就是这些目录
├── bin/           # 可执行文件 (ELF, 已签名, 已 strip, 有执行权限)
│   ├── {name}     # 主二进制
│   └── ...
├── share/         # 文档和数据（如 man 页、locale 等）
└── lib/           # 共享库 + 外部依赖（如有）
    └── external/  # 外部依赖库（非系统库，通过 patchelf 设置 $ORIGIN RPATH）
```

说明：
- **tar.gz 不含 install.sh/README.md/VERSION**：安装由 cmd-pkgs 公共安装脚本统一处理
- **bin/** 下不使用软链接（鸿蒙 SELinux 限制），用 wrapper 脚本或 cp 替代
- **lib/external/** 存放本软件依赖的外部共享库（非系统库），通过 patchelf 设置 `$ORIGIN` 相对 RPATH
- 打包命令必须从包含 `bin/` 的目录执行：`cd "$PKGDIR" && tar czf "output.tar.gz" *`

### ~~install.sh（已废弃）~~

> **已迁移至 cmd-pkgs 公共安装脚本**。不再为每个软件生成独立 install.sh。
> 使用 cmd-pkgs 公共安装脚本，托管在 cmd-pkgs 的 `pkgs` release tag 下。
> 用户通过 `curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- <name> <version>` 安装。
> 详见 packaging.md §9。

### ~~VERSION 文件（已废弃）~~

> 版本信息由 manifest.yaml 和 Release Notes 提供，不再在 tar.gz 中包含 VERSION 文件。

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

从 staging 目录（`$STAGING_PREFIX`）收集安装好的文件：

```sh
SRC_DIR="$STAGING_PREFIX"   # 即 $TEST_PREFIX/$DEFAULT_PREFIX
DST_DIR="$HOME/build/_release/$SOFTWARE_NAME-$VERSION-ohos-$ARCH"

mkdir -p "$DST_DIR"
cd "$SRC_DIR"
tar cf - bin share lib 2>/dev/null | (cd "$DST_DIR" && tar xf -)
```

### Step 2：依赖分析

用 `llvm-readelf -d` 收集所有 NEEDED 库：

```sh
echo "=== 依赖分析 ==="
find "$DST_DIR/bin" "$DST_DIR/lib" -type f \( -executable -o -name "*.so" -o -name "*.so.*" \) 2>/dev/null | while read elf; do
    echo "--- $elf ---"
    llvm-readelf -d "$elf" 2>/dev/null | grep NEEDED || true
done > "$DST_DIR/deps.txt"
```

<!-- ~~Step 3: 外部依赖收集~~ → 已迁移至 packaging.md §4 (Step 4: 收集外部依赖库到 lib/external/) -->

<!-- ~~Step 4: RPATH 设置~~ → 已迁移至 packaging.md §5 (设置 $ORIGIN 相对路径) -->

<!-- ~~Step 5: Strip + Debug 分离~~ → 已迁移至 packaging.md §6 (Strip debug 符号 + 分离保存) -->

<!-- ~~Step 6: ELF 签名~~ → 已迁移至 packaging.md §7 (adhoc self-sign 四步流程) -->

<!-- ~~Step 7: 生成 install.sh / uninstall.sh~~ → 已迁移至 packaging.md §9 (install.sh 模板 + gitcode 托管) -->

### Step 8：生成 README.md

> **⚠️ 注意**：tar.gz 不含 README.md。以下 README 仅作为 Release Notes 参考内容，发布到 GitCode Release 页面。

```sh
cat > "$DST_DIR/README.md" << EOF
# $SOFTWARE_NAME $VERSION - HarmonyOS 适配版

## 安装

使用 cmd-pkgs 公共安装脚本（一行命令安装）：

\`\`\`sh
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- $SOFTWARE_NAME $VERSION
\`\`\`

默认安装路径：\`~/usr/local/\`

## 环境变量

安装后请将以下内容添加到 \`~/.bashrc\`：

\`\`\`sh
export PATH="~/usr/local/bin:\$PATH"
export TMPDIR=/data/local/tmp
\`\`\`

## 目录结构

\`\`\`
$SOFTWARE_NAME-$VERSION-ohos-aarch64/
├── bin/          # 可执行文件
├── share/        # 文档和数据
└── lib/          # 共享库
    └── external/ # 外部依赖库
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

<!-- ~~Step 9-10: 打包 + 验证~~ → 已迁移至 packaging.md §10 (打包 tar.gz + 安装验证) -->

<!-- ~~§4 install.sh / uninstall.sh 模板规范~~ → 已迁移至 packaging.md §9 (install.sh 通用模板 + 禁止事项) -->

## §5 GitCode Release 发布流程

### Step 1：创建 Git Tag

```sh
git tag -a "v${SOFTWARE_NAME}-${VERSION}-ohos" -m "${SOFTWARE_NAME} ${VERSION} HarmonyOS 适配版"
git push origin "v${SOFTWARE_NAME}-${VERSION}-ohos"
```

Tag 命名格式：`v{软件名}-{版本}-ohos`

### Step 2：创建 Release

在 GitCode 上创建 Release，填写以下信息：

- **标题**：`{软件名} {版本} - HarmonyOS 适配版`
- **附件**：
  - `{软件名}-{版本}-ohos-{arch}.tar.gz`（产物包）
  - `{软件名}-{版本}-patches.tar.gz`（补丁包）
  - `{软件名}-{版本}-ohos-{arch}-debug.tar.gz`（debug 包，可选）
- **Release Notes**：从 `manifest.yaml` 生成，包含：
  - 版本信息
  - 适配内容概述
  - 已知问题
  - 依赖说明
  - 编译环境信息

### Release Notes 模板

```markdown
## {软件名} {版本} - HarmonyOS 适配版

### 适配内容
- 基于 {软件名} {上游版本} 进行鸿蒙适配
- 包含 {补丁数量} 个适配补丁

### 下载
| 文件 | 说明 |
|------|------|
| `{软件名}-{版本}-ohos-{arch}.tar.gz` | 产物包（{架构}） |
| `{软件名}-{版本}-patches.tar.gz` | 补丁包（源码分发） |
| `{软件名}-{版本}-ohos-{arch}-debug.tar.gz` | Debug 符号包 |

### 安装
\```sh
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- {软件名} {版本}
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
.0 打包方式（业界参考）
��式（业界参考）
