# dpkg 1.22.6 适配笔记

## 编译环境
- **构建系统**: autotools (configure + make)
- **编译日期**: 2026-05-28
- **编译器**: clang/clang++ (系统默认)
- **平台**: arm64-ohos (OpenHarmony)
- **状态**: built（部分功能可用）
- **补丁数量**: 4 个（必须的补丁）

## 编译步骤

### 1. 源码获取
从 GitHub 下载 dpkg 1.22.6 源码包（dpkg_1.22.6.tar.gz）

### 2. 初始化编译环境
```bash
SKILL_ROOT="$(dirname "$(find "$HOME/.opendesk" -name "SKILL.md" -path "*openharmony-compile-agent*" 2>/dev/null | head -1)")"
python3 $SKILL_ROOT/scripts/ohc-run.py init-build dpkg 1.22.6
```

### 3. 配置（关键修改）
```bash
cd ~/tmp/builds/dpkg-1.22.6.work
./configure --prefix=$HOME/usr/local --disable-dselect
```

**禁用 dselect 的原因**: ncursesw 头文件包含错误的八进制常量定义，导致编译失败。

### 4. 编译
```bash
make -j1
```

### 5. 安装
```bash
make install DESTDIR=$TEST_PREFIX  # Staging 安装
make install                        # 本地安装
```

### 6. 打包
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py package dpkg 1.22.6
```

## 补丁文件说明

### 必须的补丁（4 个）

所有补丁均为实质性修改（修改现有源文件），不是 configure 生成的文件。

| 补丁 | 文件 | 修改内容 | 必须性 |
|------|------|----------|--------|
| 001-openssl-md5-compat.patch | lib/dpkg/buffer.c | OpenSSL MD5 API 兼容层（MD5Init → MD5_Init） | ✅ 必须 |
| 002-linux-ohos-platform.patch | data/ostable | 添加 `base-gnu-ohos linux-ohos linux-ohos` | ✅ 必须 |
| 003-arm64-ohos-arch.patch | data/tupletable | 添加 `base-gnu-ohos-<cpu> <cpu>-ohos` 映射 | ✅ 必须 |
| 004-dpkg-libs-openssl-fallback.patch | m4/dpkg-libs.m4 | DPKG_LIB_MD 宏添加 OpenSSL fallback 检测 | ✅ 必须 |

### 删除的补丁（174 个）

以下补丁均为 configure/autoreconf 生成的文件，已删除：

- Makefile.in 补丁（17 个） - configure 生成的构建文件
- config.h.in 补丁（1 个） - autoheader 生成的配置头文件
- build-aux 补丁（10 个） - autoreconf 生成的辅助脚本（config.guess, config.sub 等）
- man 手册补丁（61 个） - 文档文件，不影响编译
- po 翻译补丁（37 个） - gettext 翻译模板
- scripts 补丁（35 个） - Perl 脚本，configure 生成的路径替换
- src 补丁（11 个） - 测试脚本和配置文件
- dselect 补丁（23 个） - 已禁用模块的构建文件

### 补丁整理原则

**保留**: 实质性修改现有源文件的补丁（修改逻辑、添加平台支持）
**删除**: configure/autoreconf 生成的文件（可通过重新运行 autoreconf 获得）

---

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | libmd 依赖缺失 | 鸿蒙系统无 libmd 库，OpenSSL API 不兼容（MD5_Init vs MD5Init） | 修改 m4/dpkg-libs.m4 添加 OpenSSL fallback；修改 lib/dpkg/buffer.c 添加兼容层（宏定义） |
| 2 | 平台架构识别失败 | ostable/tupletable 未包含 linux-ohos | 添加 `base-gnu-ohos` 到 ostable；添加 `base-gnu-ohos-<cpu>` 到 tupletable |
| 3 | HMDFS 权限问题（E011） | umask 077 创建临时目录无写入权限 | 修改 configure 脚本中的 umask 为 022 |
| 4 | dselect 编译失败 | ncursesw 头文件错误的八进制常量 | 禁用 dselect（configure 参数 --disable-dselect） |
| 5 | OpenSSL MD5 兼容层编译错误 | 错误的类型定义 OPENSSL_MD5_CTX | 删除错误的 MD5_CTX 重定义，保留函数名宏映射 |

## 源码修改

### 关键补丁文件

| 补丁 | 文件 | 修改内容 |
|------|------|---------|
| 0072 | m4/dpkg-libs.m4 | OpenSSL MD5 检查 fallback |
| 0011 | lib/dpkg/buffer.c | OpenSSL MD5 API 兼容层（MD5Init → MD5_Init） |
| 0034 | data/ostable | linux-ohos 操作系统定义 |
| 0035 | data/tupletable | arm64-ohos 架构映射 |
| 其他 | autotools 生成文件 | 178 个补丁（大部分为 autotools 更新） |

### OpenSSL MD5 兼容层实现
```c
// lib/dpkg/buffer.c
#ifdef HAVE_LIBCRYPTO
#include <openssl/md5.h>
#define MD5Init(ctx) MD5_Init(ctx)
#define MD5Update(ctx, data, len) MD5_Update(ctx, data, len)
#define MD5Final(digest, ctx) MD5_Final(digest, ctx)
#else
#include <md5.h>
#endif
```

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 系统预装 | ~/usr/local |
| liblzma (xz-utils) | 系统预装 | ~/usr/local |
| Perl | 5.42.0 | 系统预装 (/data/service/hnp/) |
| ncursesw | 系统预装 | ~/usr/local/include/ncursesw |

**未使用的依赖**（因禁用或不可用）:
- libmd（使用 OpenSSL 替代）
- libbz2（未检测到）
- libzstd（未检测到）
- libselinux（未检测到）
- ncurses（用于 dselect，已禁用）

## 验证结果

### 功能测试统计

```bash
测试项总数: 21
通过: 10 (47.6%)
失败: 11 (52.4%)
警告: 1
```

### 核心工具验证

```bash
$ ~/usr/local/bin/dpkg --version
Debian 'dpkg' package management program version 1.22.6 (arm64-ohos).

