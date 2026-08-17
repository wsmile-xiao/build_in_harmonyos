# perl-parallel-pipes 0.201 编译笔记

## 编译环境
- 构建系统: ExtUtils::MakeMaker (Makefile.PL) — Module::Build::Tiny 的回退方案
- 编译日期: 2026-07-03
- 编译器: 无需 C 编译器（纯 Perl 模块）
- 状态: published

## 编译步骤

1. 从 CPAN 下载 Parallel-Pipes-0.201.tar.gz
2. 初始化编译环境：`ohc-run.py init-build perl-parallel-pipes 0.201`
3. 生成 Makefile.PL（ExtUtils::MakeMaker，替代 Module::Build::Tiny）
4. 运行 `perl Makefile.PL INSTALLDIRS=site` 生成 Makefile
5. 运行 `make` 构建模块（.pm 文件复制到 blib/lib/）
6. 将 .pm 文件从 blib/lib/ 复制到 lib/ 目录
7. 生成 Conan 配方并验证：`ohc-run.py conan-init` + `ohc-run.py conan-verify`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Conan basic_layout 创建 `build/` 目录与 Module::Build::Tiny 的 `Build` 脚本冲突 | 大小写不敏感文件系统上 `build/` 和 `Build` 无法区分 | conanfile.py 中 `layout()` 使用 `pass` 而非 `basic_layout`，避免创建 build/ 目录 |
| 2 | Conan package() 默认安装无法被 G4 产物完整性检查找到 | Perl 模块安装到深层目录，非标准 bin/lib/include | 手动将 .pm 文件从 staging 重新组织到 `lib/` 目录 |
| 3 | conanfile.py 模板默认为 autotools/CMake，不适用于纯 Perl 模块 | conan-init 生成通用模板 | 手动替换为 Perl 专用配方，使用 `perl Build.PL` + `./Build` 构建流程 |
| 4 | CI worker 上 Module::Build::Tiny 不可用，`perl Build.PL` 失败 | CI worker 的 Perl 安装不包含 Module::Build::Tiny 模块 | 改用 ExtUtils::MakeMaker (Makefile.PL)，动态生成 Makefile.PL 并用 `make` 构建 |

## 源码修改

无补丁。Parallel::Pipes 0.201 源码在鸿蒙平台上无需修改即可编译运行。

## 依赖版本

### 运行依赖
- perl 5.42.0 (系统预装)
- Storable (Perl 核心模块)
- IO::Handle (Perl 核心模块)
- IO::Select (Perl 核心模块)

### 编译依赖
无额外编译依赖。所有依赖均为 Perl 核心模块，随 perl 解释器一起安装。

## 验证结果

```bash
# 上游测试（5 个测试文件，全部通过）
$ PERL5LIB=$PKG_LIB perl t/00_use.t   → ok 1 - happy hacking!
$ PERL5LIB=$PKG_LIB perl t/01_basic.t → 7 assertions PASS (fork+pipe 基础功能)
$ PERL5LIB=$PKG_LIB perl t/02_big.t   → 1 assertion PASS (大数据传输)
$ PERL5LIB=$PKG_LIB perl t/03_app.t   → 14 assertions PASS (App 接口)
$ PERL5LIB=$PKG_LIB perl t/04_idle.t  → 23 assertions PASS (idle 回调)

# 平台兼容性测试
$ perl platform_test.pl → 5/5 PASS (fork, pipe, IO::Select, Storable, Storable over pipe)

# 综合功能测试
$ perl functional_test.pl → 7/7 PASS

# Conan 验证
$ ohc-run.py conan-verify perl-parallel-pipes 0.201 → 全门禁 PASS
```

## 知识沉淀

### 平台发现
- 鸿蒙系统 fork() 系统调用正常工作，可用于 Perl 多进程编程
- pipe(2) + IO::Select + Storable 组合在鸿蒙平台上完整可用
- 纯 Perl 模块无需处理 CRT 文件缺失、SELinux HMDFS 等问题（与 XS 模块不同）
- Module::Build::Tiny 构建系统在鸿蒙平台上可直接使用

### 编译建议
- 纯 Perl 模块 conanfile.py 应设置 `settings = ("os", "arch")`，排除 compiler/build_type
- `layout()` 使用 `pass` 避免 build/ 目录与 Build 脚本冲突
- `package()` 需手动将 .pm 文件重新组织到 lib/ 目录以通过 G4 检查
- `package_info()` 设置 `PERL5LIB` 环境变量供消费者使用

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（纯 Perl 模块专用） |
| conandata.yml | 源码 URL + sha256 |
| test_package/ | Conan L1 测试（模块加载验证） |
| test_package/MANIFEST.yml | 上游测试声明（5 个测试，46 断言） |
| reports/test-report.md | 功能测试报告 |
| reports/conan-verify-report.md | Conan 验证报告 |
| reports/conan-create.log | Conan create 日志 |

## 注意事项

1. 此模块为纯 Perl 实现，不涉及 C/XS 编译，无 CRT 文件或 SELinux 限制问题
2. fork() 在鸿蒙系统上正常工作，多进程并行处理可用
3. Storable 模块用于进程间数据序列化，通过 pipe(2) 传输，在鸿蒙平台上验证通过
4. 上游测试中的 `Time::HiRes::sleep` 在鸿蒙系统上正常工作

---

**编译结束**: 2026-07-06
**最终状态**: published (conan-verify 全门禁通过)
