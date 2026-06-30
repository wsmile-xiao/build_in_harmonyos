# perl-json-any

**描述**: Wrapper Class for the various JSON classes (DEPRECATED)

**官网**: https://metacpan.org/pod/JSON::Any

**许可证**: GPL-1.0-or-later

**分类**: data

**构建系统**: perl (Makefile.PL)

## 版本列表

- **1.40-r0** (2026-06-12): built - 功能验证通过，使用 JSON::PP 后端

## 注意事项

⚠️ **此模块已弃用 (DEPRECATED)**，建议使用 JSON::MaybeXS 替代。

## OHOS 适配说明

- 纯 Perl 模块，无 C/XS 代码
- 不需要 ELF 签名
- 依赖 JSON::PP 作为默认后端（已预装）
- 测试依赖缺失不影响运行时功能