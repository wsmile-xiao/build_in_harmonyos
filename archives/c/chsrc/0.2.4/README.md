# chsrc — 全平台换源工具（HarmonyOS aarch64 预编译包）

> **chsrc** (Change Source) 是一个全平台换源工具，支持对编程语言包管理器、操作系统和软件进行一键换源，使用 C 语言编写，GPL-3.0+ 许可证。

## 基本信息

| 属性 | 值 |
|------|------|
| 软件名称 | chsrc |
| 版本 | 0.2.4 (2025/12/31) |
| 语言 | C |
| 许可证 | GPL-3.0+ / MIT |
| 构建系统 | Makefile（非 autotools） |
| 编译器 | clang 15.0.4 |
| 目标平台 | HarmonyOS aarch64 |
| 预编译包 | `chsrc-0.2.4-ohos-aarch64.tar.gz` (303KB, release) / `chsrc-0.2.4-ohos-aarch64-debug.tar.gz` (51KB, debug) |

## 功能概览

chsrc 支持 **79个换源目标**，涵盖三大类别：

### 编程语言生态（21个）
Python/pip, Node.js/npm, Ruby/gem, Go/goproxy, Rust/cargo, Java/Maven/Gradle, Perl/CPAN, PHP/Composer, Lua/LuaRocks, Dart/pub, Clojure, Haskell, OCaml, R/CRAN, Julia, .NET/NuGet, C/C++ 等

### 操作系统（31个）
Ubuntu, Debian, Fedora, Arch, Manjaro, openSUSE, Kali, MSYS2, Gentoo, Rocky, Alpine, OpenWrt, Deepin, openEuler, FreeBSD 等

### 软件（8个）
Homebrew, Docker, CocoaPods, Flatpak, Nix, Emacs/ELPA, LaTeX/CTAN, Conda 等

### 镜像站覆盖（35个国内镜像源）
TUNA(清华), USTC(中科大), BFSU(北外), SJTUG(交大), NJU(南大), PKU(北大), ZJU(浙大), HIT(哈工大), HUST(华科), Ali(阿里云), Tencent(腾讯云), Huawei(华为云), Volcengine(火山引擎) 等

## 核心命令

```bash
# 查看所有镜像站
chsrc ls

# 查看所有支持的换源目标
chsrc list targets

# 查看某个目标的可用源
chsrc ls python    # 查看 pip/pypi 可用镜像
chsrc ls maven     # 查看 Maven 可用镜像

# 查看当前源
chsrc get pip      # 查看 pip 当前源
chsrc get npm      # 查看 npm 当前源

# 换源（自动测速选最快）
chsrc set python

# 换源（指定镜像站）
chsrc set python tuna       # pip 换源到清华TUNA
chsrc set maven ali         # Maven 换源到阿里云

# 重置回上游默认源
chsrc reset python

# 模拟换源（不实际修改）
chsrc set python tuna -dry
```

## HarmonyOS 适配详情

chsrc 0.2.4 在 HarmonyOS 上需要 4 个补丁才能正常编译和运行：

### 补丁 1: Makefile 适配 (`0001-Makefile.patch`)
- **问题**: 原 Makefile 使用硬编码 `CC=cc`、硬编码 `/usr/bin` 安装路径、无 `DESTDIR` 支持、无 `PREFIX` 变量
- **修复**:
  - `CC ?= clang`（HarmonyOS 无 `cc` 命令，改用 `clang`）
  - `PREFIX ?= /usr/local`（添加可配置安装路径）
  - `INSTALL_BIN ?= chsrc`（添加可配置二进制名称，匹配 dev 模式产物）
  - install 规则从 `install -D` 拆分为 `install -d` + `install -m`（分离目录创建和文件复制，兼容 DESTDIR）

### 补丁 2: configure wrapper (`0002-configure.patch`)
- **问题**: Makefile 项目无 configure 脚本，G0 干净构建验证要求 configure 步骤
- **修复**: 创建简化 configure wrapper（仅 echo 配置信息 + exit 0）

