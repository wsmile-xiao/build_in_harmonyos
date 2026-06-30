# perl-probe-perl

**Probe::Perl** — 获取当前运行 Perl 解释器信息的工具模块

## 基本信息

| 项 | 值 |
|------|------|
| 软件名 | perl-probe-perl |
| 版本 | 0.03 |
| 许可证 | perl_5 |
| 主页 | https://metacpan.org/release/Probe-Perl |
| 构建系统 | ExtUtils::MakeMaker (perl-eumm) |
| 平台 | OpenHarmony (aarch64) |
| 状态 | ✅ published |

## 描述

Probe::Perl 提供了一系列方法用于获取当前运行的 Perl 解释器信息，包括：

- **config()** — 访问 Config.pm 配置值
- **find_perl_interpreter()** — 查找当前 Perl 解释器的绝对路径
- **perl_version()** — 获取 Perl 版本号（浮点格式）
- **perl_version_to_float()** — 将多段版本号转换为浮点数
- **perl_is_same()** — 判断指定 Perl 是否与当前相同
- **perl_inc()** — 获取 Perl 默认 @INC 路径列表
- **os_type()** — 获取操作系统通用类型

## 依赖

| 依赖 | 最低版本 | 实际版本 |
|------|---------|---------|
| Config | any (Perl核心模块) | 5.42.0 |
| File::Spec | any (Perl核心模块) | 3.75 |
| perl | 5.006 | 5.42.0 |

## 版本索引

| 版本 | 状态 | 日期 |
|------|------|------|
| 0.03 | published | 2026-06-26 |
