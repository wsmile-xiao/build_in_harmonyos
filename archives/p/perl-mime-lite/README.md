# perl-mime-lite

MIME::Lite — 轻量级 Perl MIME 邮件生成模块。

## 版本

- **当前版本**: 3.033
- **状态**: built (功能验证通过)

## 描述

MIME::Lite 是一个用于生成 MIME 格式邮件的 Perl 模块。它支持创建文本、HTML 邮件，添加附件，构建多部分邮件结构，以及通过 SMTP 或 sendmail 发送邮件。

## 平台兼容性

- **目标平台**: OpenHarmony (aarch64)
- **模块类型**: 纯 Perl 模块（无 XS/C 组件）
- **SELinux 限制**: 无（纯 Perl，不受 HMDFS 限制）

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Email::Date::Format | ≥1.005 | 运行时依赖，需单独安装 |
| MIME::Types | ≥2.29 | MIME 类型推断 |
| MIME::Base64 | ≥3.16 | Perl 核心模块 |
| Mail::Address | ≥2.22 | 邮件地址解析 (perl-mailtools) |
| Mail::Header | ≥2.22 | 邮件头处理 (perl-mailtools) |

## 构建方式

```bash
perl Makefile.PL PREFIX=$DEFAULT_PREFIX
make
make install
```

纯 Perl 模块，无需 C 编译器。

## 验证结果

- 官方测试套件: ✅ 48/48 通过
- 自定义功能测试: ✅ 18/18 通过
- 质量门禁: ✅ G1-G4 全通过

详见各版本的 `reports/test-report.md`。
