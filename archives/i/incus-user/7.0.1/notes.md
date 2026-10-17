# incus-user 7.0.1 适配笔记

## 编译环境
- 构建系统: custom（Go toolchain / `go build`）
- 编译日期: 2026-10-10
- 编译器: go1.26.5 (linux/arm64)，`CGO_ENABLED=0`
- 状态: built

## 编译步骤

```bash
# 1. 上游源码（官方 GitHub tag 归档，sha256 校验）
#    https://github.com/lxc/incus/archive/refs/tags/v7.0.1.tar.gz
#    sha256=69068dd6cd94eb70d3cb007140eb6b3211937ebfd16f6cedb0ee5e5aa073a2dc
# 2. 自举 Go SDK 1.26.5（linux-arm64）并对其所有 ELF 做 OHOS 自签名
binary-sign-tool sign -selfSign 1 -inFile <elf> -outFile <elf>.signed -signAlg SHA256withECDSA
# 3. 真实构建（-toolexec 包装器重定向链接器输出到 /dev/shm；GitHub 归档无 vendor/）
cd incus-7.0.1
go mod download                                   # GOPROXY=https://goproxy.cn,direct
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local GOFLAGS=-mod=mod \
  GOSUMDB=off go build -toolexec $HOME/tmp/toolexec_wrapper.sh -trimpath \
  -ldflags "-s -w" -o bin/incus-user ./cmd/incus-user
# 4. 对产物签名（OHOS 未签名 ELF 不可执行）
binary-sign-tool sign -selfSign 1 -inFile bin/incus-user -outFile bin/incus-user.signed -signAlg SHA256withECDSA
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `/…/go-sdk/go/bin/go: Permission denied`(126) | OHOS 内核拒绝 execve 未签名 ELF；Go SDK 内 10 个 ELF 均未签名 | 对 `bin/go`、`bin/gofmt`、`pkg/tool/linux_arm64/*` 逐个 `binary-sign-tool` 自签 |
| 2 | `link: mapping output file failed: permission denied` | E523：链接器对输出文件调用 `fallocate(fd,0,0,size)`，HMDFS 返回 EACCES，而 Go 链接器只忽略 ENOTSUP/EOPNOTSUPP/EPERM/ENOSYS，不忽略 EACCES | `-toolexec` 包装器把链接器 `-o` 输出重定向到支持 fallocate 的 `/dev/shm`，链接后回拷原路径 |
| 3 | `-toolexec` 报 `fork/exec …/lan: no such file or directory` | 包装器路径含空格（`lan work`），Go 按空格切分 `-toolexec` 值 | 包装器放到无空格路径（`/dev/shm/incus-user-toolexec.sh`）；配方内自动选择无空格目录 |
| 4 | `go test` 报 `fork/exec ….test: permission denied` / `operation not permitted` | E318：测试二进制未签名不可执行；且 go 在链接后会改写文件，包装器内即时签名会因文件被改写而失效 | 改用 `go test -c` 编译 → 签名 → 直接执行测试二进制（签名在最终拷贝之后） |

## 源码修改

无补丁（`patches_applied: []`）。OHOS 适配全部通过配方环境变量 + toolexec 包装器完成，未改动上游源码。

## 依赖版本

- 无第三方 C/C++ 库依赖（N=0，见 `.dep2/reports/incus-user-7.0.1.md`）
- Go 工具链: go1.26.5（linux/arm64）；上游 go.mod 要求 `go >= 1.25.11`
- Go 模块: 经 `go mod download`（GOPROXY=https://goproxy.cn）拉取（源为 GitHub git archive，无 vendor/）

## 验证结果

```bash
$ bin/incus-user --version
7.0.1

$ bin/incus-user --help
（正常列出 incus-user 用法）

# 上游测试（incus-user 闭包 8 个包）：151 PASS / 0 FAIL / 0 SKIP
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/incus-user | 15,007,906 B | Incus 用户项目守护进程（aarch64 静态 ELF，OHOS 已签名） |

## 注意事项

- incus-user 是守护进程，实际运行需 net/cgroups/dbus 与系统 incusd；OHOS 无这些 OS 设施，本库仅保证构建与 CLI 可用。
- 上游服务端组件（incusd/incus-agent/incus-migrate 等）需 CGO + liblxc/cowsql，OHOS 不可构建，不在本库范围。
- 同源先例：`archives/i/incus/7.1.0`（同一 `incus-user` 二进制，CGO_ENABLED=0 built）。
---

**编译结束**: 2026-10-10 20:15
**最终状态**: built
