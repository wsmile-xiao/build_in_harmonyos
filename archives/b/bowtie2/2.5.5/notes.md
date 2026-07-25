# bowtie2 2.5.5 适配笔记

## 软件概述

bowtie2 是一个快速灵敏的带间隔读段比对工具，用于将下一代测序数据（NGS reads）
比对到参考基因组。采用 C++11 编写，使用纯 Makefile 构建系统（非 autotools / cmake）。

上游仓库: https://github.com/BenLangmead/bowtie2
上游版本: v2.5.5
许可证: GPL-3.0

## 源码来源

- 主源码: `https://github.com/BenLangmead/bowtie2/archive/refs/tags/v2.5.5.tar.gz`
  - SHA256: `e38d1833ec235ca27fa57589d32d897c9addf87085b7cb7bc978662954662da2`
- simde submodule: `https://github.com/simd-everywhere/simde-no-tests/archive/f6a0b3b2882226e98496be9147265e05c7127c1f.tar.gz`
  - SHA256: `b354eb97cbb74d9bf246db2f87f5c07a5bd64d696f6aacd0bbcca19054a8567b`
  - 提交: f6a0b3b2882226e98496be9147265e05c7127c1f (对应 .gitmodules 中 third_party/simde 的 master 分支)

> 注: CI worker 无法访问 GitHub，后续如 CI 报下载失败，需切换到 GitCode 镜像 URL。

## 编译环境

- 构建系统: Makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-07-17
- 目标平台: aarch64-OHOS (HarmonyOS PC)
- 编译器: 由 Conan conf `tools.build:compiler_executables` 提供（默认回退 `/data/service/hnp/bin/clang` / `clang++`）
- 适配路径: A（基础适配）

## 编译步骤

1. `conan source` 下载主源码（`get(..., strip_root=True)`）。
2. **填充 simde submodule** — `source()` 从 conandata.yml 的 `simde` 字段下载 simde-no-tests 压缩包，解压到 `third_party/simde/` 目录。
3. `make -j1 SHELL=... CC=... CXX=... CPPFLAGS="... -Ithird_party" CXXFLAGS="-stdlib=libc++" LDFLAGS="-stdlib=libc++ ..." all`
4. 拷贝 6 个 ELF 二进制 + 3 个包装脚本到 `package/bin/`。

Makefile 自动检测 aarch64 平台（第 92-98 行）：
- `uname -m` → aarch64 → BITS=64, SSE_FLAG 为空, 添加 `-fopenmp-simd`
- `CPPFLAGS += -Ithird_party`（aarch64 专用，使 sse_wrap.h 能找到 `simde/x86/sse2.h`）
- `POPCNT_CAPABILITY ?= 0`（aarch64 不使用 POPCNT 硬件指令）

## 关键适配点

### 1. simde submodule 必须填充（aarch64 必需）
- `sse_wrap.h` 在 `__aarch64__`（或 `__s390x__`/`__powerpc__`）定义时无条件 `#include "simde/x86/sse2.h"`（第 115-119 行）。
- GitHub Release tarball **不包含** submodule 内容，`third_party/simde` 是空目录。
- 解决方案：在 conandata.yml 中声明 `simde` 额外源，`source()` 方法用 `get(..., destination=third_party/simde, strip_root=True)` 填充。

### 2. OHOS 无 /bin/bash
- bowtie2 Makefile 使用 `$(shell ...)` 调用 `cat` / `hostname` / `date` 等命令，需要 shell。
- OHOS 默认 shell 是 mksh，但 Makefile 中部分命令依赖 bash 语法。
- 解决方案：通过 `SHELL="/data/service/hnp/bin/bash"` 显式指定 shell。

### 3. R33: 编译器路径不硬编码
- 项目规则 R33 禁止在 recipe 中硬编码平台环境变量，必须从 Conan Toolchain 派生。
- 解决方案：通过 `self.conf.get("tools.build:compiler_executables", default={})` 读取编译器路径，仅在 conf 未设置时回退到 hnp 工具链路径。

### 4. R26: -stdlib=libc++ 同时在 CXXFLAGS 和 LDFLAGS
- OHOS 使用 libc++（非 libstdc++），编译和链接都需要 `-stdlib=libc++` 标志。
- bowtie2 Makefile 的链接行只携带 `LDLIBS`（`-lpthread -lz`），不传递 CXXFLAGS 给链接器。
- 解决方案：将 `-stdlib=libc++` 同时放入 `CXXFLAGS`（编译）和 `LDFLAGS`（链接）。

