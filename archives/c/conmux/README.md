# conmux

Console Multiplexor - 串口/控制台复用器（纯 Perl 应用，IBM autotest 项目 conmux 子目录）

## 描述

CONMUX 是控制台抽象层（Console Multiplexor）：为任意控制台提供统一的位置、
命名与语义。无论底层访问方式如何，对控制台的访问与硬复位操作保持一致。
核心组件：conmux（守护进程）、conmux-registry（注册表服务）、conmux-attach
（客户端）、console（交互客户端）。

## 特性

- 纯 Perl 实现，无 XS/无 C/C++ 编译
- 统一控制台抽象：socket / application / command 三种会话类型
- registry 注册表服务：ADD / LOOKUP / LIST 协议
- 多路复用（IO::Multiplex 事件循环）
- 驱动扩展：blade / dli-lpc / hmc / ivm / reboot-* / zseries 等

## 编译状态

| 版本 | 状态 | 编译日期 | 测试结果 | 预编译包 | 说明 |
|------|------|---------|---------|---------|------|
| 0.12.0 | built | 2026-09-10 | ✅ PASS (8/8 自研) | ✅ | 纯 Perl 应用，质量门禁通过 |

### 测试详情

- **上游测试套件**: 无（R51 穷尽核查——上游确无自带测试）
- **test_package 自研断言**: 8
- **通过数**: 8
- **失败数**: 0
- **覆盖**: 脚本 usage / Conmux.pm 加载 / conmux-registry 真实协议（ADD/LOOKUP/LIST）

### 质量门禁

- ✅ G1: 配方完整性
- ✅ G2: conan create（含 test_package 真实功能验证）
- ✅ G3: 系统同名库隔离
- ✅ G4: 产物完整性

## 依赖

- Perl 5.42.0+
- perl-io-multiplex/1.16（IO::Multiplex）
- perl-uri/5.35（URI::Escape）
- Perl 核心模块（IO::Socket / IPC::Open3 / POSIX 等）

## 适配要点（OHOS）

- **E049 shebang**：脚本 `#!/usr/bin/perl` 硬编码，设备 perl 在
  `/data/service/hnp/bin/perl`——package() 统一修正为 `#!/usr/bin/env perl`
- 源码为 autotest 官方仓库 conmux 子目录，conandata 指向官方 tarball + 固定 sha256
- 构建为纯拷贝安装（`make install BUILD=<staging>`，无编译目标）

## 安装

```bash
# conan 安装后，脚本位于 <pkg>/usr/local/conmux/{bin,sbin}
export PERL5LIB=<site_perl 目录>

# 使用
conmux <config file>
conmux-registry <local port> <store>
console <service>
```

## 相关链接

- 上游: https://github.com/autotest/autotest/tree/master/conmux
- 作者: Andy Whitcroft (IBM) 等
