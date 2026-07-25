# bowtie2

**简介**: 快速灵敏的带间隔读段比对工具，用于将下一代测序数据比对到参考基因组

**主页**: https://bowtie-bio.sourceforge.net/bowtie2/

**许可证**: GPL-3.0-or-later

**分类**: data（生物信息数据处理）

**构建系统**: Makefile（纯 Makefile，无 configure 脚本）

## 版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.5.5 | built | 2026-07-17 | aarch64-OHOS 适配 |

## 产物

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

## OHOS 适配要点

- 纯 Makefile 项目（无 configure 脚本），通过 SHELL/CC/CXX/CPPFLAGS/CXXFLAGS/LDFLAGS 环境变量注入编译配置
- aarch64 上 SSE2 内联函数通过 SIMD Everywhere（simde/x86/sse2.h）实现可移植
- Release tarball 不含 simde submodule，需在 source() 中从 simde-no-tests 仓库填充 third_party/simde
- OHOS 无 /bin/bash，Makefile 内 shell 命令必须显式指定 SHELL=/data/service/hnp/bin/bash
- R26: -stdlib=libc++ 必须同时出现在 CXXFLAGS 和 LDFLAGS
- 无标准 make check 目标，上游 simple-test 依赖 Perl + aarch64 运行时，已加入 no_official_test.txt 白名单

## 依赖

- **zlib/1.3.1** — Conan 仓库已发布（Makefile 硬编码 `-lz`）
- **pthread** — sysroot 提供
- **simde** — 上游 git submodule（third_party/simde），已在 conandata.yml 声明并自动填充

## 已知限制

- bowtie2 Perl 包装脚本（`bowtie2`）在无 Perl 环境下不可用；Python3 包装脚本可直接使用
- 上游 `make simple-test` 因 Perl 依赖 + 交叉编译架构不匹配而跳过
- 不支持 SRA 输入（`USE_SRA` 未启用）
- 不支持 zstd 压缩（`WITH_ZSTD` 未启用）
