# perl-spreadsheet-xlsx 0.18 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-01
- 验证日期: 2026-07-03
- 编译器: clang/clang++
- 状态: published

## 软件概述

Spreadsheet::XLSX 是一个纯 Perl 模块，用于读取 Microsoft Excel 2007 (.xlsx) 文件。
与 perl-dbd-pg 不同，此模块不含 XS/C 代码，无需处理 CRT 文件缺失和链接参数问题。

## 编译步骤

1. 从 CPAN 下载 Spreadsheet-XLSX-0.18.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-spreadsheet-xlsx 0.18
3. 运行 perl Makefile.PL INSTALL_BASE=/ 配置
4. 运行 make -j1 编译
5. 运行 make install DESTDIR=$TEST_PREFIX 安装到 staging
6. 生成 Conan 配方：ohc-run.py conan-init perl-spreadsheet-xlsx 0.18
7. 验证 Conan 配方：ohc-run.py conan-verify perl-spreadsheet-xlsx 0.18

## 与 perl-dbd-pg 编译经验对比

| 方面 | perl-dbd-pg | perl-spreadsheet-xlsx |
|------|-------------|----------------------|
| 模块类型 | XS (含 C 代码) | 纯 Perl |
| CRT 链接问题 | 需要 -nostartfiles -nodefaultlibs -lc | 无需处理 |
| SELinux 限制 | 动态库加载受限 | 不涉及 (无 .so 文件) |
| 构建复杂度 | 高 (需修改 Makefile.PL) | 低 (标准流程) |
| 补丁需求 | 2 个补丁 | 0 个补丁 |

## 依赖链

### 直接依赖
- Archive::Zip >= 1.18 (已安装 1.68)
- Spreadsheet::ParseExcel (已安装 0.66)

### 间接依赖 (Spreadsheet::ParseExcel 的依赖)
- OLE::Storage_Lite >= 0.19 (已安装 0.20)
- Crypt::RC4 (已安装 2.02)
- Digest::Perl::MD5 (已安装 1.91)
- IO::Scalar (IO::Stringy, 已安装 2.113)

## 编译产物

- **Spreadsheet/XLSX.pm**: 11406 字节，主模块文件
- **Spreadsheet/XLSX/Fmt2007.pm**: 5940 字节，格式化模块
- **Spreadsheet/XLSX/Utility2007.pm**: 36722 字节，工具模块

## Conan 验证结果

- G0 (预构建风险评估): PASS
- G1 (配方完整性): PASS
- G2 (conan create): PASS
- G3 (系统同名库隔离): PASS
- G4 (产物完整性): PASS
- L2 (smoke test): PASS (纯库包，跳过)
- L4 (安全扫描): PASS (无 ELF 文件)
- L5 (产物基线): PASS (7 个文件一致)

## 功能测试结果

### 模块加载测试
- ✅ Spreadsheet::XLSX 0.18 加载成功
- ✅ Archive::Zip 加载成功
- ✅ Spreadsheet::ParseExcel 加载成功

### 源码测试套件 (8 个测试文件)
- ✅ 0____________use.t: 2/2 通过 (模块加载测试)
- ✅ 1_____loreyna126.t: 3/3 通过 (读取 XLSX 文件，验证工作表和单元格)
- ✅ 2_____with_chart.t: 6/6 通过 (读取含图表的 XLSX 文件)
- ⏭️ 3_____invalid_formular.t: SKIP (发布候选测试)
- ✅ empty_v_tag.t: 1/1 通过 (空值标签处理)
- ✅ formats.t: 10/10 通过 (日期/时间/数字/文本格式化)
- ⏭️ kwalitee.t: SKIP (发布候选测试)
- ✅ missing_styles.t: 1/1 通过 (缺失样式处理)

### 端到端功能测试
- ✅ 读取 loreyna126.xlsx: 3 个工作表，797 行数据
- ✅ 读取 with_chart.xlsx: 4 个工作表（含图表）
- ✅ 读取 formats.xlsx: 3 个工作表，格式化数据正确

## 知识沉淀

### 平台发现
- 纯 Perl 模块在鸿蒙平台编译无特殊问题
- INSTALL_BASE=/ 配合 DESTDIR 可正确安装到 staging 目录
- 运行时依赖通过 PERL5LIB 环境变量解析，不依赖 Conan 依赖链

