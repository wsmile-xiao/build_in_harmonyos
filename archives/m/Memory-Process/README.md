# Memory::Process

## 简介

Memory::Process 是一个 Perl 模块，用于监控和报告进程的内存使用情况。它继承自 Memory::Usage，提供了简化的内存报告功能（仅输出首行和末两行数据，而非全部历史记录）。

- **CPAN**: https://metacpan.org/pod/Memory::Process
- **GitHub**: https://github.com/michal-josef-spacek/Memory-Process
- **许可证**: BSD-2-Clause

## OHOS 适配

### 模块类型
- ✅ **纯 Perl 模块**（无 XS/C 代码）
- ✅ **无需 ELF 签名**
- ✅ **无 SELinux HMDFS 限制**（不涉及 .so 加载）
- ✅ **用户级安装**（无需管理员权限）

### 平台兼容性
- ✅ OpenHarmony (Linux 内核，/proc 文件系统可用)
- ❌ FreeBSD, Windows, OpenBSD, Solaris, Darwin (不支持)

### 安装方式
```bash
# 手动安装（cpan install 到系统目录会失败）
PREFIX=~/usr/local/lib/site_perl/5.42.0
mkdir -p "$PREFIX/Memory"
cp Process.pm "$PREFIX/Memory/"
```

### 依赖模块
同样需手动安装到 `~/usr/local/lib/site_perl/5.42.0/`：
- **Memory::Usage** 0.201 (必需 - 基类)
- **Readonly** 2.05 (必需 - 常量定义)
- **Test::NoWarnings** 1.04 (仅测试用)
- **Capture::Tiny** (仅测试用)

## 功能验证

```perl
use Memory::Process;

my $m = Memory::Process->new;
$m->record("Before my big method");
# ... 执行一些操作 ...
$m->record("After my big method");
print $m->report;
```

输出示例：
```
  time    vsz (  diff)    rss (  diff) shared (  diff)   code (  diff)   data (  diff)
     0  2133008 ( 2133008)   9492 (  9492)   7528 (  7528)   1500 (  1500)  19588 ( 19588) Before my big method
     1  2133008 (     0)   9492 (     0)   7528 (     0)   1500 (     0)  19588 (     0) After my big method
```

## 测试结果
- **单元测试**: 8/8 文件, 27/27 用例全部通过
- **功能测试**: 12/12 全部通过
- **状态**: ✅ 完全可用

## 已知限制
1. `module-size` 脚本需通过 `perl` 调用（直接执行报 Permission denied）
2. cpan install 到系统目录失败（只读），需手动安装 .pm 文件
3. 仅支持 Linux/OHOS 平台

## 版本索引
- 0.06-r3: ✅ published (2026-06-17)
