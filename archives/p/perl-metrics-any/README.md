# perl-metrics-any

**Metrics::Any** — Perl 模块，提供监控指标的抽象收集机制。

## 描述

Metrics::Any 为 Perl 模块提供统一的指标收集 API，允许在代码中声明和报告监控指标（counters、gauges、distributions、timers），同时将实际报告机制委托给可配置的适配器。设计灵感来自 Log::Any。

核心特点：
- 模块侧通过 `use Metrics::Any '$metrics'` 获取 collector
- 应用侧通过 `use Metrics::Any::Adapter 'Type'` 配置适配器
- 默认 Null 适配器不做任何事，模块可零依赖使用
- 支持 Counter、Distribution、Gauge、Timer 四种指标类型
- 支持严格模式 (strict) 和懒创建模式

## 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| 0.10-r1 | 2026-06-18 | published | OpenHarmony 平台编译，纯 Perl 模块 |

## 使用示例

```perl
use Metrics::Any '$metrics',
    strict => 0,
    name_prefix => ['my_module'];

# 声明指标
$metrics->make_counter( requests => description => "Total requests" );
$metrics->make_timer( processing_time => description => "Processing time" );

# 报告指标
$metrics->inc_counter( 'requests' );
$metrics->report_timer( 'processing_time', 2.5 );
```

## 构建说明

- 构建系统: Module::Build
- 编译方式: 纯 Perl，无需 C 编译器
- 安装路径: `~/usr/local/lib/site_perl/5.42.0/Metrics/`

## 平台兼容性

- ✅ OpenHarmony (aarch64) — 完全兼容
- 纯 Perl 模块，无 SELinux 限制问题
- 无 XS/C 代码，无需 ELF 签名

## 作者

Paul Evans <leonerd@leonerd.org.uk>
