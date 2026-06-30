# chamber homebrew 适配笔记

## 编译环境
- 构建系统: custom (Go)
- 编译日期: 2026-06-21
- 编译器: clang/clang++ (未使用，Go 自带编译器)
- Go 版本: go1.26.4 linux/arm64
- 状态: published

## 编译步骤

1. **源码获取**：GitHub 直接下载超时，使用 `go install github.com/segmentio/chamber/v3@latest` 通过 GOPROXY (https://goproxy.cn) 下载源码和依赖
2. **源码准备**：从 Go 模块缓存 `$(go env GOMODCACHE)/github.com/segmentio/chamber/v3@v3.1.5/` 复制源码到 work/orig 目录
3. **初始化**：使用 `ohc-run.py init-build chamber homebrew --url=... --no-download` 初始化（源码已就位）
4. **编译**：在 BUILD_SRC_DIR 中执行 `GOPROXY=https://goproxy.cn GOFLAGS=-mod=mod go build -o chamber .`
5. **安装到 staging**：`cp chamber $TEST_PREFIX$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build URL 搜索超时 | GitHub 在中国网络环境下访问不稳定 | 从 Go 模块缓存获取源码，使用 --no-download |
| 2 | GitHub 下载超时 | GitHub 直接下载在中国大陆受限 | 使用 GOPROXY=https://goproxy.cn 加速 Go 模块下载 |
| 3 | chamber --version 报错 | chamber 使用 cobra 框架，version 是子命令而非 flag | 使用 `chamber version` 获取版本 |
| 4 | git clone 失败 | libz.so 缺失 | 使用 go install/go build 代替 git clone |

## 源码修改

无源码修改，Go 项目直接编译。

## 依赖版本

- Go 1.26.4 (linux/arm64)
- GOPROXY=https://goproxy.cn
- Go 模块: github.com/segmentio/chamber/v3 v3.1.5
- 主要依赖: AWS SDK Go v2, cobra CLI 框架

## 验证结果

```bash
$ chamber version
chamber dev

$ chamber --help
CLI for storing secrets
Usage:
  chamber [command]
Available Commands:
  completion    Generate the autocompletion script for the specified shell
  delete        Delete a secret, including all versions
  env           Print the secrets from the parameter store in a format to export as environment variables
  exec          Executes a command with secrets loaded into the environment
  ...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| chamber-homebrew-ohos-aarch64.tar.gz | ~33MB | 预编译包 |

## 注意事项

- chamber 是 Go 语言编写的 AWS Secrets Manager CLI 工具
- Go 编译产生静态链接二进制，无需额外共享库依赖
- 版本显示为 "dev" 因为未设置 ldflags，如需正确版本需添加 `-ldflags "-X main.version=3.1.5"`
---

**编译结束**: 2026-06-21 14:26
**最终状态**: published
