# perl-specio-library-path-tiny 0.05 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-01 (初次) / 2026-07-02 (完善+测试)
- 编译器: clang/clang++（纯 Perl 模块，未实际使用 C 编译器）
- 状态: built (conan-verify 全部通过，功能测试全部通过)
- Conan 验证: 全部 PASS (G0-G4, L2, L4, L5) — 2026-07-02T16:45:29

## 软件简介

Specio::Library::Path::Tiny 是 Specio 类型系统的扩展库，为 Path::Tiny 文件路径对象
提供类型约束和强制转换。提供以下类型：
- Path — 任意 Path::Tiny 对象
- AbsPath — 绝对路径
- RealPath — 真实路径（无符号链接）
- File — 文件
- AbsFile — 绝对文件
- RealFile — 真实文件
- Dir — 目录
- AbsDir — 绝对目录
- RealDir — 真实目录

每种类型都支持从字符串和数组引用的强制转换。

## 编译步骤

1. 从 CPAN 下载 Specio-Library-Path-Tiny-0.05.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-specio-library-path-tiny 0.05
3. 运行 perl Makefile.PL INSTALLDIRS=site 配置
4. 运行 make -j1 编译（E074: HarmonyOS SELinux 禁止 FIFO，必须 -j1）
5. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging
6. 生成 Conan 配方：ohc-run.py conan-init perl-specio-library-path-tiny 0.05
7. 验证 Conan 配方：ohc-run.py conan-verify perl-specio-library-path-tiny 0.05
8. 收尾：ohc-run.py finish perl-specio-library-path-tiny 0.05 built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | make 并行编译失败 | HarmonyOS SELinux 禁止 FIFO 操作（E074） | 使用 `make -j1` 单线程编译 |
| 2 | conanfile.py/conandata.yml/test_package 缺失 | finish 步骤异常导致文件未归档 | 从 Conan 缓存恢复 + 重建 test_package |
| 3 | SPECIO_IMPLEMENTATION=PP 未设置 | 依赖 Specio，需要 PP 后端 | 在 conanfile.py package_info() 中通过 runenv_info.define() 设置 |

## 与 perl-dbd-pg 和 perl-specio 的对比

| 维度 | perl-dbd-pg | perl-specio | perl-specio-library-path-tiny |
|------|-------------|-------------|-------------------------------|
| 模块类型 | XS 模块（含 C 代码） | 纯 Perl 模块 | 纯 Perl 模块 |
| CRT 链接问题 | 需要 -nostartfiles -nodefaultlibs -lc | 不需要 | 不需要 |
| 补丁 | 2 个（Makefile + Makefile.PL） | 0 个 | 0 个 |
| 产物 | Pg.so + .pm 文件 | 42 个 .pm 文件 | 1 个 .pm 文件 |
| 构建复杂度 | 高（需要 pg_config, DBI, libpq） | 低 | 低 |
| 平台适配 | Makefile.PL 补丁 | SPECIO_IMPLEMENTATION=PP | 继承 Specio 的 PP 设置 |
| 依赖 | postgresql, perl-dbi | Clone::PP 等 | perl-specio, Path::Tiny |

## 依赖版本

### 运行时依赖（已安装到系统 Perl）
- perl-specio 0.53 (Conan 包)
- Path::Tiny (>=0.087, 系统 Perl 模块)
- Scalar::Util (Perl 核心)
- Specio::Declare, Specio::Library::Builtins, Specio::PartialDump, Specio::Exporter (perl-specio 子模块)

### 编译依赖
- perl 5.42.0 (ExtUtils::MakeMaker)

## 编译产物

- **1 个 .pm 文件**: `lib/Specio/Library/Path/Tiny.pm` (10498 bytes)
- 安装到 `lib/perl5/site_perl/5.42.0/` 目录

## 关键平台适配: SPECIO_IMPLEMENTATION=PP

### 背景
本模块依赖 Specio 类型系统。在鸿蒙平台上，Specio 必须使用 PP (Pure Perl) 后端，
因为系统 Clone 模块基于 Storable::dclone，不支持 CODE 引用克隆。

### 解决方案
1. 在 conanfile.py 的 `package_info()` 中通过 `runenv_info.define("SPECIO_IMPLEMENTATION", "PP")` 自动设置
2. 依赖的 perl-specio/0.53@ohpcd/stable 已设置相同环境变量
3. 消费者通过 `conan install` 自动获取 PERL5LIB 和环境变量

## 知识沉淀

### 平台发现
- 纯 Perl 模块在鸿蒙平台编译无需特殊适配
- HarmonyOS SELinux 禁止 FIFO，make 必须使用 -j1（E074）
- PERL5LIB 需包含系统 Perl site_perl 路径以加载运行时依赖
- 依赖 Specio 的模块需继承 SPECIO_IMPLEMENTATION=PP 环境变量
- Conan 配方 package_info() 可通过 runenv_info.define() 自动设置环境变量
- Specio 类型层级是扁平的：所有 8 种路径类型都是 Path 的直接子类型
- RealPath 类型通过 `realpath == self` 检查拒绝符号链接

