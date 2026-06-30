# inframap

## 软件描述

inframap 是一个从 Terraform tfstate 或 HCL 文件生成图形的工具，支持每个 Terraform provider 的特定资源关系可视化。

- **项目主页**: https://github.com/cycloidio/inframap
- **许可证**: MIT
- **构建系统**: Go
- **编程语言**: Go

## 功能特性

- 从 Terraform tfstate 生成图形
- 从 HCL 配置文件生成图形
- 支持多个 Terraform provider
- 可视化资源依赖关系
- 支持导出多种格式（DOT、SVG 等）

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| v0.8.1 | built | 2026-06-05 | 成功编译，可执行 |

## 依赖

### 编译依赖
- Go 1.22.0+（通过 goenv 安装）
- GOPROXY: https://goproxy.cn（国内镜像）

### 运行依赖
- 无外部依赖（静态链接）

## 使用说明

```bash
# 查看 tfstate 文件的图形
inframap --tfstate path/to/terraform.tfstate

# 从 HCL 配置生成图形
inframap --hcl path/to/terraform/config

# 导出到 DOT 格式
inframap --tfstate path/to/terraform.tfstate --output dot

# 导出到 SVG（需要 graphviz）
inframap --tfstate path/to/terraform.tfstate --output svg
```

## OpenHarmony 特殊说明

### HMDFS SELinux 权限处理

由于 HMDFS 文件系统的 hmmac 强制访问控制（SELinux 权限限制），Go 编译器工具链需要放置在 `/data/storage/el2/base/cache` 目录下才能正常执行。该目录允许未签名的 ELF 文件执行。

### Go 工具链安装

如果系统未预装 Go 编译器，可以通过以下方式安装：

```bash
# 使用 goenv 安装
goenv install 1.22.0
goenv global 1.22.0

# 复制到可执行目录（解决 SELinux 限制）
cp -r ~/.goenv/versions/1.22.0 /data/storage/el2/base/cache/go-1.22.0
export GOROOT=/data/storage/el2/base/cache/go-1.22.0
export PATH=$GOROOT/bin:$PATH
```

## 相关链接

- [GitHub 仓库](https://github.com/cycloidio/inframap)
- [文档](https://github.com/cycloidio/inframap/tree/master/docs)
- [发布页面](https://github.com/cycloidio/inframap/releases)