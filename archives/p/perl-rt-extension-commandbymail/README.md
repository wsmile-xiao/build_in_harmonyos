# perl-rt-extension-commandbymail

RT (Request Tracker) 邮件命令扩展模块（RT::Extension::CommandByMail），允许通过邮件修改工单元数据。

## 软件信息

- **官网**: https://metacpan.org/release/RT-Extension-CommandByMail
- **源码**: https://cpan.metacpan.org/authors/id/B/BP/BPS/RT-Extension-CommandByMail-3.02.tar.gz
- **许可证**: GPL-2.0-or-later
- **分类**: perl-module

## 已编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 3.02 | published | 2026-06-29 | 纯 Perl 模块，补丁替换 Makefile.PL 为标准 EUMM。Conan 验证全部通过 |

## 运行依赖

- RT (Request Tracker) 4.4+
- Email::Address
- Role::Basic

## 编译依赖

无额外依赖（纯 Perl 模块）

## 使用说明

RT::Extension::CommandByMail 允许用户通过发送包含特殊命令的邮件来修改 RT 工单的元数据，
包括队列、状态、优先级、负责人、观察者等属性。

### 安装

通过 Conan 安装：

```bash
conan install --requires=perl-rt-extension-commandbymail/3.02
```

模块安装到 `lib/perl5/RT/` 目录下，通过 `PERL5LIB` 环境变量自动加载。

### 模块文件

| 文件 | 说明 |
|------|------|
| RT/Extension/CommandByMail.pm | 核心模块 — 邮件命令解析与执行 |
| RT/Extension/CommandByMail/Test.pm | 测试辅助模块 |
| RT/Interface/Email/Action/CommandByMail.pm | 邮件动作处理接口 |
| RT/Interface/Email/Filter/TakeAction.pm | 邮件过滤器 — 执行邮件中的命令 |

### 邮件命令示例

在发送给 RT 的邮件正文中添加以下格式的命令：

```
Subject: Re: [RT #1234] Problem report

Queue: customer-service
Status: open
Priority: 3
Owner: jsmith
Requestor: newuser@example.com
```

支持的命令包括：
- **常规属性**: Queue, Owner, Subject, Status, Priority, FinalPriority
- **时间属性**: TimeWorked, TimeLeft, TimeEstimated
- **日期属性**: Due, Starts, Started, Resolved, Told
- **链接属性**: MemberOf, Parents, Members, Children, RefersTo, DependsOn 等
- **观察者属性**: Requestor, Cc, AdminCc

### 注意事项

- 此模块为纯 Perl 实现，不包含 XS 代码，无需 ELF 签名
- 运行时需要 RT (Request Tracker) 4.4+ 环境
- 无平台特殊限制，可在鸿蒙系统正常使用
- 编译时通过补丁将 Makefile.PL 从 Module::Install 替换为标准 EUMM，绕过 RT configure 时依赖

---
*OpenHarmony 编译归档 · 2026-06-29*
