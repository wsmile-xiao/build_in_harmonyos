# tenv

**版本管理器**：用于管理多个版本的 OpenTofu、Terraform、Terragrunt、Terramate 和 Atmos。

## 描述

tenv 是一个版本管理工具，允许用户在同一系统上安装和管理多个版本的：
- OpenTofu (开源 Terraform 替代品)
- Terraform (基础设施编排工具)
- Terragrunt (Terraform 包装器)
- Terramate (基础设施编排工具)
- Atmos (云原生应用管理工具)

## 特性

- 多版本管理：安装和切换不同版本的工具
- 自动版本选择：基于配置文件自动选择合适的版本
- 简洁的 CLI：易于使用的命令行界面
- 支持多个工具：统一管理多种基础设施工具

## 构建系统

- **类型**: Go
- **语言**: Go 1.25+
- **构建命令**: `make build`

## 编译依赖

- go/1.25.0

## 安装

```bash
# 使用预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- tenv 4.12.2

# 验证安装
tenv version
tenv help
```

## 使用示例

```bash
# 安装 OpenTofu 版本
tenv tofu install 1.6.0

# 安装 Terraform 版本
tenv tf install 1.5.0

# 查看已安装版本
tenv tofu list
tenv tf list

# 切换版本
tenv tofu use 1.6.0
tenv tf use 1.5.0
```

## 二进制文件

- `tenv`: 主命令
- `tofu`: OpenTofu 包装器
- `terraform`: Terraform 包装器
- `terragrunt`: Terragrunt 包装器
- `terramate`: Terramate 包装器
- `atmos`: Atmos 包装器

## 官方资源

- **官网**: https://github.com/tofuutils/tenv
- **文档**: https://github.com/tofuutils/tenv#readme
- **源码**: https://github.com/tofuutils/tenv

## HarmonyOS 适配说明

- 所有二进制文件已完成 ELF 签名（覆盖率 100%）
- 需要设置 GOPROXY=https://goproxy.cn,direct 以访问依赖包
- Go 工具链需要 ELF 签名才能在 HarmonyOS 上运行