### 5. zlib 依赖
- Makefile 第 27 行硬编码 `LDLIBS := -lpthread -lz`。
- 解决方案：声明 `self.requires("zlib/1.3.1")`，在 build() 中从 `self.dependencies["zlib"].cpp_info` 提取 include/lib 路径，通过 `CPPFLAGS` 和 `LDFLAGS` 传递给 make。

### 6. 上游测试跳过
- bowtie2 上游测试目标 `make simple-test` 依赖 Perl + 多个 CPAN 模块（File::Which, Math::Random, Clone, Test::Deep, Sys::Info），且需要运行 aarch64 二进制。
- OHOS CI worker 为 x86_64 架构，无法运行 aarch64 二进制；OHOS 也不提供 Perl。
- 解决方案：将 `bowtie2` 添加到 `ci/config/no_official_test.txt` 白名单跳过 L1c 检查；在 test_package 中用真实功能验证替代（版本检查 + 索引构建）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `fatal error: 'simde/x86/sse2.h' file not found` | Release tarball 不含 git submodule 内容，third_party/simde 为空目录 | 在 conandata.yml 声明 simde 额外源，source() 方法填充 third_party/simde |
| 2 | OHOS 无 /bin/bash | Makefile 内 shell 命令依赖 bash | `SHELL="/data/service/hnp/bin/bash"` 显式指定 |
| 3 | 链接失败：找不到 libc++ 符号 | Makefile 链接行不传递 CXXFLAGS | `-stdlib=libc++` 同时放入 CXXFLAGS 和 LDFLAGS |
| 4 | 找不到 zlib.h / -lz | Makefile 硬编码 -lz，未指定路径 | 从 Conan zlib 依赖的 cpp_info 提取路径，通过 CPPFLAGS/LDFLAGS 传递 |
| 5 | 上游测试无法执行 | aarch64 二进制无法在 x86_64 CI worker 运行 + Perl 依赖 | 加入 no_official_test.txt 白名单；test_package 用版本检查+索引构建验证 |

## 产物清单

构建产物（6 个 ELF 二进制 + 3 个包装脚本）均安装到 `bin/`：

| 文件 | 类型 | 说明 |
|------|------|------|
| bowtie2-align-s | ELF | 小索引比对器（small index, ≤4Gb 参考） |
| bowtie2-align-l | ELF | 大索引比对器（large index, >4Gb 参考） |
| bowtie2-build-s | ELF | 小索引构建器 |
| bowtie2-build-l | ELF | 大索引构建器 |
| bowtie2-inspect-s | ELF | 小索引查看器 |
| bowtie2-inspect-l | ELF | 大索引查看器 |
| bowtie2 | Perl 脚本 | 用户面向包装脚本（需 Perl） |
| bowtie2-build | Python3 脚本 | 用户面向包装脚本（需 Python3） |
| bowtie2-inspect | Python3 脚本 | 用户面向包装脚本（需 Python3） |

## 依赖

- **zlib/1.3.1**（Conan 仓库已发布）— Makefile 硬编码 `-lz`
- **pthread** — sysroot 提供
- **simde** — 上游 git submodule（third_party/simde），已在 conandata.yml 声明并自动填充

## 源码修改

**无源码补丁**。所有适配通过 Conan recipe 的环境变量注入和 simde submodule 填充完成，未修改任何上游源代码。

## 验证

由于用户无 HarmonyOS PC 真机，本地无法运行 aarch64 二进制，所有验证依赖 CI：

- **编译验证**: 由 CI `conan-build-test` 步骤执行 `conan create` + `make all`
- **功能验证**: 由 CI `conan-test` 步骤执行 test_package/test_bowtie2.sh
  - 测试 1-3: `bowtie2-align-s` / `bowtie2-build-s` / `bowtie2-inspect-s` 的 `--version` 输出 2.5.5
  - 测试 4: `bowtie2-build-s` 对合成 FASTA 构建小索引，生成 `.1.bt2`
  - 测试 5: 验证 `.1.rev.bt2` 反向索引文件生成
  - 断言总数: 5（与 MANIFEST.yml 的 `assertion_count` 一致）

## 已知限制

- bowtie2 Perl 包装脚本（`bowtie2`）在无 Perl 环境下不可用；Python3 包装脚本（`bowtie2-build` / `bowtie2-inspect`）可直接使用。
- 上游 `make simple-test` 因 Perl 依赖 + 交叉编译架构不匹配而跳过。
- 不支持 SRA 输入（`USE_SRA` 未启用，需 ncbi-ngs/vdb 静态库）。
- 不支持 zstd 压缩（`WITH_ZSTD` 未启用，需 libzstd）。
