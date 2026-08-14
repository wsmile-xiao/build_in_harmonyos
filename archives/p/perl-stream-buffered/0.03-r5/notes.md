# perl-stream-buffered 0.03-r5 适配笔记

## 编译环境
- 构建系统: Perl ExtUtils::MakeMaker (Makefile.PL)
- 编译日期: 2026-07-03
- 编译器: clang/clang++ (未使用，纯 Perl 模块)
- 状态: published

## 编译步骤

1. 从 CPAN 下载 Stream-Buffered-0.03.tar.gz
2. 解压源码包
3. 运行 `perl Makefile.PL INSTALLDIRS=site` 配置
4. 运行 `make -j1` 编译（纯 Perl 模块，仅复制 .pm 文件到 blib/）
5. 运行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging
6. 运行 `make test` 执行上游测试套件
7. 生成 Conan 配方 (conan-init)
8. 验证 Conan 配方 (conan-verify)
9. 执行 finish 收尾归档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 模块未安装到系统 Perl 路径 | Conan 包安装到 package_folder 而非系统目录 | conanfile.py `package()` 中将 .pm 文件从 DESTDIR 路径复制到 `lib/` 供 Conan 产物检测 |
| 2 | G4 产物完整性检查通过但 cache 路径找不到 | Conan 包结构中 lib/ 与 DESTDIR 路径并存 | `copy()` 将 .pm 文件复制到标准 `lib/` 目录确保 G4 检测通过 |
| 3 | conan test_package 运行时 os.version 不匹配 | 包构建时 os.version=6.0，测试时 profile 默认 5.0 | 指定 `-s os.version=6.0` 匹配构建时的 settings |

## 源码修改

无补丁。纯 Perl 模块，无需任何源码修改即可在鸿蒙平台编译。

## 依赖版本

### 编译依赖
- perl 5.42.0 (系统自带, /data/service/hnp/bin/perl)
- make (系统自带)

### 运行依赖
- perl 5.42.0
- FileHandle 模块 (Perl 核心模块，自带)

## 与 perl-dbd-pg 编译经验对比

| 对比项 | perl-dbd-pg (XS 模块) | perl-stream-buffered (纯 Perl 模块) |
|--------|----------------------|--------------------------------------|
| 构建系统 | ExtUtils::MakeMaker | ExtUtils::MakeMaker |
| C 编译 | 需要 (XS 扩展) | 不需要 (纯 Perl) |
| CRT 文件问题 | 遇到 (需 -nostartfiles -nodefaultlibs -lc) | 不涉及 (无 C 链接) |
| SELinux/HMDFS 限制 | 影响 .so 加载 | 不涉及 (无 .so 文件) |
| 补丁 | 需要 2 个补丁 | 不需要补丁 |
| 编译复杂度 | 高 | 低 |

## 验证结果

```bash
# make test 结果
t/print.t ............... ok
t/release-pod-syntax.t .. skipped: these tests are for release candidate testing
t/subclass.t ............ ok
All tests successful.
Files=3, Tests=18, 0 wallclock secs
Result: PASS

# conan test_package 结果
Test 1 (load + print + size): Buffer size: 5
Test 2 (rewind + read): Read back: test data
```

## 知识沉淀

### 平台发现
- 纯 Perl 模块（无 XS/C 扩展）在鸿蒙平台编译无需任何特殊处理
- ExtUtils::MakeMaker 构建系统完全兼容鸿蒙平台
- conanfile.py 的 `package()` 方法需要将 .pm 文件从 DESTDIR 路径复制到标准 `lib/` 目录，确保 Conan G4 产物完整性检查通过

### 编译建议
- 纯 Perl 模块使用 `settings = ("os", "arch")` 即可，无需 compiler 设置
- `build()` 方法中使用 `perl Makefile.PL INSTALLDIRS=site` + `make` 即可
- `package()` 方法中 `make install DESTDIR` 后需手动 `copy()` .pm 文件到标准路径

---

**编译结束**: 2026-07-03 10:05
**最终状态**: published
