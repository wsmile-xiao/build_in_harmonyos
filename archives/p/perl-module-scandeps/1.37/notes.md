# perl-module-scandeps 1.37 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker)
- 编译日期: 2026-06-18
- 编译器: clang/clang++（纯 Perl 模块，实际不使用 C 编译器）
- Perl 版本: 5.42.0 (aarch64-linux)
- 操作系统: OpenHarmony (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

Module::ScanDeps 是一个纯 Perl 模块，不包含 XS/C 代码，编译过程简单直接。

```bash
# 1. 解压源码
cd ~/tmp
tar xzf Module-ScanDeps-1.37.tar.gz
cd Module-ScanDeps-1.37

# 2. 生成 Makefile (使用 PREFIX 和 INSTALLDIRS 指定安装路径)
perl Makefile.PL PREFIX=$DEFAULT_PREFIX INSTALLDIRS=site

# 3. 编译
make

# 4. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX

# 5. 安装到本地 (模拟用户部署)
make install

# 6. 运行测试套件
make test
```

### 关键编译命令

```bash
perl Makefile.PL PREFIX=/storage/Users/currentUser/usr/local INSTALLDIRS=site
make
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，不涉及 C 编译 | 无需特殊处理 |

### 与 perl-dbd-pg 编译经验对比

perl-dbd-pg 编译中遇到的关键问题在 perl-module-scandeps 中均不存在：

| 问题 | perl-dbd-pg | perl-module-scandeps |
|------|-------------|---------------------|
| SELinux HMDFS 限制 | ❌ XS 模块(.so)无法从 HMDFS 加载 | ✅ 不适用（纯 Perl 模块） |
| CRT 文件缺失 | ❌ 需要 `-nostartfiles -nodefaultlibs -lc` | ✅ 不适用（无 C 编译） |
| DBI::DBD 加载失败 | ❌ 需硬编码路径绕过 | ✅ 不适用（无 DBI 依赖） |
| ELF 签名 | ❌ .so 需签名才能执行 | ✅ 不适用（无二进制产物） |
| pg_config 包装器 | ❌ 需创建包装器脚本 | ✅ 不适用（无外部依赖） |

**结论**: perl-module-scandeps 作为纯 Perl 模块，无需任何平台适配修改，开箱即用。

## 源码修改

无。perl-module-scandeps 1.37 为纯 Perl 模块，源码无需任何修改即可在 OpenHarmony 平台编译和运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 系统预装 (HNP) |
| ExtUtils::MakeMaker | 7.76 | Perl 核心模块 |

## 验证结果

```bash
# 模块加载验证
$ perl -MModule::ScanDeps -e 'print $Module::ScanDeps::VERSION'
1.37

# Cache 子模块加载
$ perl -MModule::ScanDeps::Cache -e 'print "OK"'
OK

# 测试套件
$ make test
All tests successful.
Files=21, Tests=201, 16 wallclock secs
Result: PASS

# 功能测试 - scan_deps 扫描依赖
$ perl -MModule::ScanDeps=scan_deps -e '...'
Total dependencies found: 38
Modules: 29, Shared (XS): 6

# scandeps.pl 命令行工具
$ scandeps.pl -B test_scan.pl
# 正确输出所有核心模块及其版本号

# scandeps.pl 非核心模块扫描
$ scandeps.pl test_noncore.pl
'Module::ScanDeps' => '1.37',
'Module::Metadata' => '1.000038',
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-scandeps-1.37-ohos-aarch64.tar.gz | 83KB | 预编译包（含 ScanDeps.pm, Cache.pm, scandeps.pl） |
| Module/ScanDeps.pm | 61,607 bytes | 主模块文件 |
| Module/ScanDeps/Cache.pm | 2,495 bytes | 缓存模块文件 |
| bin/scandeps.pl | 6,681 bytes | 命令行工具 |

## 安装路径

- 模块文件: `~/usr/local/lib/site_perl/5.42.0/Module/ScanDeps.pm`
- 缓存模块: `~/usr/local/lib/site_perl/5.42.0/Module/ScanDeps/Cache.pm`
- 命令行工具: `~/usr/local/bin/scandeps.pl`
- Packlist: `~/usr/local/lib/site_perl/5.42.0/aarch64-linux/auto/Module/ScanDeps/.packlist`

## 注意事项

1. **纯 Perl 模块**: 不涉及 XS/C 编译，无平台适配问题
2. **无 SELinux 限制**: 与 XS 模块不同，纯 Perl 模块不受 HMDFS SELinux 限制
3. **OO 接口**: `new()` 方法需传入 hashref（`Module::ScanDeps->new({recurse => 1})`），不接受 key-value 参数（上游 API 设计）
4. **scandeps.pl 默认行为**: 不带 `-B` 选项时只报告非核心模块，使用 `-B` 可列出全部依赖
5. **XS 检测能力**: 虽然本模块为纯 Perl，但能正确检测系统 XS 模块（.so）的依赖关系
6. **下游依赖**: Module::ScanDeps 是 PAR::Packer (pp 命令) 和 Module::Install 的核心依赖
---

**编译结束**: 2026-06-23
**最终状态**: published
