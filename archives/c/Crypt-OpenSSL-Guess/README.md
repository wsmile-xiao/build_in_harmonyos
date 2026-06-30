# Crypt::OpenSSL::Guess

OpenSSL 路径检测辅助工具 - 鸿蒙平台预编译包

## 软件介绍

Crypt::OpenSSL::Guess 提供 OpenSSL 安装路径检测功能，用于其他 Crypt::OpenSSL::* XS 模块的编译配置。

### 主要特性
- 自动检测 OpenSSL include 路径
- 自动检测 OpenSSL library 路径
- 支持 OPENSSL_PREFIX 环境变量覆盖
- 纯 Perl 实现，无 XS 组件

### 技术信息
- **版本**: 0.15
- **许可证**: Perl Artistic License
- **构建系统**: ExtUtils::MakeMaker (Makefile.PL)
- **类型**: 纯 Perl 模块

## 鸿蒙平台适配

### 编译状态
- **编译日期**: 2026-06-16
- **平台**: OpenHarmony (aarch64-unknown-linux-ohos)
- **状态**: ✅ 编译成功，可加载

### 功能验证

#### 测试结果
- **测试日期**: 2026-06-16
- **测试用例**: 13 个
- **通过率**: 100% (13/13)
- **测试结论**: ✅ **ALL TESTS PASSED**

#### 验证功能
```perl
use Crypt::OpenSSL::Guess qw(openssl_inc_paths openssl_lib_paths);

# OpenSSL 路径检测
print openssl_inc_paths();  # -I/path/to/include (空值表示标准位置)
print openssl_lib_paths();  # -L/usr -L/usr/lib

# OpenSSL 前缀和版本
print find_openssl_prefix();  # /usr
print openssl_version();      # 3.0.9
```

#### 测试覆盖
- ✅ 模块加载和导出函数验证
- ✅ OpenSSL 路径检测功能验证
- ✅ OPENSSL_PREFIX 环境变量支持验证
- ✅ Makefile.PL 集成场景验证
- ✅ 依赖链完整性验证（Crypt::OpenSSL::RSA/Random）

#### 详细报告
- 功能测试报告: `reports/test-report.md`
- 质量门禁报告: `reports/quality-report.md`

#### 质量门禁
根据 ARCHIVE-SPEC v2.0 规范，通过全部质量门禁：
- ✅ G0 干净构建验证
- ✅ G1 二进制完整性（纯 Perl 无二进制）
- ✅ G2 功能可用性
- ✅ G3 可移植性
- ✅ G4 档案完整性

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.15 | published | 2026-06-16 |

## 相关模块

- **Crypt::OpenSSL::Random**: OpenSSL 随机数生成器 (XS)
- **Crypt::OpenSSL::RSA**: OpenSSL RSA 加密 (XS)
- **Mail::DKIM**: DKIM 签名验证