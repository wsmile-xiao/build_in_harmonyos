# perl-mojolicious 9.42 适配笔记

## 编译环境
- 构建系统: Perl Makefile.PL (ExtUtils::MakeMaker 7.76)
- 编译日期: 2026-06-23
- 编译器: clang/clang++
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 编译步骤

```bash
# 1. 解压源码
cd ~/tmp/builds/perl-mojolicious-9.42.work

# 2. 配置 (Perl 模块使用 Makefile.PL)
perl Makefile.PL PREFIX=~/usr/local

# 3. 编译
make -j1

# 4. 安装到 staging (DESTDIR 模式)
make install DESTDIR=~/tmp/test-install-perl-mojolicious-9.42

# 5. 安装到本地 (模拟用户部署)
make install

# 6. 运行测试
PERL_DL_NONLAZY=1 HARNESS_OPTIONS=j1 perl -Iblib/lib -Iblib/arch -MTest::Harness -e 'runtests(@ARGV)' t/*.t t/*/*.t
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Can't set $0 with prctl(): Invalid argument` 导致 4 个测试文件崩溃 | OpenHarmony 内核不完全支持 `prctl(PR_SET_NAME)` 系统调用，Perl `$0` 赋值触发该调用并返回 EINVAL | 用 `eval { }` 包裹 `$0` 赋值，`local $SIG{__WARN__}` 抑制警告，手动 save/restore 替代 `local $0` |
| 2 | `local $0;` 本身也会触发 prctl 调用 | `local $0` 隐式将 `$0` 赋值为 undef，触发 set magic 和 prctl | 完全避免对 `$0` 使用 `local`，改用 `my $saved_0 = $0;` 手动保存 |
| 3 | clean-verify.py 脚本不支持 Perl 模块 | 脚本默认使用 `/bin/sh ./configure`，未检测 `Makefile.PL` | 手动验证补丁自包含性（通过） |

## 源码修改

### 补丁 1: `0001-lib-Mojo-Server.pm.patch`
- **文件**: `lib/Mojo/Server.pm`
- **函数**: `load_app()`
- **修改**: 将 `local $0 = $path = ...` 改为先提取 `$path`，用 `my $saved_0 = $0` 保存原值，`eval { $0 = $path }` 安全赋值，代码块结束时 `eval { $0 = $saved_0 }` 恢复

### 补丁 2: `0002-lib-Mojo-Server-Hypnotoad.pm.patch`
- **文件**: `lib/Mojo/Server/Hypnotoad.pm`
- **函数**: `run()`
- **修改**: 将 `$0 = $ENV{HYPNOTOAD_APP} ||= ...` 拆分为先设置 ENV，再用 eval 包裹 `$0` 赋值

### 补丁 3: `0003-lib-Mojo-Server-Morbo.pm.patch`
- **文件**: `lib/Mojo/Server/Morbo.pm`
- **函数**: `run()`
- **修改**: 将 `unshift @{$self->backend->watch}, $0 = $app;` 拆分为先 eval 包裹 `$0` 赋值，再单独执行 unshift

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| ExtUtils::MakeMaker | 7.76 | 构建系统 |
| IO::Socket::IP | >= 0.37 | 网络套接字（系统预装） |
| Sub::Util | >= 1.41 | 子程序工具（系统预装） |

## 验证结果

```bash
# 官方测试套件
All tests successful.
Files=109, Tests=4158, 77 wallclock secs
Result: PASS

# 模块加载
perl -MMojolicious -e 'print $Mojolicious::VERSION'  # 9.42

# 命令行工具
mojo version  # Perl (v5.42.0, linux), Mojolicious (9.42, Waffle)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-mojolicious-9.42-ohos-aarch64.tar.gz | 2503KB | 预编译包（112 PM 模块 + 3 脚本） |
| 0001-lib-Mojo-Server.pm.patch | 1402B | prctl 修复补丁 |
| 0002-lib-Mojo-Server-Hypnotoad.pm.patch | 943B | prctl 修复补丁 |
| 0003-lib-Mojo-Server-Morbo.pm.patch | 744B | prctl 修复补丁 |

## 注意事项

1. **prctl 平台限制**: OpenHarmony 不完全支持 `prctl(PR_SET_NAME)`，所有涉及 `$0` 赋值的 Perl 模块都可能遇到此问题。修复模式为 `eval { $0 = $value }` 包裹 + 手动 save/restore。

2. **`local $0` 陷阱**: 不仅 `$0 = $value` 会触发 prctl，`local $0;`（即使不赋值）也会隐式触发。必须完全避免对 `$0` 使用 `local`。

3. **Mojo::Pg 限制**: Mojo::Pg 依赖 DBD::Pg XS 模块，受 SELinux HMDFS 限制无法从用户目录加载。需将 DBD::Pg 安装到系统目录（`/data/service/hnp/`）才能使用。参考 perl-dbd-pg 的安装指南。

4. **G0 验证**: clean-verify.py 脚本不支持 Perl 模块的自动构建验证（默认使用 `./configure`），已通过手动验证确认补丁自包含性。

5. **构建系统标记**: Perl 模块应使用 `makefile` 构建系统标记，configure 命令为 `perl Makefile.PL PREFIX=$DEFAULT_PREFIX`。
---

**编译结束**: 2026-06-23 14:28
**最终状态**: published
