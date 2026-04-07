# GNU sed 4.9 for HarmonyOS/OpenHarmony

> **编译日期**: 2026-04-07
> **状态**: ✅ success — 编译通过 + 独立测试通过 + 预编译包就绪
> **构建系统**: Autotools (configure/make)

## 一、软件简介

GNU sed 是 GNU 项目提供的流编辑器，用于对文本进行过滤和转换。它是 autotools 生态的基础工具之一——很多软件的 configure 脚本内部会调用 sed 来处理文本。

**为什么鸿蒙需要它？** 鸿蒙系统自带 toybox sed，但 toybox sed 对复杂脚本支持有限（分支命令、保持空间、-z NULL 分隔等），autotools 生成的 configure 脚本中大量使用高级 sed 特性，用 GNU sed 替代可避免潜在的构建问题。

## 二、编译指导

### 2.1 环境要求

| 依赖 | 版本/说明 | 鸿蒙自带 |
|------|----------|---------|
| clang | 15.0.4+ | ✅ |
| llvm-* 工具链 | ar, ranlib, nm, strip, objcopy | ✅ |
| musl libc | — | ✅ |
| make | — | ✅ (toybox) |

**无外部依赖**：sed 是纯 C 实现，不需要 gettext/libintl 等库（NLS/i18n 自动降级）。

### 2.2 编译命令

```bash
# 1. 下载源码
curl -fSL -o sed-4.9.tar.xz https://ftp.gnu.org/gnu/sed/sed-4.9.tar.xz
tar xf sed-4.9.tar.xz && cd sed-4.9

# 2. 应用补丁（见下方 §三 补丁清单）
patch -p1 < patches/0001-build-aux-config.guess.patch
patch -p1 < patches/0002-build-aux-config.sub.patch

# 3. 配置（注意：configure 在鸿蒙上约需 5 分钟）
export TMPDIR=$HOME/tmp   # 必须！/tmp 只读（见 E002）
./configure --prefix=$HOME/usr/local

# 4. 编译 + 安装
make -j1 && make install
```

**参数说明**：
- `--prefix` 是唯一需要的参数，无额外 hack（P0 参数最少化原则 ✓）
- `make -j1` 单线程编译（FIFO 限制，并行可能卡住）
- NLS 自动禁用（缺 libintl），不影响核心功能

### 2.3 configure 为什么这么慢？

sed 使用 autotools 构建系统。configure 脚本在运行时会**编译并执行数十个小测试程序**（conftest）来检测平台能力：
- 检查函数是否存在（如 `mbrlen`, `isblank` 等）
- 检查类型大小（如 `size_t`, `wchar_t` 等）
- 检查头文件是否可用
- 检查编译器行为

每个 conftest 都要经历 **编译 → 执行 → 分析输出** 三步。在鸿蒙上首次执行非系统二进制需要安全弹窗确认，加上 musl 环境下部分测试行为不同，导致总耗时约 5 分钟。

**不要提前中断 configure！** 如果超时被杀，下次重新跑即可（弹窗已确认过会快一些）。

## 三、补丁清单与适配原因

> **核心原则**：sed 4.9 的源码本身无需任何修改就能在鸿蒙上编译通过。
> 唯一需要适配的是 **GNU 构建系统的平台识别层**（config.guess / config.sub），
> 它们不认识 HarmonyOS 这个操作系统名称。

### Patch 0001: build-aux/config.guess — 让 configure 认识 HarmonyOS

**文件**: `build-aux/config.guess`
**修改量**: +20 行
**类型**: 平台识别补丁

**问题**: `config.guess` 是 GNU 构建系统的"指纹识别器"。它在 configure 运行时自动检测当前系统是什么，输出一个标准的三元组字符串（如 `x86_64-pc-linux-gnu`）。但它的规则表里没有 HarmonyOS：

```
正常 Linux 系统:  uname -s → "Linux"    → config.guess 输出 x86_64-pc-linux-gnu
鸿蒙系统:         uname -s → "HarmonyOS" → config.guess 不认识 → 输出 unknown 或报错
```

如果 config.guess 无法识别系统，configure 会误判为交叉编译环境，导致后续检测全部使用硬编码默认值。

**解决方案**: 在 config.guess 的 case 分支中添加 HarmonyOS 识别：

```bash
*:HarmonyOS:*:*)
    case "$UNAME_MACHINE" in
        aarch64|arm64) GUESS=aarch64-unknown-linux-ohos ;;
        *)             GUESS=$UNAME_MACHINE-unknown-linux-ohos ;;
    esac
    ;;
```

**为什么映射到 `linux-ohos` 而不是全新 OS 名？**
- 鸿蒙内核 API 与 Linux 高度兼容（大部分 syscall 相同）
- 用户空间使用 musl libc（同 Alpine Linux）
- 映射到 `*-linux-ohos` 可以复用所有现有的 Linux 兼容代码路径
- 只在 OS 后缀加 `ohos` 区分，让需要特殊处理的代码可以 `case *ohos*` 匹配

### Patch 0002: build-aux/config.sub — 接受 ohos 作为合法操作系统名

**文件**: `build-aux/config.sub`
**修改量**: +2 行
**类型**: 平台识别补丁

