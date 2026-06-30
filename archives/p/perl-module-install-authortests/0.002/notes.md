# perl-module-install-authortests 0.002 适配笔记

## 编译环境
- 构建系统: Makefile.PL (Perl ExtUtils)
- 编译日期: 2026-06-18
- 编译器: clang/clang++ (Clang 21.1.5, Harmonybrew ohos-llvm)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

1. 下载源码包 `Module-Install-AuthorTests-0.002.tar.gz`，SHA256: `4025722de6357edf53c28501b00e7da92cd2f9fc611ba0753761a0e1dff32d88`
2. 解压到构建目录 `~/tmp/builds/perl-module-install-authortests-0.002.work/`
3. 运行 `perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX` 生成 Makefile
4. 执行 `make` 编译模块
5. 执行 `make test` 运行测试套件
6. 执行 `make install DESTDIR=$TEST_PREFIX` 安装到 staging 目录
7. 执行 `make install` 安装到 `$DEFAULT_PREFIX`（模拟用户部署）
8. 打包预编译包 `perl-module-install-authortests-0.002-ohos-aarch64.tar.gz`

### 关键命令

```bash
cd $BUILD_SRC_DIR
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX
make
make test
make install DESTDIR=$TEST_PREFIX
make install  # 安装到 ~/usr/local
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，无平台适配问题 | 无需特殊处理 |

> 参考perl-dbd-pg编译经验：纯Perl模块不涉及XS/ELF签名/SELinux限制问题，比XS模块更简单。
> perl-dbd-pg遇到的SELinux HMDFS限制（XS模块无法从~/usr/local加载）对本模块不适用，
> 因为 Module::Install::AuthorTests 是纯Perl代码，不包含任何.so二进制文件。

## 源码修改

无。本模块为纯 Perl 代码，在 OpenHarmony 平台上无需任何源码修改即可编译运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | OpenHarmony aarch64 平台预装 |
| Module::Install | 1.21 | 构建系统依赖，已预装 |
| Module::Install::Base | 1.21 | 继承的基类 |
| Carp | (核心模块) | Perl 核心模块 |
| File::Find | (核心模块) | Perl 核心模块，用于 recursive_author_tests |

## 验证结果

### make test 结果
```bash
$ make test
t/basic.t .. ok
All tests successful.
Files=1, Tests=1,  0 wallclock secs (0.04 usr + 0.02 sys + 0.05 cusr + 0.10 csys = 0.21 CPU)
Result: PASS
```

### 模块加载验证
```bash
$ perl -MModule::Install::AuthorTests -e 'print "Version: $Module::Install::AuthorTests::VERSION\n"'
Version: 0.002

$ perl -MModule::Install::AuthorTests -e 'print "Path: $INC{\"Module/Install/AuthorTests.pm\"}\n"'
Path: /storage/Users/currentUser/usr/local/lib/perl5/Module/Install/AuthorTests.pm
```

### 功能验证（完整测试报告见 reports/test-report.md）
- 模块加载: ✅ PASS
- 版本号验证: ✅ PASS (0.002)
- 方法可用性: ✅ PASS (author_tests, recursive_author_tests)
- 实际使用场景: ✅ PASS (创建测试项目验证 author_tests 功能)
- 依赖兼容性: ✅ PASS (Module::Install::Base 1.21, Carp, File::Find)

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-install-authortests-0.002-ohos-aarch64.tar.gz | 11799 bytes | 预编译包 |

### 打包内容
```
lib/perl5/Module/Install/AuthorTests.pm     # 主模块文件
lib/perl5/aarch64-linux/auto/Module/Install/AuthorTests/.packlist  # 安装记录
lib/perl5/aarch64-linux/perllocal.pod       # 本地安装文档
```

## 注意事项

1. **纯 Perl 模块**: 本模块不包含任何 XS/C 代码，不涉及 ELF 签名问题
2. **无 SELinux 限制**: 与 perl-dbd-pg 不同，纯 Perl 模块可从 HMDFS 直接加载，无需安装到系统目录
3. **依赖 Module::Install**: 构建时需要 Module::Install 1.21+，运行时通过 `inc::Module::Install` 自动加载
4. **Perl 版本要求**: 最低需要 Perl 5.005，OpenHarmony 的 Perl 5.42.0 完全满足
5. **作者测试机制**: `author_tests` 命令通过检测 `inc/.author` 目录判断是否为作者模式
6. **打包结构**: 使用 INSTALL_BASE 路径结构，与 cmd-pkgs 公共安装脚本兼容
