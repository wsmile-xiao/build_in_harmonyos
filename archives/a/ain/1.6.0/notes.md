# ain 1.6.0 适配笔记

## 编译环境
- 构建系统: custom (Go 项目，go build ./cmd/ain)
- 编译日期: 2026-08-08
- 编译器: Go 1.23.8 (clang 15.0.4 用于 CGO，本包 CGO_ENABLED=0)
- 状态: built

## 编译步骤

1. 下载源码：从官方 GitHub tag `https://github.com/jonaslu/ain/archive/refs/tags/v1.6.0.tar.gz`
2. 解压到 work 目录
3. 配置 Go 工具链（go1.23.8 linux-arm64 解压到工作区，ELF 用 binary-sign-tool 签名）
4. 编译命令：
```bash
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0
go mod download
go build -trimpath -ldflags "-s -w -X main.gitSha=v1.6.0" -o bin/ain ./cmd/ain
```
5. 链接输出重定向到非 hmdfs 工作区（/data/storage/el2/...），再复制回 bin/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 工具链二进制 Permission denied | hmdfs 下无 .codesign 段 ELF 被 Seccomp 拦截 | binary-sign-tool 签名 go/gofmt/pkg/tool 全部 ELF 后执行 |
| 2 | Go linker 报 mapping output file failed | linker mmap 输出文件在 hmdfs 失败（E051） | 链接输出目录放到 el2 tmpfs 工作区（aliyun 同款先例） |
| 3 | go test 测试二进制无法 exec | 测试产物未签名被 Seccomp 拦截 | go test -exec 包装器签名后运行 |
| 4 | e2e 测试失败（could not start command） | e2e 内部重建未签名 ain_test 且依赖 localhost HTTP 服务 | 记录为平台限制，非功能缺陷 |

## 源码修改

无补丁，源码未修改。

## 依赖版本

- Go 1.23.8（go.mod: go 1.13）
- github.com/hashicorp/go-envparse v0.1.0
- github.com/pkg/errors v0.9.1
- gopkg.in/yaml.v3 v3.0.1
- 无 C/C++ 依赖（CGO_ENABLED=0 纯静态）

## 验证结果

```bash
$ ./bin/ain -v
Ain 1.6.0 (v1.6.0) linux/arm64

$ go test ./internal/pkg/parse ./internal/pkg/utils
ok  github.com/jonaslu/ain/internal/pkg/parse  0.283s
ok  github.com/jonaslu/ain/internal/pkg/utils  0.288s
```

编译产物：2,278,336 字节 ELF static arm64（stripped），conan-verify G0-G4 + L2/L4/L5 全部通过。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ain | 2,278,336 字节 | Ain 终端 HTTP API 客户端 (stripped) |
| packaging/ain-1.6.0-ohos-aarch64.tar.gz | 2,310,517 字节 | 打包产物 |

## 注意事项

1. **Go 工具链签名**：OHOS 下 Go SDK 的 go/gofmt/pkg/tool/* 均为未签名 ELF，必须用 binary-sign-tool 签名后才能执行（配方内 `_sign_go_sdk_if_ohos` 自动处理）。
2. **HMDFS 链接限制**：Go linker 在 hmdfs 上 mmap 输出失败，链接输出目录必须放在非 hmdfs 工作区（OHOS 下默认 /data/storage/el2/base/haps/entry/files/ain-conan-go）。
3. **e2e 平台限制**：上游 e2e 测试内部重建未签名二进制并调用 localhost HTTP 服务，在 OHOS Seccomp 沙箱内无法完整执行，属平台已知限制；内部包单元测试（parse/utils）全部通过。
---

**编译结束**: 2026-08-08 15:13
**最终状态**: built
