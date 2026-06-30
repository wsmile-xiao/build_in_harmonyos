# Crypt::OpenSSL::Random

OpenSSL 随机数生成器接口 - 鸿蒙平台编译

## 软件介绍

Crypt::OpenSSL::Random 提供 OpenSSL 随机数生成器的 Perl 接口。

### 主要特性
- 随机字节生成 (random_bytes)
- 伪随机字节生成 (random_pseudo_bytes)
- 随机数种子 (random_seed)
- PRNG 状态检查 (random_status)

### 技术信息
- **最新版本**: 0.15
- **可用版本**: 0.11, 0.15
- **许可证**: Perl Artistic License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: XS 模块 (需要 C 编译)

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-16
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **OpenSSL**: 1.1.1w
- **状态**: ✅ 编译成功，⚠️ XS模块需HNP安装

### XS 编译要点
- **链接参数**: `-nostartfiles -nodefaultlibs -lc` (绕过CRT缺失)
- **OpenSSL路径**: 显式指定 LIBS/INC

### SELinux 限制
XS 模块在 HMDFS 目录无法加载，需要管理员安装到 `/data/service/hnp`。

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.11 | built | 2026-06-16 |

## 相关模块

- **Crypt::OpenSSL::Guess**: OpenSSL 路径检测 (纯Perl)
- **Crypt::OpenSSL::RSA**: OpenSSL RSA 加密 (XS)nSSL 路径检测 (纯Perl)
- **Crypt::OpenSSL::RSA**: OpenSSL RSA 加密 (XS)