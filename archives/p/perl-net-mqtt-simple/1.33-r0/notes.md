# perl-net-mqtt-simple 1.33-r0 适配笔记

## 编译环境
- 构建系统: Makefile.PL (ExtUtils::MakeMaker)
- 编译日期: 2026-06-26
- 编译器: clang/clang++
- Perl 版本: 5.42.0 (aarch64-linux, OpenHarmony 平台)
- 状态: built (conan-verify 全部通过)

## 软件描述

Net::MQTT::Simple 是一个纯 Perl 实现的 MQTT v3.1.1 客户端模块，提供最小化的
MQTT 协议接口。支持 publish/subscribe、QoS 0、Last Will、retain 消息等功能。
无需 XS 编译，不依赖 C 库，适合在资源受限的环境中使用。

## 编译步骤

```bash
# 1. 下载源码
wget https://cpan.metacpan.org/authors/id/J/JU/JUERD/Net-MQTT-Simple-1.33.tar.gz

# 2. 解压
tar xzf Net-MQTT-Simple-1.33.tar.gz
cd Net-MQTT-Simple-1.33

# 3. 生成 Makefile
perl Makefile.PL

# 4. 编译
make

# 5. 安装到 staging 目录
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 无编译问题 | 纯 Perl 模块，无 C/XS 代码 | 无需修改，直接 perl Makefile.PL && make |
| 2 | SSL 子模块加载失败 | IO::Socket::SSL 未安装 | SSL 是可选功能，不影响核心模块使用 |
| 3 | 无 SELinux/HMDFS 限制问题 | 纯 Perl 模块不加载 .so 文件 | 与 perl-dbd-pg 不同，无需处理 SELinux 限制 |

## 与 perl-dbd-pg 编译经验对比

| 对比项 | perl-dbd-pg | perl-net-mqtt-simple |
|--------|-------------|----------------------|
| 模块类型 | XS (C 扩展) | 纯 Perl |
| 构建系统 | Makefile.PL + XS | Makefile.PL |
| SELinux 限制 | 有 (HMDFS 无法加载 .so) | 无 (不加载 .so) |
| CRT 链接问题 | 有 (缺少 crti.o 等) | 无 (无 C 代码) |
| 补丁需求 | 需要 2 个补丁 | 不需要补丁 |
| 运行时依赖 | PostgreSQL libpq | 无外部依赖 |
| 功能可用性 | 需管理员安装 XS 模块 | 直接可用 |

## 源码修改

无。本软件为纯 Perl 模块，无需任何源码修改即可在鸿蒙平台编译和运行。

## 依赖版本

- Perl: 5.42.0 (系统预装, /data/service/hnp/perl.org/perl_5.42.0)
- ExtUtils::MakeMaker: 7.70 (Perl 自带)
- IO::Socket::IP: Perl 核心模块 (用于 TCP 连接)
- IO::Socket::SSL: 未安装 (SSL 子模块的可选依赖)

## 验证结果

### Conan 验证 (conan-verify)
```
G0: PASS (构建系统识别)
G1: PASS (配方完整性)
G2: PASS (conan create 成功)
G3: PASS (系统同名库隔离)
G4: PASS (产物完整性: 2 .pm 文件)
L2: PASS (纯库包，跳过 smoke test)
L4: PASS (无 ELF 文件)
L5: PASS (产物基线一致)
```

### 源码测试套件
```
t/regex.t .. ok
t/use.t .... ok
All tests successful.
Files=2, Tests=561, 0 wallclock secs
Result: PASS
```

### 功能测试
```
15/15 测试通过
- 模块加载、构造器、发布、订阅、通配符订阅
- filter_as_regex 主题匹配、保留消息、Last Will
- 大消息传输 (10KB)、二进制消息 (10KB)
- 取消订阅、SSL 依赖检查、断开连接
- CLI 工具、源码测试套件
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/Net/MQTT/Simple.pm | 24,823 bytes | 主模块 |
| lib/Net/MQTT/Simple/SSL.pm | 4,341 bytes | SSL 子模块 (可选) |

## 注意事项

1. **SSL 功能**: SSL 子模块 (Net::MQTT::Simple::SSL) 依赖 IO::Socket::SSL，
   当前平台未安装此模块。如需 SSL/TLS 支持，需先安装 IO::Socket::SSL。
2. **MQTT Broker**: 本模块是 MQTT 客户端，需要连接外部 MQTT broker 才能使用
   publish/subscribe 功能。功能测试中使用了内置的简易 broker。
3. **纯 Perl 优势**: 与 perl-dbd-pg 等 XS 模块不同，本模块不受 SELinux HMDFS
   限制影响，可直接在用户空间使用，无需管理员安装。
4. **版本号说明**: 版本号 1.33-r0 中的 -r0 表示 OpenHarmony 适配修订号 0
   (首次适配，无修订)。

---

**编译结束**: 2026-06-26 18:09
**最终状态**: built (conan-verify 全部通过，功能测试 15/15 通过)
