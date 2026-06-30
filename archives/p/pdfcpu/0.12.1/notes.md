# pdfcpu 0.12.1 适配笔记

## 编译环境
- 构建系统: Go (CGO_ENABLED=0)
- 编译日期: 2026-05-25
- 编译器: go 1.25.10
- 状态: built

## 编译步骤

pdfcpu 是纯 Go 项目，采用静态编译方式（CGO_ENABLED=0），无需 C 编译器：

1. 下载源码 `go mod download`
2. 修补 go.sum 中的依赖版本冲突（部分依赖存在多个版本条目）
3. 编译 Release 版本：
   ```bash
   CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o pdfcpu
   ```
4. 编译 Debug 版本：
   ```bash
   CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -gcflags="all=-N -l" -o pdfcpu-debug
   ```
5. ELF 签名二进制文件
6. 创建 tar.gz 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | go.sum 存在重复版本条目 | 依赖更新后新旧版本 hash 同时存在 | 清理 go.sum，保留最新版本条目 |

## 源码修改

| 文件 | 原因 | 方式 |
|------|------|------|
| go.sum | 清理重复依赖版本条目 | 删除过旧的 x/crypto v0.49.0、x/text v0.35.0、x/image v0.38.0、go-runewidth v0.0.21/v0.0.22 条目 |

## 依赖版本

pdfcpu 是纯 Go 项目（CGO_ENABLED=0），无外部 C 依赖。Go 模块依赖：

| 依赖 | 版本 |
|------|------|
| github.com/hhrutter/lzw | v1.0.0 |
| github.com/hhrutter/pkcs7 | v0.2.2 |
| github.com/hhrutter/tiff | v1.0.3 |
| github.com/spf13/cobra | v1.10.2 |
| golang.org/x/crypto | v0.50.0 |
| golang.org/x/image | v0.39.0 |
| golang.org/x/text | v0.36.0 |

## 验证结果

- ✅ `pdfcpu version` 输出正确版本 v0.12.1
- ✅ 二进制为静态 ELF executable（aarch64，无动态库依赖）
- ✅ Release 版本 18MB（stripped），Debug 版本 76KB（调试符号单独打包）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pdfcpu-0.12.1-ohos-aarch64.tar.gz | 18MB | Release 制品（stripped 二进制） |
| pdfcpu-0.12.1-ohos-aarch64-debug.tar.gz | 76KB | Debug 制品（调试符号） |

## 注意事项
- CGO_ENABLED=0 静态编译，运行时无动态库依赖
- go.sum 需要修补以清理重复版本条目

**编译结束**: 2026-05-25
**最终状态**: built