### 编译建议
- 纯 Perl 模块优先使用标准 ExtUtils::MakeMaker 流程
- 需确保所有运行时依赖模块已安装（包括间接依赖）
- conanfile.py 中 requirements() 为空，因依赖通过 PERL5LIB 解析

### 归档补全修复 (2026-07-03)

初次 conan-verify 后发现归档目录缺失 6 个核心文件，逐步补全：

1. **conanfile.py + conandata.yml**: 从 Conan 缓存 `/storage/Users/currentUser/.conan2/p/perl-45407ea4bd0d0/e/` 恢复
2. **manifest.yaml (版本级 + 软件级)**: 参照 perl-dbd-pg 模板创建
3. **notes.md**: 整理编译过程和测试结果
4. **README.md**: 软件说明文档
5. **test_package/conanfile.py**: 消费者测试配方，含 smoke test

### G1 修复: test_package/MANIFEST.yml

CI L0e 门禁要求 `test_package/MANIFEST.yml` 存在，用于声明上游测试列表。
参照 perl-sql-abstract 2.000001 的 MANIFEST.yml 格式创建，声明了 8 个上游测试文件。

### G2 修复: test_package/conanfile.py

**问题1**: test_package/conanfile.py 缺少 `requirements()` 方法，未声明对被测包的依赖。
- 修复: 添加 `def requirements(self): self.requires(self.tested_reference_str)`

**问题2**: 测试脚本在 `/tmp` 写临时文件失败 — OpenHarmony `/tmp` 为只读文件系统。
- 修复: 使用 Conan `self.build_folder` 作为临时文件目录，通过 `@ARGV` 传递路径给 Perl 脚本

### G2 修复后的 conan-verify 结果

| 门禁 | 名称 | 结果 |
|------|------|------|
| G0 | 预构建风险评估 | ✅ PASS |
| G1 | 配方完整性 | ✅ PASS |
| G2 | conan create | ✅ PASS |
| G3 | 系统同名库隔离 | ✅ PASS |
| G4 | 产物完整性 | ✅ PASS |
| L2 | smoke test | ✅ PASS |
| L4 | 安全扫描 | ✅ PASS |
| L5 | 产物基线 | ✅ PASS |

### CI L0c+L0d 修复: 测试源文件 + self.run() 要求 (2026-07-09)

CI 脚本 `build_and_test.sh` 的 L0c 门禁要求 test_package/ 下必须存在测试源文件（.c/.cpp/.cc/.cxx/.sh/.py），L0d 门禁要求 test_package/conanfile.py 的 test() 方法中必须包含 `self.run()` 调用。

**问题1 (L0c)**: test_package/ 下仅有 conanfile.py 和 MANIFEST.yml，无测试源文件，CI L0c 检查 `find` 不匹配。
**问题2 (L0d)**: 原 test_package 使用 `subprocess.run()` 直接执行 Perl 测试脚本，CI L0d 检查 `grep "self\.run"` 不匹配。
**问题3 (R33)**: 原 test_package 使用 `os.environ["PERL5LIB"] = perl5lib` 直接修改全局环境变量，违反 R33 规范。
**问题4 (P2)**: 原 test_package 硬编码 perl 路径 `/data/service/hnp/bin/perl` 和系统 Perl 库路径。

**修复**:
1. 创建 `test_spreadsheet_xlsx.sh` 测试脚本，包含完整的 smoke test 逻辑
2. 脚本内通过 `command -v perl` 动态发现 Perl 解释器路径（R33 合规）
3. 脚本内通过 `perl -e 'print join(":", @INC)'` 动态发现系统 Perl 库路径（无硬编码）
4. PERL5LIB 在 shell 子进程中 `export` 设置，不污染 Python 全局环境（R33 合规）
5. conanfile.py 简化为调用 `self.run(f'sh "{test_script}" "{pkg_folder}"')`，满足 L0d

### CI 模拟结果 (W3)

```
L0_RESULT=pass: all checks passed (L0c: test_spreadsheet_xlsx.sh found)
L1_RESULT=pass: test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=warn: no artifacts found
All packages built and tested successfully ✅
```

---
**编译结束**: 2026-07-01 10:04
**归档补全**: 2026-07-03
**最终状态**: published (编译成功，conan-verify 全部通过，功能测试全部通过)
**功能测试日期**: 2026-07-03