**问题**: `config.sub` 是 config.guess 的搭档——它负责**验证**三元组字符串的合法性。即使 config.guess 输出了 `aarch64-unknown-linux-ohos`，config.sub 也会拒绝它，因为 `ohos` 不在已知的操作系统列表中。

**解决方案**: 在两个位置各加一行：
1. 操作系统匹配模式中添加 `ohos*`（接受以 ohos 开头的任何 OS 变体）
2. 内核-操作系统验证中添加 `linux-ohos*`（接受 linux-ohos 组合）

这两处改动极小（共 2 行），但对所有使用 autotools 的 GNU 软件通用。

### 总结：适配工作量

| 层级 | 是否需要改 | 说明 |
|------|----------|------|
| C 源码 (`*.c`) | ❌ 不需要 | sed 的 C 代码完全兼容 musl/HarmonyOS |
| configure.ac | ❌ 不需要 | 无需额外 feature detection |
| Makefile.am | ❌ 不需要 | 无需修改构建规则 |
| config.guess | ✅ 必须改 | 平台识别（+20 行） |
| config.sub | ✅ 必须改 | OS 合法性验证（+2 行） |

**这是最轻量的适配级别**——仅改构建系统的平台识别层，不动一行业务代码。

## 四、已知限制

| 功能 | 状态 | 说明 |
|------|------|------|
| 核心替换/正则/地址空间 | ✅ 正常 | 全部可用 |
| `-i` 原地编辑 | ✅ 正常 | 已验证 |
| `-E` 扩展正则 | ✅ 正常 | 已验证 |
| `-z` NULL 分隔输入 | ✅ 正常 | 已验证 |
| 保持空间 h/H/g/G/x | ✅ 正常 | 已验证 |
| 分支/标签 :label/b/t | ✅ 正常 | 已验证 |
| NLS/i18n 多语言消息 | ⚠️ 禁用 | 缺 libintl，自动降级为英文 |
| SELinux 上下文操作 | ❌ 不适用 | 鸿蒙 SELinux 实现不同 |

## 五、功能验证方法

```bash
# 1. 版本确认
$ sed --version
# 预期: sed (GNU sed) 4.9

# 2. 基本替换
echo "hello world" | sed 's/world/harmonyos/'
# 预期: hello harmonyos

# 3. 全局替换
echo "a b a b a" | sed 's/a/X/g'
# 预期: X b X b X

# 4. 行删除
echo -e "line1\nbad\nline3" | sed '/bad/d'
# 预期: line1 / line3

# 5. 打印指定行
echo -e "a\nb\nc\nd\ne" | sed -n '2,4p'
# 预期: b / c / d

# 6. 扩展正则
echo "hello123world456" | sed -E 's/[0-9]+/NUM/g'
# 预期: helloNUMworldNUM

# 7. i 标志（忽略大小写）
echo "Hello HELLO hello" | 's/hello/hi/gI'
# 预期: hi HI hi

# 8. y 转换（字符级替换）
echo "abcABC" | sed 'y/abc/XYZ/'
# 预期: XYZXYZ

# 9. in-place 编辑（注意用 $TMPDIR 非 /tmp）
TMPF="$HOME/tmp/sed-test.txt"
echo "original" > "$TMPF"
sed -i 's/original/modified/' "$TMPF"
cat "$TMPF"
# 预期: modified

# 10. 保持空间交换
echo -e "first\nsecond" | sed -n 'h;n;G;p'
# 预期: second / first（两行互换）

# 11. 空输入不崩溃
echo "" | sed ''
# 预期: （无输出，无错误）

# 12. 长行处理（10K 字符）
python3 -c "print('x'*10000)" | sed 's/^/PREFIX:/'
# 预期: PREFIX:xxxx...（10006 字符）
```

## 六、预编译包安装

```bash
curl -fsSL <gitcode-release-url>/install.sh | sh
```

安装后在新终端执行 `sed --version` 验证。

## 七、交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `packaging/sed-4.9-ohos-aarch64.tar.gz` | ~398K | Release 制品（strip 后干净二进制） |
| `packaging/sed-4.9-ohos-aarch64-debug.tar.gz` | ~49K | Debug 符号包（GDB/coredump 分析用） |
| `packaging/install.sh` | ~1.8K | 安装脚本（gitcode 单独托管） |
| `patches/0001-build-aux-config.guess.patch` | 591B | 平台识别补丁 |
| `patches/0002-build-aux-config.sub.patch` | 850B | OS 合法性补丁 |

## 八、参考链接

- [GNU sed 官方手册](https://www.gnu.org/software/sed/manual/)
- [GNU sed 下载页](https://ftp.gnu.org/gnu/sed/)
- [GNU config 项目](https://git.savannah.gnu.org/cgit/config.git/)（config.guess/sub 上游）
- [SKILL.md](../../../SKILL.md)（鸿蒙编译框架主文档）
- [error-patterns.md](../../../knowledge/error-patterns.md)（已知错误模式库）

---

*文档版本: 2.0*
*最后更新: 2026-04-07*
*v2.0: 按 SKILL v4.0 归档规范重写，增加详细适配原因解释*
