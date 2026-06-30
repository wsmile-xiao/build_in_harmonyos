# perl-module-refresh 0.18 适配笔记

## 编译环境
- 构建系统: perl (ExtUtils::MakeMaker via Module::Install)
- 编译日期: 2026-06-18
- 编译器: N/A（纯 Perl 模块，无 C/XS 编译）
- Perl 版本: 5.42.0 (aarch64-linux)
- 平台: OpenHarmony / HarmonyOS, HongMeng Kernel 1.12.0, aarch64
- 状态: published

## 编译步骤

perl-module-refresh 是纯 Perl 模块（Module::Refresh），无需 C/XS 编译。

```bash
# 1. 下载并解压源码
tar xzf Module-Refresh-0.18.tar.gz

# 2. 生成 Makefile（perl Makefile.PL）
cd Module-Refresh-0.18
perl Makefile.PL PREFIX=~/usr/local

# 3. 编译（无 C 代码，仅处理 .pm 文件）
make

# 4. 安装到 staging 目录
make install DESTDIR=~/tmp/test-install-perl-module-refresh-0.18

# 5. 运行测试
make test

# 6. 安装到本地（模拟用户部署）
make install

# 7. 验证
perl -MModule::Refresh -e 'print $Module::Refresh::VERSION'
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Path::Class 测试依赖缺失 | 测试套件 t/clear_symtable.t 依赖 Path::Class | 通过 CPAN 安装 Path::Class |
| 2 | 无 | 纯 Perl 模块，无需源码修改 | N/A |

**与 perl-dbd-pg 的对比**：
- perl-dbd-pg 遇到 SELinux HMDFS 限制（XS 模块无法从 ~/usr/local/lib 加载），需要 HNP 包安装
- perl-module-refresh 是纯 Perl 模块，**不受 SELinux 限制**，可直接从用户目录加载
- perl-dbd-pg 需要补丁处理 CRT 文件缺失和 DBI::DBD 加载问题
- perl-module-refresh **无需任何补丁**，开箱即用

## 源码修改

无。模块为纯 Perl 实现，无需任何源码修改即可在 OpenHarmony 平台编译运行。
- `.edit-tracker.json` 确认: `edited: []`, `added: []`
- 无补丁文件

## 依赖版本

| 依赖 | 版本 | 类型 |
|------|------|------|
| Perl | 5.42.0 | 运行时 |
| ExtUtils::MakeMaker | 7.76 | 构建时 |
| Path::Class | (CPAN最新) | 测试时 |
| File::Temp | 0.19+ | 测试时 |
| Test::More | (核心模块) | 测试时 |

## 验证结果

```bash
# 模块加载
$ perl -MModule::Refresh -e 'print $Module::Refresh::VERSION'
0.18

# 安装路径
$ perl -MModule::Refresh -e 'print $INC{q(Module/Refresh.pm)}'
/storage/Users/currentUser/usr/local/lib/site_perl/5.42.0/Module/Refresh.pm

# 测试套件
$ make test
Files=4, Tests=16, 3 wallclock secs
Result: PASS

# API 方法检查
$ perl -MModule::Refresh -e '... (检查8个API方法)'
All 8 methods: OK

# 核心功能验证
$ perl -MModule::Refresh -e '... (模块刷新测试)'
refresh_module: v1 -> v2: PASS
refresh(): v2 -> v3: PASS
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-module-refresh-0.18-ohos-aarch64.tar.gz | 14,871 bytes | 预编译包 |

## 注意事项

1. **纯 Perl 模块**：无 C/XS 代码，不受 SELinux HMDFS 限制，可直接从用户目录加载
2. **Perl 编译器缓存行为**：直接函数调用（`Foo::bar()`）在编译时缓存，refresh 后仍返回旧值；方法调用（`$obj->bar()`）能正确看到刷新后的值。这是 Perl 的预期行为，非平台问题
3. **mtime 检测正常**：HMDFS 文件系统的 stat() 返回正确的 mtime，Module::Refresh 的文件变更检测功能正常工作
4. **$^P 调试标志**：模块使用 `$^P |= 0x10` 启用 `%DB::sub` 符号表追踪，在 Perl 5.42 上正常工作
---

**编译结束**: 2026-06-23
**最终状态**: published