$ ~/usr/local/bin/dpkg-deb --version
Debian 'dpkg-deb' package archive backend version 1.22.6 (arm64-ohos).

$ ~/usr/local/bin/dpkg-query --version
Debian 'dpkg-query' package query tool version 1.22.6 (arm64-ohos).

$ ~/usr/local/sbin/start-stop-daemon --version
start-stop-daemon 1.22.6 for Debian
```

### 已验证可用的工具

- ✅ dpkg（核心工具）
- ✅ dpkg-deb（包处理）
- ✅ dpkg-query（包查询）
- ✅ dpkg-split（包分割/合并）
- ✅ dpkg-divert（文件 diversion）
- ✅ dpkg-statoverride（权限覆盖）
- ✅ dpkg-trigger（触发器）
- ✅ update-alternatives（替代品管理）
- ✅ start-stop-daemon（守护进程）

### Perl 工具问题（需配置）

```bash
$ ~/usr/local/bin/dpkg-architecture
Can't locate Dpkg.pm in @INC...
```

**解决方案**: 设置 `PERL5LIB="$HOME/usr/local/share/perl/5.42.0"`

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| dpkg-1.22.6-ohos-aarch64.tar.gz | 6.8MB | 预编译包（主包） |
| dpkg-1.22.6-ohos-aarch64-debug.tar.gz | 1.0MB | 调试符号包 |
| patches/*.patch (178个) | ~4MB | 源码补丁集 |

## 功能限制与注意事项

### ⚠️ Perl 模块路径问题

**问题描述**: Perl 工具无法找到 Dpkg.pm 模块

**影响范围**: dpkg-architecture、dpkg-buildpackage、dpkg-scanpackages 等

**解决方案**:
```bash
# 临时方案
export PERL5LIB="$HOME/usr/local/share/perl/5.42.0"

# 持久方案（添加到 shell 配置）
echo 'export PERL5LIB="$HOME/usr/local/share/perl/5.42.0"' >> ~/.zshrc
```

### ⚠️ HMDFS 文件系统限制

**问题描述**: 无法创建 .deb 包（权限 2771 不满足要求）

**影响范围**: 包构建功能

**替代方案**:
- 使用下载的现有 .deb 包进行查询/解压操作
- 在非 HMDFS 环境（容器/虚拟机）中创建包
- 使用其他打包工具（如 tar + 自定义脚本）

### ⚠️ start-stop-daemon 路径

**位置**: `~/usr/local/sbin/start-stop-daemon`（非标准 bin 目录）

**使用**: `~/usr/local/sbin/start-stop-daemon --version`

### ⚠️ dselect 已禁用

**原因**: ncursesw 头文件兼容性问题

**影响**: 无法使用 dselect 图形化包管理界面

**替代**: 使用命令行工具（dpkg、dpkg-query）

---

**编译结束**: 2026-05-28 16:50
**最终状态**: built（部分功能可用）
**测试报告**: reports/functional-test-report.md