### 编译建议
- 纯 Perl 模块（无 XS）的 Conan 配方中 generate() 无需设置工具链
- package_info() 通过 runenv_info.append_path("PERL5LIB", ...) 设置消费者环境
- package_info() 通过 runenv_info.define() 设置平台必需的环境变量
- INSTALLDIRS=site 确保安装到 site_perl 目录
- test_package/MANIFEST.yml 是 CI L0e 门禁的必需文件

## 功能测试结果

### Conan 集成测试
- `conan install --requires=perl-specio-library-path-tiny/0.05@ohpcd/stable` 成功
- 环境变量传播验证:
  - SPECIO_IMPLEMENTATION=PP ✅ (通过 runenv_info.define 自动设置)
  - PERL5LIB 包含包路径 + 依赖路径 ✅
- 消费者环境激活后模块加载成功 ✅
- 注意: Path::Tiny 是系统级运行时依赖，需额外加入 PERL5LIB

### 功能测试 (functional_test.pl) — 146/146 通过

| 测试模块 | 测试数 | 结果 |
|----------|--------|------|
| 模块加载与环境验证 | 6 | ✅ |
| 类型约束对象创建 (9种类型) | 18 | ✅ |
| 类型验证 - 接受有效值 | 17 | ✅ |
| 类型验证 - 拒绝无效值 | 48 | ✅ |
| 强制转换 (string/arrayref/object) | 14 | ✅ |
| 错误消息生成 | 4 | ✅ |
| 鸿蒙平台特有场景 | 12 | ✅ |
| 真实应用场景模拟 | 10 | ✅ |
| 内联约束验证 | 9 | ✅ |
| 类型关系验证 | 8 | ✅ |
| **合计** | **146** | **✅ 全部通过** |

### 鸿蒙平台特有场景覆盖
- HMDFS 路径 (`/storage/Users/currentUser`) ✅
- 系统服务路径 (`/data/service/hnp`) ✅
- Perl 安装路径 (`/data/service/hnp/perl.org/perl_5.42.0`) ✅
- 只读文件系统路径 (`/tmp` 只读) ✅ — 不崩溃
- 深层嵌套目录 (8层) ✅
- Unicode 文件名 ✅
- 符号链接处理 ✅ — Path 接受，RealPath 正确拒绝

### 真实应用场景覆盖
- 类型约束子程序 (coerce + slurp) ✅
- 路径拼接 (child + is_absolute) ✅
- 目录遍历 (iterator + is_dir/is_file) ✅
- 文件读写 (spew + lines) ✅
- 临时目录创建 (tempdir + RealDir 验证) ✅

### 依赖版本验证
| 模块 | 要求版本 | 实际版本 | 状态 |
|------|---------|---------|------|
| Path::Tiny | >=0.087 | 0.144 | ✅ |
| Specio | >=0.29 | 0.53 | ✅ |
| File::pushd | any | 1.016 | ✅ |
| Test::More | >=0.96 | 1.302210 | ✅ |
| File::Temp | >=0.18 | 0.2311 | ✅ |

### 测试中遇到的问题与修复
| # | 问题 | 根因 | 修复方案 |
|---|------|------|----------|
| 1 | 消费者测试写 /tmp 失败 | E002: HarmonyOS /tmp 只读 | 改用 $ENV{TMPDIR} 或 $HOME/tmp |
| 2 | 测试中硬编码 /tmp 路径 | 同上 | 替换为 $ENV{HOME} 绝对路径 |
| 3 | 清理代码 unlink 目录失败 | Path::Tiny remove() 对目录调用 unlink | 改用 remove_tree() |
| 4 | 上游测试缺 File::pushd | 测试依赖未预装 | 从 CPAN 下载安装到用户 site_perl |
| 5 | Specio::Declare 导入 t() 失败 | t() 由 Specio::Library::Path::Tiny 导出 | 移除 `use Specio::Declare qw(t)` |
| 6 | 类型层级断言错误 | 所有类型都是 Path 直接子类型 | 修正 is_a_type_of 断言 |

---
**编译结束**: 2026-07-01 10:05 (初次)
**完善+测试**: 2026-07-02 18:36
**最终状态**: built (编译成功，全部测试通过)
**上库评估**: ✅ 符合上库要求 (status: built)
  - conan-verify: G0-G4 + L2-L5 全部 PASS
  - 消费者测试: 44/44 通过
  - 功能测试: 146/146 通过
  - 上游测试: t/basic.t 47/47 + t/00-report-prereqs.t 1/1 = 48/48 通过
  - Conan 集成测试: 环境变量传播 + 消费者加载 ✅
  - 总计: 238/238 全部通过
---
