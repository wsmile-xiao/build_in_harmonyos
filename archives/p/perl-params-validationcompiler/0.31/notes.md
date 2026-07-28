# perl-params-validationcompiler 0.31 编译笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang 18.1.8 (aarch64-unknown-linux-ohos)
- Perl 版本: 5.42.0
- 状态: built (Conan 验证通过)

## 软件特点

Params::ValidationCompiler 是一个**纯 Perl 模块**，无 XS/C 编译代码。
与 perl-dbd-pg 等 XS 模块不同，本模块：
- 不需要 C 编译器链接（无 .so 生成）
- 不需要 musl C 库头文件
- 不需要 `-nostartfiles -nodefaultlibs -lc` 链接参数
- 不受 SELinux HMDFS 动态库加载限制
- 编译过程简单直接

## 编译步骤

1. 从 CPAN 下载 Params-ValidationCompiler-0.31.tar.gz
2. 初始化编译环境：ohc-run.py init-build perl-params-validationcompiler 0.31
3. 运行 `perl Makefile.PL INSTALL_BASE=/usr/local` 配置
4. 运行 `make` 编译
5. 运行 `make install DESTDIR=$dest` 安装到 staging
6. Conan 配方生成：ohc-run.py conan-init perl-params-validationcompiler 0.31
7. Conan 验证：ohc-run.py conan-verify perl-params-validationcompiler 0.31

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，编译无障碍 | - |

**与 perl-dbd-pg 编译经验对比**：

| 对比项 | perl-dbd-pg (XS 模块) | perl-params-validationcompiler (纯 Perl) |
|--------|----------------------|------------------------------------------|
| CRT 文件缺失 | ❌ 需要 `-nostartfiles -nodefaultlibs -lc` | ✅ 不涉及 |
| musl C 库头文件 | ❌ 需要 371 个头文件 | ✅ 不需要 |
| SELinux HMDFS 限制 | ❌ XS 模块需安装到 /data/service/hnp | ✅ 不受限制 |
| 补丁文件 | 2 个 (Makefile + Makefile.PL) | 0 个 |
| Conan 配方 | 无 (手动编译) | 有 (conan create 验证通过) |
| 编译复杂度 | 高 | 低 |

## 编译产物

- **ValidationCompiler.pm**: 主模块文件
- **ValidationCompiler/Compiler.pm**: 编译器实现
- **ValidationCompiler/Exceptions.pm**: 异常类定义

## 测试结果

- 模块自带测试套件: 20 个测试文件, 87 个测试, 全部通过
- Conan test_package: Perl 模块加载验证通过
- 功能测试: 8 项自定义测试全部通过

## 编译产物安装路径

`/usr/local/lib/site_perl/5.42.0/Params/ValidationCompiler/`

---
**编译结束**: 2026-07-03
**最终状态**: built (Conan 验证通过，测试套件全部通过)
**归档修复**: 2026-07-06 恢复缺失的归档文件

## 归档修复记录 (2026-07-06)

### 问题
原始编译成功但归档目录缺失多个关键文件：
- conanfile.py / conandata.yml（CI 输入）
- test_package/conanfile.py / MANIFEST.yml（CI 输入）
- manifest.yaml（软件级 + 版本级）
- README.md / notes.md
- test-report.md / quality-report.md
- packaging 产物

### 修复方案
1. 从 Conan 缓存 (`~/.conan2/p/perl-5a505048f6cab/e/`) 恢复 conanfile.py 和 conandata.yml
2. 参考 perl-net-cidr-lite 创建 test_package/conanfile.py 和 MANIFEST.yml
3. 参考 perl-dbd-pg 创建 manifest.yaml（软件级 + 版本级）、README.md、notes.md
4. 运行功能测试（10 项）和原始测试套件（87 项）生成 test-report.md
5. 创建 quality-report.md 质量评估报告
6. 创建 packaging tar.gz 打包产物
7. 清理 test_package 中的 Conan 生成文件

### 验证结果
- Conan 验证：G0-G4 + L2/L4/L5 全部 PASS
- 自检：6/6 PASS
- 功能测试：10/10 PASS
- 原始测试套件：87/87 PASS（1 项跳过）

### 参考 perl-dbd-pg 编译经验
- perl-dbd-pg 是 XS 模块，需要 `-nostartfiles -nodefaultlibs -lc` 链接参数和 musl C 库头文件
- 本模块是纯 Perl 模块，不受 CRT 文件缺失和 SELinux HMDFS 限制影响
- 两者编译复杂度差异显著：perl-dbd-pg 需 2 个补丁，本模块需 0 个补丁
