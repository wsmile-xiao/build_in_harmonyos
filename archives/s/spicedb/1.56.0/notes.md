# spicedb 1.56.0 — HarmonyOS PC 适配 notes

## 上游信息
- 仓库：https://github.com/authzed/spicedb（Google Zanzibar 灵感权限数据库）
- tag：`v1.56.0`
- 源码 tarball：`https://github.com/authzed/spicedb/archive/refs/tags/v1.56.0.tar.gz`
- SHA256：`e8c15ecc241e3f50feeab0c63062c961e4558608f25376623ce38e44ec3897b1`（已用 gh-proxy 实际字节核验一致）
- 许可证：Apache-2.0
- 语言：Go（`go.mod` 要求 `go 1.26.5`），纯静态，`CGO_ENABLED=0`

## 构建
- 入口：`go build -trimpath ./cmd/spicedb`，产物二进制 `spicedb`
- 版本注入：`-ldflags "-s -w -X github.com/jzelinskie/cobrautil/v2.Version=1.56.0"`（与上游 Homebrew 打包一致）
- 目标：`GOOS=linux`、`GOARCH=arm64|amd64`，静态链接

## OHOS 平台要点（编译 Agent 门禁）
1. **Go 工具链版本**：go.mod 要求 go 1.26.5，必须用 ≥1.26.5 的 SDK（`GOTOOLCHAIN=local`）。SDK 下载 sha256：
   - linux-arm64：`fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49`
   - linux-amd64：`5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053`
   - 与官方 go1.26.5 校验值一致。
2. **Go linker mmap 失败（E051/E046）**：在 HMDFS/tmpfs 上 `linker mapping output file failed`。链接输出必须放到 ext2 类可写工作区（配方用 `OHOS_GO_WORKDIR`，默认 `/data/storage/el2/base/haps/entry/files/spicedb-conan-go`）。
3. **ELF 签名**：OHOS 上每次 exec 的 ELF（spicedb 主程序与 `go test` 生成的 `*.test` 二进制）都必须带 `.codesign` 段，否则 `Permission denied`。用 `binary-sign-tool` 签名；上游测试通过 `go test -exec <wrapper>`（wrapper 先签名再 exec）。
4. **Go 工具链本身可执行性**：解压后 SDK 内 `bin/go`、`pkg/tool/*/` 也需要签名（若本机已有可用 go 工具链则优先复用，避免 SDK 可执行性坑）。

## 上游测试
- spicedb 是大型 Go 模块，`go test -v -count=1 ./...` 覆盖默认（非 build-tag）单元测试。
- 部分套件（postgres/mysql/spanner 等 datastore 后端，以及 `integration` build-tag 套件）需外部服务/容器，OHOS worker 不可用；本适配运行默认单元测试并如实统计 PASS/FAIL/SKIP。
- 统计以最终 `HMBS_UPSTREAM_TEST_RESULT` 与 PR 中的真实日志为准。

## 交付物
- `bin/spicedb` 可执行
- `licenses/LICENSE`（Apache-2.0）
- `share/doc/spicedb/README.md`
---

**编译结束**: 2026-08-27 20:45
**最终状态**: built
