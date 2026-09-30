# qrcp 0.11.6 HarmonyOS PC 适配说明

## 软件信息

- 软件：qrcp
- 版本：0.11.6（上游 tag `v0.11.6`）
- 上游：https://github.com/claudiodangelis/qrcp
- 许可证：MIT
- 语言：纯 Go（module `github.com/claudiodangelis/qrcp`，`go 1.18`）
- 构建系统：Go 工具链（上游 `.goreleaser.yml`，无 Makefile/CMake/autotools）

## 源码

- URL：`https://codeload.github.com/claudiodangelis/qrcp/tar.gz/refs/tags/v0.11.6`
- SHA256：`a3eff505f366713fcb7694e0e292ff2da05e270f9539b6a8561c4cf267ec23c8`
- 归档大小：13,297,138 字节

## 依赖

- qrcp 为**纯 Go** 程序，`.goreleaser.yml` 强制 `CGO_ENABLED=0`，无 C/C++ 第三方库。
- `go.mod` 声明的 33 个依赖全部为 Go module（11 直接 + 22 间接/`indirect`），
  由 Go 工具链从 GOPROXY 自动拉取并静态链接进单一二进制，**无任何 conan 运行时依赖**。
- 结论：强制第三方依赖数量 = 0（详见依赖分析报告）。

## HarmonyOS PC 适配

参考仓库既有 Go CLI 适配方式（abbtr / aiac 模式）：

- `CGO_ENABLED=0`、`GOOS=linux`、`GOARCH=arm64`：交叉编译为 aarch64 静态 ELF，
  HarmonyOS（Linux 兼容内核）可直接运行。
- **自引导 Go 工具链**：conanfile.py 内置下载 `go1.23.8.linux-<hostarch>.tar.gz`
  （官方 URL + sha256 校验）到可写工作区，不依赖宿主机预装 Go。
- **避免 HMDFS mmap 限制**：Go 链接输出写入 ext2 风格可写工作区
  （`/data/storage/el2/base/haps/entry/files/qrcp-0.11.6-go/link-out`）。
- **OHOS ELF 签名**：Go SDK 工具二进制与最终 `qrcp` 二进制均使用
  `binary-sign-tool` 自签名（写入 `.codesign` 段），否则 HarmonyOS 拒绝 fork/exec。
- 构建命令（等价）：

  ```sh
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local \
  go build -trimpath \
    -ldflags "-s -w -X github.com/claudiodangelis/qrcp/version.version=0.11.6 \
                     -X github.com/claudiodangelis/qrcp/version.date=2026-09-29" \
    -o qrcp .
  ```

## 上游测试

- 上游测试入口：`.github/workflows/main.yml` 的 test job → `go test ./...`。
- 全仓唯一测试文件：`config/config_test.go`，含 1 个测试函数 `TestNew`
  （表驱动，5 个子用例：partial / init / #2 / #2 / overrides）。
- 执行命令：`go test -v -count=1 -exec=<sign-wrapper> ./...`
  （`-exec` 包装器在 OHOS 上对编译出的测试二进制补签名后执行）。
- 实测结果：discovered=6，executed=6，passed=6，failed=0，skipped=0。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go mod download` 失败：`lookup goproxy.cn on 8.8.8.8:53: i/o timeout` | HarmonyOS 仅拦截 libc `getaddrinfo`，Go 纯解析器（CGO_ENABLED=0 下 `netdns=cgo` 不可用）无法解析 DNS | 构建环境提供可达 GOPROXY（CI 正常 DNS；本机 W3 用 127.0.0.1 代理转发） |
| 2 | 上游测试 `fork/exec …/config.test: permission denied` | OHOS 拒绝执行未签名 ELF | `go test -exec` 包装器：执行前用 `binary-sign-tool` 给测试二进制补签名 |
| 3 | 上游测试 `panic: route ip+net: netlinkrib: permission denied` | HarmonyOS 对沙箱进程限制 `AF_NETLINK`，`net.Interfaces()` 失败，进而 `config.New()` 与 `TestNew` panic | 补丁 `patches/0001-ohos-netlink-and-tmpdir.patch`（见下） |
| 4 | 上游测试 `t.Skip()`（`os.CreateTemp` 失败） | 测试开头 `os.Clearenv()` 清空 `TMPDIR`，回退到只读 `/tmp` | 同上补丁：跨 `os.Clearenv()` 保留 `TMPDIR` |

## 源码修改（补丁）

`patches/0001-ohos-netlink-and-tmpdir.patch`（patch_type: portability，无平台宏）：

1. `config/config.go`：`New()` 在接口自动探测失败时不再 `panic`，改为打印告警并保留
   未设置的接口（调用方可用 `--interface` 显式指定）——避免沙箱 `AF_NETLINK`
   受限导致的启动崩溃。
2. `config/config_test.go`：
   - 跨 `os.Clearenv()` 保留 `TMPDIR`（HarmonyOS `/tmp` 只读）；
   - `chooseInterface` 失败时不再 `panic`，仅跳过接口归一化，配置解析断言仍完整执行。

> 补丁为最小化的平台可移植性修改，不改变 qrcp 在网络可用环境下的原有行为。

## 依赖版本

- Go 工具链：1.23.8（自引导，arm64/amd64）
- Go modules：由 `go.mod`/`go.sum` 锁定（共 33 个，均 Go module）

## 验证结果

```sh
# 真实 conan create（host/build profile = ci/conan/profiles/ohos-aarch64）
conan create . -pr:h=... -pr:b=...
# 结果：build OK；上游测试 6/6 PASS；test_package 6/6 PASS
```

- 上游测试：`go test -v -count=1 -exec=… ./...` → `ok github.com/claudiodangelis/qrcp/config`
- test_package：`test_qrcp.sh` 6 项断言全过（含鸿蒙 `.codesign` 校验）

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/qrcp` | 静态 aarch64 ELF，已 OHOS 自签名 |
| `licenses/LICENSE` | 上游许可证 |
| `res/README.md` | 上游说明 |

## 注意事项

- HarmonyOS 沙箱（本工作环境）限制 `AF_NETLINK`，qrcp 的自动网卡探测不可用；
  实际使用时可通过 `--interface` 指定网卡，或由具备网络信息权限的环境运行。
- 二进制必须保持 `.codesign` 段（`conan install` 后由包直接提供，无需二次签名）。
---

**编译结束**: 2026-09-29 21:26
**最终状态**: built
