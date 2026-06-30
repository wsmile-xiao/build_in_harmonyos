# Crypt::OpenSSL::RSA

OpenSSL RSA 加密接口 - 鸿蒙平台编译

## 软件介绍

Crypt::OpenSSL::RSA 提供 OpenSSL RSA 加密操作的 Perl 接口。

### 主要特性
- RSA 公钥/私钥加载
- RSA 加密/解密
- RSA 签名/验证
- 支持 PKCS1/X509 格式

### 技术信息
- **版本**: 0.33
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
- **产物**: RSA.so (42368 bytes)

### SELinux 限制
XS 模块在 HMDFS 目录无法加载，需要管理员安装到 `/data/service/hnp`。

### 依赖链
```
Mail::DKIM (DKIM签名)
    └── Crypt::OpenSSL::RSA (RSA操作)
            ├── Crypt::OpenSSL::Random (随机数)
            └── OpenSSL 1.1.1w
```

## 版本信息

| 版本 | 状态 | 发布日期 |
|------|------|---------|
| 0.33 | built | 2026-06-16 |

## 相关模块

- **Mail::DKIM**: DKIM 签名验证 (依赖RSA)
- **Crypt::OpenSSL::Random**: 随机数生成
- **Crypt::OpenSSL::Guess**: OpenSSL 路径检测