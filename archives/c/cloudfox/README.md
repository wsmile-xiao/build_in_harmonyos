# cloudfox

## 基本信息
- **名称**: cloudfox
- **类别**: security（安全审计工具）
- **许可证**: MIT
- **维护者**: BishopFox
- **上游 URL**: https://github.com/BishopFox/cloudfox

## 描述
CloudFox 是一个用于评估云环境（AWS、Azure、GCP）安全性的工具。它可以帮助安全审计人员快速识别云环境中的潜在风险和配置问题。

## 主要功能
- AWS 安全审计
- Azure 安全审计
- GCP 安全审计
- 权限分析和发现
- 资源枚举

## 编译版本
- 1.14.0（2024-04-16）：兼容 Go 1.21/1.22，推荐用于鸿蒙系统
- 2.0.5（最新）：需要 Go 1.25+，暂不支持

## 依赖
- Go >= 1.21（1.14.0 版本）
- Go >= 1.25（2.0.5 版本，暂不支持）

## 安装
```bash
# 通过预编译包安装（推荐）
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- cloudfox 1.14.0

# 验证安装
cloudfox --help
```

## 使用示例
```bash
# AWS 安全审计
cloudfox aws --profile default

# Azure 安全审计
cloudfox azure

# GCP 安全审计
cloudfox gcp
```

## 编译说明
详见各版本的 notes.md 和 reports/build-report.md。

## 相关链接
- GitHub: https://github.com/BishopFox/cloudfox
- 官方文档: https://github.com/BishopFox/cloudfox/blob/main/README.md