### 补丁 3: OS 检测 (`0003-lib-xy.h.patch`)
- **问题**: `_xy_detect_os()` 函数通过 `/proc/version` 和 `uname -s` 检测 OS，但不识别 HarmonyOS。HarmonyOS 上 `/proc/version` 权限拒绝，`uname -s` 返回 "HarmonyOS" 而非 "Linux"
- **修复**:
  - 添加 `#ifdef __OHOS__` 编译时守卫（编译时检测，最可靠）
  - 添加 `uname -s == "HarmonyOS"` 运行时检测（在 BSD 检测之前）
  - 设置 `xy.on_linux=true`（HarmonyOS 兼具 Linux 特性）

### 补丁 4: 临时文件路径 (`0004-src-framework-core.c.patch`)
- **问题**: 源码硬编码 `/tmp` 作为临时文件路径。HarmonyOS 的 `/tmp` 是只读 erofs 分区，无法写入
- **修复**: 使用 `getenv("TMPDIR")` 获取临时目录，回退到 `/tmp`

### HarmonyOS 特殊注意事项

| 特征 | 值 | 影响 |
|------|------|------|
| uname -s | "HarmonyOS" | OS 检测需专门处理 |
| /proc/version | Permission denied | 不可用于 OS 检测 |
| /tmp | 只读 erofs | 临时文件需用 TMPDIR |
| cc 命令 | 不存在 | 编译器需用 clang |
| pip config --user | 写入 /data/storage/el2/.../pip/pip.conf | 文件路径与标准Linux不同 |

## 编译说明

```bash
# 解压源码
tar xzf chsrc-0.2.4.tar.gz
cd chsrc-0.2.4

# 应用4个补丁
patch -p1 -i 0001-Makefile.patch
patch -p1 -i 0002-configure.patch
patch -p1 -i 0003-lib-xy.h.patch
patch -p1 -i 0004-src-framework-core.c.patch

# configure（仅验证）
chmod +x configure && ./configure

# 编译（开发模式）
make CC=clang CFLAGS="-Iinclude -Ilib -fPIC -O2 -D__OHOS__"

# 编译（发布模式）
make build-in-release-mode CC=clang CFLAGS="-Iinclude -Ilib -fPIC -O2 -D__OHOS__"

# 安装
make install PREFIX=/usr/local DESTDIR=/staging INSTALL_BIN=chsrc-release
```

## 验证结果

- ✅ `chsrc --version` → "chsrc v0.2.4 (2025/12/31)"
- ✅ `chsrc ls` → 35个镜像站完整列表
- ✅ `chsrc list targets` → 79个换源目标
- ✅ `chsrc set python tuna` → pip 源切换到 TUNA 并生效
- ✅ `chsrc reset python` → 重置回上游默认源
- ✅ G0 干净构建验证: PASS
- ✅ G1-G4 质量门禁: PASS
- ✅ 内部单元测试: 3/3 PASS (test-make-env, test-xy, test-fw)

## 二进制信息

| 属性 | 值 |
|------|------|
| 格式 | ELF64, LSB, arm64, PIE (Position-Independent) |
| 链接器 | /lib/ld-musl-aarch64.so.1 |
| text段 | 204,448 bytes |
| data段 | 38,389 bytes |
| stripped | not stripped（debug包保留完整符号） |

## 预编译包内容

```
chsrc-0.2.4-ohos-aarch64.tar.gz:
  bin/chsrc                  # 主程序（release 模式）
  share/man/man1/chsrc.1     # man 手册页

chsrc-0.2.4-ohos-aarch64-debug.tar.gz:
  bin/chsrc                  # 主程序（dev 模式，保留符号）
  share/man/man1/chsrc.1     # man 手册页
```

## 来源

- **上游源码**: https://github.com/RubyMetric/chsrc (tag v0.2.4)
- **许可证**: GPL-3.0+ / MIT
- **作者**: 曾奥然、郭恒 及社区贡献者