# Log::Log4perl

Log4j implementation for Perl - 鸿蒙平台预编译包

## 软件介绍

Log::Log4perl 是 Perl 的日志库，实现了 Apache Log4j API。它提供了灵活的日志配置和管理功能。

### 主要特性
- 多级日志输出（DEBUG, INFO, WARN, ERROR, FATAL）
- 多种输出方式（文件、屏幕、syslog、数据库）
- 配置文件和代码配置支持
- 日志过滤和格式化

### 技术信息
- **版本**: 1.57
- **许可证**: Perl Artistic License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: 纯 Perl 模块（无 XS）

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-15（依赖完善: 2026-06-17）
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **Perl 版本**: 5.42.0
- **状态**: ✅ 编译成功，依赖已完善

### 平台适配说明
- 纯 Perl 模块，无需平台相关补丁
- 核心依赖（File::Spec, File::Path）是 Perl 核心模块
- 跨平台兼容，无需特殊处理
- **DBI PurePerl 适配**: DBI.so 无法在鸿蒙平台通过 ELF 签名，已 patch DBI.pm 使用 PurePerl fallback
- **DBD::CSV**: 通过 DBI PurePerl 模式可用，CRUD 操作全部正常
- **Log::Dispatch::FileRotate**: 已安装 Date::Manip 6.96，日志轮转功能可用
- **XML::Parser/XML::DOM**: 平台限制不可用（dlopen 拒绝加载本地编译的 .so）

### 质量门禁
| 门禁 | 状态 | 说明 |
|------|------|------|
| G1 二进制完整性 | PASS | 纯 Perl 模块，无二进制 |
| G2 功能可用性 | PASS | 核心功能可用 |
| G3 可移植性 | PASS | 无 RPATH 问题 |
| G4 档案完整性 | PASS | 归档文件完整 |

## 安装

### 预编译包安装
```bash
# 使用 cmd-pkgs 安装脚本
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- Log-Log4perl 1.57
```

### 手动安装
```bash
# 解压预编译包
tar xzf Log-Log4perl-1.57-ohos-aarch64.tar.gz -C ~/usr/local

# 验证安装
perl -MLog::Log4perl -e 'print $Log::Log4perl::VERSION'
```

## 使用示例

### 基础使用
```perl
use Log::Log4perl;

# 简单配置
Log::Log4perl->easy_init($ERROR);

# 获取 logger
my $logger = Log::Log4perl->get_logger();

# 日志输出
$logger->debug("Debug message");
$logger->info("Info message");
$logger->warn("Warning message");
$logger->error("Error message");
$logger->fatal("Fatal message");
```

### 配置文件方式
```perl
use Log::Log4perl;

# 配置文件
my $conf = q(
log4perl.rootLogger=INFO, Screen, File

log4perl.appender.Screen=Log::Log4perl::Appender::Screen
log4perl.appender.Screen.stderr=1
log4perl.appender.Screen.layout=PatternLayout
log4perl.appender.Screen.layout.ConversionPattern=%d %p %m %n

log4perl.appender.File=Log::Log4perl::Appender::File
log4perl.appender.File.filename=/var/log/app.log
log4perl.appender.File.layout=PatternLayout
log4perl.appender.File.layout.ConversionPattern=%d %p %m %n
);

Log::Log4perl->init(\$conf);

my $logger = Log::Log4perl->get_logger();
$logger->info("Application started");
```

## 依赖关系

### 核心依赖（已内置）
- File::Spec >= 0.82（Perl 核心模块）
- File::Path >= 2.07（Perl 核心模块）

### 推荐依赖状态（更新于 2026-06-17）

| 依赖模块 | 版本要求 | 当前状态 | 版本 | 功能 | 备注 |
|---------|---------|---------|------|------|------|
| Log::Dispatch | >= 2.00 | ✅ published | 2.71 | 增强输出器支持 | 纯 Perl，直接可用 |
| DBI | >= 1.607 | ✅ PurePerl | 1.637 | 数据库接口 | DBI.so 无法签名，已 patch DBI.pm 使用 PurePerl fallback |
| DBD::SQLite | - | ✅ published | - | SQLite 日志存储 | 已编译可用 |
| SQL::Statement | >= 1.20 | ✅ published | 1.414 | SQL 解析引擎 | Clone::PP wrapper 解决 XS 问题 |
| DBD::CSV | >= 0.33 | ✅ 可用 | 0.62 | CSV 日志存储 | 通过 DBI PurePerl 模式，7/7 功能测试通过 |
| Text::CSV | - | ✅ 可用 | 2.06 | CSV 解析 | 纯 Perl 模块 |
| Log::Dispatch::FileRotate | >= 1.10 | ✅ 可用 | 1.38 | 日志文件轮转 | 需 Date::Manip 6.96（已安装） |
| Date::Manip | - | ✅ 已安装 | 6.96 | 日期处理 | 纯 Perl，Log::Dispatch::FileRotate 依赖 |
| XML::RegExp | - | ✅ published | - | XML 正则表达式 | 纯 Perl |
| XML::DOM | >= 1.29 | ❌ 不可用 | - | XML 配置支持 | 依赖 XML::Parser，平台限制无法加载 |
| XML::Parser | >= 2.30 | ❌ 不可用 | 2.47 | XML 解析器 | 已编译但 dlopen() 拒绝加载本地编译的 .so（平台限制） |

### 平台限制说明

**XML::Parser/XS 模块限制**：
- 鸿蒙平台 dlopen() 拒绝加载所有本地编译的共享库（.so），即使已通过 binary-sign-tool 签名
- 这影响所有依赖 XS 共享库的 Perl 模块
- XML::Parser 2.47 已成功编译（Expat.so 生成），但运行时无法加载
- 建议：如需 XML 配置支持，考虑使用纯 Perl 的 XML 解析方案（如 XML::SAX::PurePerl）

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 1.57 | published | 2026-06-17 |

## 相关链接
- 官方仓库：https://github.com/mschilli/log4perl
- CPAN：https://metacpan.org/pod/Log::Log4perl
- 文档：https://log4perl.sourceforge.net/