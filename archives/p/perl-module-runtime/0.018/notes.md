# perl-module-runtime 0.018 适配笔记

## 编译环境
- 构建系统: makefile (ExtUtils::MakeMaker)
- 编译日期: 2026-06-18
- 编译器: clang/clang++
- Perl 版本: 5.42.0 (aarch64-linux)
- 操作系统: OpenHarmony (aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

Module::Runtime 是一个纯 Perl 模块，不包含 XS/C 代码，编译过程简单直接。

```bash
# 1. 解压源码
cd ~/tmp
tar xzf Module-Runtime-0.018.tar.gz
cd Module-Runtime-0.018

# 2. 生成 Makefile (使用 INSTALL_BASE 指定安装路径)
perl Makefile.PL INSTALL_BASE=$DEFAULT_PREFIX

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
perl Makefile.PL INSTALL_BASE=/storage/Users/currentUser/usr/local
make
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无 | 纯 Perl 模块，不涉及 C 编译 | 无需特殊处理 |

### 与 perl-dbd-pg 编译经验对比

perl-dbd-pg 编译中遇到的关键问题在 perl-module-runtime 中均不存在：

| 问题 | perl-dbd-pg | perl-module-runtime |
|------|-------------|---------------------|
| SELinux HMDFS 限制 | ❌ XS 模块(.so)无法从 HMDFS 加载 | ✅ 不适用（纯 Perl 模块） |
| CRT 文件缺失 | ❌ 需要 `-nostartfiles -nodefaultlibs -lc` | ✅ 不适用（无 C 编译） |
| DBI::DBD 加载失败 | ❌ 需硬编码路径绕过 | ✅ 不适用（无 DBI 依赖） |
| ELF 签名 | ❌ .so 需签名才能执行 | ✅ 不适用（无二进制产物） |

**结论**: perl-module-runtime 作为纯 Perl 模块，无需任何平台适配修改，开箱即用。

## 源码修改

无。perl-module-runtime 0.018 为纯 Perl 模块，源码无需任何修改即可在 OpenHarmony 平台编译和运行。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | 系统预装 (HNP) |
| ExtUtils::MakeMaker | 7.76 | Perl 核心模块 |

## 验证结果

```bash
# 模块加载验证
$ perl -MModule::Runtime -e 'print $Module::Runtime::VERSION'
0.018

# 测试套件
$ make test
All tests successful.
Files=11, Tests=365,  2 wallclock secs
Result: PASS

# 功能测试
$ perl -MModule::Runtime=use_module -e 'use_module("Cwd"); print Cwd::getcwd(), "\n"'
/storage/Users/currentUser
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-runtime-0.018-ohos-aarch64.tar.gz | 26KB | 预编译包（含 Runtime.pm + .packlist） |
| Module/Runtime.pm | 18,650 bytes | 主模块文件 |

## 安装路径

- 模块文件: `~/usr/local/lib/perl5/Module/Runtime.pm`
- Packlist: `~/usr/local/lib/perl5/aarch64-linux/auto/Module/Runtime/.packlist`

## 注意事项

1. **纯 Perl 模块**: 不涉及 XS/C 编译，无平台适配问题
2. **taint 模式**: 在 taint 模式下需显式指定 `-I` 路径（Perl 安全特性，非模块缺陷）
3. **无 SELinux 限制**: 与 XS 模块不同，纯 Perl 模块不受 HMDFS SELinux 限制
4. **下游依赖**: Module::Runtime 是许多 Perl 模块的运行时依赖（如 Module::Implementation、Dist::CheckConflicts 等）
---

**编译结束**: 2026-06-23 11:06
**最终状态**: published
