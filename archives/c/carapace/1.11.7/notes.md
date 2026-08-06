# carapace 1.11.7 适配笔记

## 编译环境
- 构建系统: Go (go build)
- 编译日期: 2026-08-05
- 编译器: Go 1.24.0 (自动下载)
- 状态: built

## 编译步骤

carapace 是一个 Go 语言 shell 补全库项目。本配方使用 Go SDK 从源码编译两个二进制：
`carapace` (来自 ./example) 和 `carapace-nonposix` (来自 ./example-nonposix)。

**构建方案**：从源码编译（参照 chkbit 配方模式）

具体步骤：
1. `ohc-run.py init-build carapace 1.11.7 --url=https://github.com/carapace-sh/carapace/archive/refs/tags/v1.11.7.tar.gz`
2. `ohc-run.py conan-init carapace 1.11.7` 生成配方骨架
3. 手动编写 conanfile.py（基于 chkbit Go 配方模式）
4. `ohc-run.py conan-verify carapace 1.11.7` 验证配方
5. `ohc-run.py finish carapace 1.11.7 built`
6. `ohc-run.py submit carapace 1.11.7`

## Go 工具链处理

- Go SDK 1.24.0 从 golang.google.cn 自动下载
- 所有 Go SDK ELF 二进制在 OHOS 上签名后执行
- 工作区使用 /data/storage/el2/base/haps/entry/files/ 绕过 HMFS mmap 限制
- CGO_ENABLED=0 纯 Go 编译，GOOS=linux GOARCH=arm64

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go linker mmap "permission denied" | HongMeng 安全模型限制 Go 链接器 mmap 操作 | 使用 /data/storage/el2/base/haps/entry/files/ 工作区（参照 chkbit 配方） |
| 2 | Go SDK 二进制无法执行 | 未签名 ELF 在 OHOS 上不可执行 | 对所有 Go 工具链二进制执行 binary-sign-tool 签名 |
| 3 | 上游测试需要链接器 | Go test 产生的测试二进制也需要链接 | 在 OHOS 上使用 go test -c 编译到工作区，签名后执行 |

## 源码修改

无源码修改。从源码直接编译。

## 依赖版本

- Go 1.24.0 (自动下载，工具链需 ELF 签名)

## 验证结果

```bash
$ carapace --version
example version example

$ carapace-nonposix --help
nonposix examples
Usage: example-nonposix [flags]
...
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/carapace | 主二进制 (ELF 64-bit arm64 static) |
| bin/carapace-nonposix | 非POSIX示例二进制 (ELF 64-bit arm64 static) |

## 注意事项

1. **Go 链接器 mmap 限制**：OHOS 平台限制 Go 链接器的 mmap 操作，使用 /data/storage/el2/base/haps/entry/files/ 工作区绕过。
2. **ELF 签名必需**：所有可执行二进制（包括 Go 工具链）必须在 OHOS 上签名才能执行。
3. **CGO_ENABLED=0**：纯 Go 编译，静态二进制，不依赖本地 C 库。
---

**编译结束**: 2026-08-05 15:33
**最终状态**: built
