# unfurl 0.4.3 适配笔记

## 编译环境
- 构建系统: custom (Go 1.23.8 自举工具链, go build)
- 编译日期: 2026-08-15
- 编译器: clang/clang++ (宿主), GOOS=linux GOARCH=arm64 CGO_ENABLED=0 (产物)
- 状态: built

## 编译步骤

1. `init-build unfurl 0.4.3 --url=<官方 tag tarball>` 下载并解压源码（SHA256 核验见 manifest）
2. `conanfile.py` 按 ain/1.6.0 + addchain/0.4.0 Go CLI 先例编写：
   - 无本地 Go 工具链时自举下载 go1.23.8.linux-arm64（官方 + 镜像 fallback），GOTOOLCHAIN=local
   - `go mod download` 拉取 Cgboal/DomainParser、jakewarren/tldomains、golang.org/x/net (indirect)
   - `go build -trimpath -ldflags "-s -w" -o <exe> .`（根包 main）
3. OHOS 侧处理：
   - Go SDK 二进制与产物 ELF 用 binary-sign-tool 自签（.codesign 段）
   - linker mmap 失败（E051）：链接输出放到 /data/storage/el2/... 非 hmdfs 工作区
   - 上游测试用 `go test -exec` 包装器签名 *.test 二进制后执行
4. `test_package/`：test.sh 从 stdin 喂 URL 验证 domains/paths/keys/format 四个模式真实输出

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载 SSL 证书失败 | urllib 系统 CA 缺失 | 设置 SSL_CERT_FILE=certifi cacert.pem，ohc-run 自动安装 121 个根证书到 usr/local/ssl |
| 2 | Go 工具链不存在 | 设备无预装 Go | 配方自举下载 go1.23.8 linux-arm64 SDK |
| 3 | 未签名 ELF 不可执行 | OHOS Seccomp 拦截无 .codesign 的 ELF | binary-sign-tool 自签 SDK、产物与测试二进制 |

## 源码修改

无。上游源码未做任何修改，无 patches。

## 依赖版本

- Go SDK: 1.23.8 (linux-arm64, 自举)
- Cgboal/DomainParser v0.0.0-20210827145802-99068439e39f
- jakewarren/tldomains v0.0.0-20220401175117-e21ec594add9
- golang.org/x/net v0.0.0-20220401154927-543a649e0bdd (indirect)

## 验证结果

```bash
go test -v -count=1 ./...
# TestFormat: 32 个子用例全部 PASS, 0 FAIL, 0 SKIP
```

## 上游测试说明

上游仅 1 个测试文件 `format_test.go`：1 个测试函数 `TestFormat`，
由 32 个表驱动子用例（t.Run(strconv.Itoa(i))）组成，覆盖 format 模式
全部指令（%s/%u/%d/%S/%r/%t/%P/%p/%e/%q/%f/%%/%@/%:/%?/%#/%a）。

## 下一步

- conan-verify 8 道门禁
- finish unfurl 0.4.3 built
---

**编译结束**: 2026-08-15 22:25
**最终状态**: built
