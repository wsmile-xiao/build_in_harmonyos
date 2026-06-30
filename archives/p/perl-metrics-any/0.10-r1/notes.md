# perl-metrics-any 0.10-r1 适配笔记

## 编译环境
- 构建系统: Module::Build (Perl 纯模块构建系统)
- 编译日期: 2026-06-18
- 编译器: 无需 (纯 Perl 模块)
- Perl 版本: 5.42.0 (aarch64-linux)
- 状态: published

## 软件概述

Metrics::Any 是一个 Perl 模块，提供监控指标的抽象收集机制。它允许模块作者在代码中声明和报告监控指标 (counters, gauges, distributions, timers)，同时将实际的报告机制委托给可配置的适配器 (adapter)。设计灵感来自 Log::Any 模块。

### 包含的模块

| 模块 | 说明 |
|------|------|
| Metrics::Any | 主模块，提供 import 语法 |
| Metrics::Any::Collector | 收集器，提供 make_*/inc_*/report_* API |
| Metrics::Any::Adapter | 适配器基类 |
| Metrics::Any::Adapter::Null | 空适配器 (默认，不报告) |
| Metrics::Any::Adapter::Stderr | 标准错误输出适配器 |
| Metrics::Any::Adapter::File | 文件输出适配器 |
| Metrics::Any::Adapter::Tee | 多路输出适配器 |
| Metrics::Any::Adapter::Test | 测试用适配器 (捕获指标) |
| Metrics::Any::AdapterBase::Stored | 存储适配器基类 |

## 编译步骤

### 1. 下载和解压

源码来自本地打包的 no-ssl 版本 (已去除 SSL 相关测试)：

```bash
# 源码已存在于 ~/tmp/builds/perl-metrics-any-0.10-r1.work/
```

### 2. 构建

```bash
cd ~/tmp/builds/perl-metrics-any-0.10-r1.work
perl Build.PL --prefix ~/usr/local    # 生成 Build 脚本
./Build                                # 构建 (纯 Perl，无编译)
```

### 3. 测试

```bash
./Build test
# 结果: 14 个测试文件, 83 个测试全部通过
```

### 4. 安装

```bash
./Build install --prefix ~/usr/local
# 安装到 ~/usr/local/lib/site_perl/5.42.0/Metrics/
```

### 5. 验证

```bash
perl -MMetrics::Any -e 'print $Metrics::Any::VERSION'
# 输出: 0.10
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Quality Report G4 FAIL | manifest.yaml 缺少 build_system 字段，notes.md 为模板 | 填充 manifest 和 notes |
| 2 | 模块未安装到本地 | 编译后未执行 install 步骤 | 执行 `./Build install --prefix ~/usr/local` |
| 3 | 99pod.t 被 skip | Test::Pod 模块未安装 | 非阻塞，仅影响 POD 格式检查 |

**与 perl-dbd-pg 编译经验的对比**：

perl-dbd-pg 是 XS 模块 (含 C 代码)，编译时遇到：
- SELinux HMDFS 限制导致 DBI::DBD 加载失败 → 硬编码路径
- CRT 文件缺失 → 使用 `-nostartfiles -nodefaultlibs -lc` 链接参数
- XS 模块运行时加载限制 → 需要 HNP 包安装到系统目录

而 Metrics::Any 是纯 Perl 模块，**不涉及以上任何问题**，编译和运行完全兼容。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Perl | 5.42.0 | OpenHarmony 预装 |
| Module::Build | 0.4231 | 构建工具 |
| List::Util | ≥1.29 | Perl 核心模块 (5.20+ 内置) |

## 验证结果

```bash
$ perl -MMetrics::Any -e 'print $Metrics::Any::VERSION'
0.10

$ cd ~/tmp/builds/perl-metrics-any-0.10-r1.work && perl Build test
All tests successful. Files=14, Tests=83, Result: PASS

$ perl ~/tmp/test_metrics_any.pl  # 16 项功能测试
测试汇总: PASS=16, FAIL=0
结论: ✅ 全部通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| perl-metrics-any-0.10-r1-ohos-aarch64.tar.gz | 60KB | 预编译包 (含全部 .pm 文件) |

## 安装文件路径

安装到: `~/usr/local/lib/site_perl/5.42.0/Metrics/`

```
Metrics/Any.pm
Metrics/Any/Collector.pm
Metrics/Any/Adapter.pm
Metrics/Any/Adapter/File.pm
Metrics/Any/Adapter/Null.pm
Metrics/Any/Adapter/Stderr.pm
Metrics/Any/Adapter/Tee.pm
Metrics/Any/Adapter/Test.pm
Metrics/Any/AdapterBase/Stored.pm
```

## 注意事项

1. **纯 Perl 模块**: 无需 C 编译器或 XS 支持，可直接安装使用
2. **Test::Pod 缺失**: 99pod.t 测试被跳过，不影响功能。如需完整测试可安装 Test::Pod
3. **SSL 相关**: 使用 no-ssl 版本源码，已去除 SSL 相关的测试用例
4. **安装路径**: 使用 `--prefix ~/usr/local` 确保模块安装到用户可访问的 site_perl 目录

---

**编译结束**: 2026-06-18
**最终状态**: published
