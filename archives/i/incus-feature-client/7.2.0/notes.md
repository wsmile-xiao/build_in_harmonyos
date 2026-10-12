# incus-feature-client 7.2.0 适配笔记

## 编译环境
- 构建系统: custom（Go toolchain / `go build`）+ Conan 2
- 编译日期: 2026-10-10
- 编译器: 不涉及（纯 Go 交叉编译，`CGO_ENABLED=0`）
- 宿主机: HarmonyOS PC (HongMeng Kernel 1.12.0, aarch64/Toybox)；conan 2.29.1（OHOS 适配版）
- 目标平台: OpenHarmony / HarmonyOS PC aarch64（`os=OHOS`, `arch=armv8`）
- 状态: built

## 目标识别
- 目标库 `incus-feature-client/7.2.0` = Alpine 源包 `incus-feature`（`community/incus-feature/APKBUILD`，7.2.0-r0）
  的二进制子包；`client()` 函数把 `/usr/bin/incus` 拆出，即 Incus CLI 客户端。
- 上游源码 = `github.com/lxc/incus` tag **v7.2.0**（`module github.com/lxc/incus/v7`，`go 1.25.10`）。
- 源码 tarball sha256 = `03c48d5fbd097c5e4ae16e96efa768a5f147b86adada7a824f15af017b075bf0`
  （与 APKBUILD 声明的 sha512 `e1875cf7…860c` 同源一致）。

## 编译步骤

```bash
# 1) 初始化（下载/解压 incus v7.2.0 到 .work，生成 .build-context）
python3 scripts/ohc-run.py init-build incus-feature-client 7.2.0 \
    --url=https://github.com/lxc/incus/archive/refs/tags/v7.2.0.tar.gz

# 2) 语言预检（R47；本任务语言 = go）
python3 scripts/ohc-run.py lang-preflight incus-feature-client 7.2.0 \
    --src <work> --lang go

# 3) 真实构建（等效于配方 build()）
export GOROOT=<go1.25.10>; export CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GOTOOLCHAIN=local
export TMPDIR=$WS/tmp GOTMPDIR=$WS/tmp GOCACHE=$WS/gocache GOMODCACHE=$WS/gomodcache
go build -trimpath -o $WS/bin/incus ./cmd/incus
binary-sign-tool sign -selfSign 1 -inFile $WS/bin/incus -outFile $WS/bin/incus.signed -signAlg SHA256withECDSA

# 4) 上游测试（客户端 import 闭包，逐包）
go test -v -count=1 -exec="bash sign-exec.sh" <closure packages>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go build` 报 `link: mapping output file failed: permission denied` | HMDFS 不支持 Go 链接器对输出文件的 mmap | 链接产物与 GOTMPDIR/GOCACHE/GOMODCACHE 放到 ext2 风格可写分区 `/data/storage/el2/base/haps/entry/files` |
| 2 | 构建成功的 ELF 执行报 `permission denied`（退出码 126） | OHOS 只执行带 `.codesign` 段的 ELF | `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` 自签名（产物 + go test 测试二进制） |
| 3 | `go mod download` / `go build` 卡死在 DNS：`lookup goproxy.cn on 8.8.8.8:53: i/o timeout` | Go 纯解析器（CGO_ENABLED=0，`netdns=cgo` 不可用）直连 resolv.conf 名称服务器超时；而系统 `getaddrinfo`（curl 用）正常 | 提供可达 GOPROXY（本机以本地转发代理注入 `GOPROXY=http://127.0.0.1:8786`）；配方默认 `GOPROXY=https://goproxy.cn,direct`，可经环境变量覆盖 |
| 4 | `go test ./...` 中服务端包编译失败 | `cmd/incusd`、`internal/server/*` 需 CGO + liblxc/cowsql/go-sqlite3 | 客户端任务只在 `./cmd/incus` 的 import 闭包内执行测试（与服务端解耦） |
| 5 | `shared/subprocess::TestSignalHandling` 在用 `nohup` 启动测试时失败（HUP trap 不生效、进程被 SIGUSR1 杀死） | `nohup` 将 SIGHUP 置为 SIG_IGN，并被 `sh` 子进程继承；POSIX 规定启动时被忽略的信号不可被 trap | 测试运行器不使用 `nohup`（前台运行）；已实测前台 12/12 包全通过 |

## 源码修改

无。`patches: []` —— 客户端为纯 Go，`CGO_ENABLED=0` 直接交叉编译；全部 OHOS 适配落在构建配方层（Go 自举、HMDFS 产物路径、ELF 签名、GOPROXY）。

## 依赖版本

- Go 工具链: 1.25.10（配方内自举下载）
- 第三方 C/C++ 强制依赖: **无（N=0）**
- Go modules: 由 `go mod` + GOPROXY 自动拉取（不计入强制第三方依赖）

## 验证结果

```bash
$ bin/incus --version
7.2
$ bin/incus --help | head -1
Command line client for Incus
$ llvm-objdump -f bin/incus
bin/incus:  file format elf64-littleaarch64   (architecture: aarch64)
$ readelf -S bin/incus | grep codesign
  [..] .codesign  ...           # OHOS 执行前置要求
$ # 上游测试（客户端 import 闭包，12 包）
$ go test -v -count=1 -exec="bash sign-exec.sh" <12 packages>
... 248 case(s): PASS=248 FAIL=0 SKIP=0  (12/12 packages ok)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/incus` | ~31.7 MB | Incus CLI 客户端（静态 aarch64 ELF，已 OHOS 签名） |

## 注意事项

- 仅提供客户端；运行时需另行连接 Incus 守护进程（`incusd`）。
- 服务端 `incusd` 需 CGO + liblxc/cowsql/libsqlite3/libudev，OHOS 不可用（与 `archives/i/incus` 7.1.0 结论一致）。
---

**编译结束**: 2026-10-10 19:57
**最终状态**: built
