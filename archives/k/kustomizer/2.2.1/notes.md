# kustomizer v2.2.1 鸿蒙PC (aarch64) 适配笔记

## 编译信息

| 项 | 值 |
|---|---|
| 软件 | kustomizer 2.2.1 |
| 上游 | https://github.com/stefanprodan/kustomizer (tag v2.2.1) |
| 许可证 | Apache-2.0 |
| 语言 / 构建系统 | Go / Makefile（本配方直接调用 go build） |
| 构建工具链 | 官方静态 go1.24.13 linux-arm64（构建时自举） |
| 目标平台 | HarmonyOS PC, os=OHOS 6.0, arch=armv8 (aarch64) |
| 构建方式 | CGO_ENABLED=0，纯静态二进制 |
| 构建日期 | 2026-10-05 |

## 适配过程

### 1. 源码获取

conandata.yml 指向官方 GitHub tag 归档（R39）：

```
https://github.com/stefanprodan/kustomizer/archive/refs/tags/v2.2.1.tar.gz
sha256 = bba48e2eed5b84111c39b34d9892ffc9f0575b6f6470d50f832f47ff6417bf03
```

### 2. Go 工具链自举（核心适配点）

本机/CI 均无系统 Go 工具链，制品仓 ohpcd 也没有 golang 包（已用
`conan download "golang/*" -r=ohpcd --only-recipe` 实测为空）。配方在 build
folder 私有目录 `_go/` 内自举官方工具链：

1. 解析上游 `go.mod` 的 `go 1.19` 最低版本要求；
2. 从 go.dev 发布清单（`https://go.dev/dl/?mode=json&include=all`）交叉校验
   固定工具链版本的官方 sha256；
3. 从官方源 `https://go.dev/dl/go1.24.13.linux-arm64.tar.gz`
   （备选 `golang.google.cn/dl`）下载，下载后再次本地校验 sha256；
4. 解压到 build folder 私有前缀（R49，不污染共享目录）。

**为什么用 go1.24.13 而不是 go.mod 要求的 1.19？** 实测官方
go1.19.x linux-arm64 工具链是动态链接 glibc 的（ELF 解释器
`/lib/ld-linux-aarch64.so.1`，依赖 libc.so.6/libpthread.so.0），而鸿蒙用户态
只有 musl，无 glibc 兼容层，go1.19 工具链根本无法启动。Go 自 1.20 起官方
linux-arm64 发行版改为纯静态；经实测 go1.24.13 为完全静态二进制，可直接在
鸿蒙上运行，且对声明 `go 1.19` 的模块向后兼容（Go 1 兼容性承诺）。

### 3. 工具链 ELF 自签名

鸿蒙强制签名：任何未签名 ELF 执行时返回 Permission denied (EACCES)。因此
自举后不仅 `bin/go`，GOROOT 内 `pkg/tool/linux_arm64/` 下的 compile、link、
asm、vet 等全部构建期实际调用的工具（共约 20 个）都必须用
`binary-sign-tool` 自签名。签名范围限定在 `bin/` 与 `pkg/tool/`，不处理
`src/**/testdata` 下的测试样本 ELF 和 race `.syso`（构建不会执行它们，签名
反而会破坏 Go 自带测试夹具）。

旧版 Go 链接产物（以及 Go 1.19 时代链接的 k8s/etcd 二进制）段表布局会导致
签名器报 "Failed to save 4K data to .codesign section"；先用 GNU strip 规整
段头即可签名成功。

### 4. 构建

通过 `self.run` 在受控环境下构建（不裸用宿主机环境变量，R33）：

```
CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
GOPROXY=https://goproxy.cn,https://goproxy.io,direct \
GOTOOLCHAIN=local GOFLAGS=-mod=mod \
go build -trimpath -ldflags="-s -w -X main.VERSION=2.2.1" \
  -o kustomizer ./cmd/kustomizer
```

- `CGO_ENABLED=0`：纯静态、internal link，不依赖 OHOS 系统库，也避开沙箱内
  缺失的 external linker (gold)；
- `-X main.VERSION=2.2.1`：上游版本变量（见 cmd/kustomizer/main.go，默认值
  2.0.0-dev.0），使 `kustomizer --version` 输出真实版本；
- 产物再经 strip（如需）+ 自签名后打包到 `bin/kustomizer`。

### 5. 功能验证

- `kustomizer --version` → `kustomizer version 2.2.1`
- `kustomizer --help` → 正常列出全部子命令
- 离线清单构建（不需集群/registry）：对最小 ConfigMap 清单执行
  `kustomizer build inv`，成功输出渲染后的 Kubernetes YAML，证明核心构建
  链路在鸿蒙真实可用。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律 |
|---|------|------|----------|------|
| 1 | 无 Go 工具链，ohpcd 也无 golang 包 | 赛事物/CI 不预装 Go | 配方内从 go.dev 自举官方静态工具链并校验 sha256 | W0, R49 |
| 2 | go1.19 官方工具链无法执行 | 动态链接 glibc，OHOS 只有 musl | 选用纯静态的 go1.24.13（向后兼容 go1.19 模块） | R32 |
| 3 | bin/go 执行报 Permission denied | OHOS 强制 ELF 签名 | 用 binary-sign-tool 自签名 | R40 |
| 4 | 只签 go 后构建仍失败 | compile/link/asm 等 GOROOT 工具同样未签名 | 对 bin/ 与 pkg/tool/ 下全部工具签名 | R40 |
| 5 | 签名器报 .codesign 写入失败 | 旧 Go ELF 段表布局不兼容 | 先 GNU strip 再签名 | R40 |
| 6 | 上游测试 kube-apiserver 启动超时 | 沙箱无默认路由，无法自动选择 advertise address | 测试 assets 中用 wrapper 给 apiserver 追加 --advertise-address=127.0.0.1（不改上游代码/测试） | R51 |
| 7 | etcd 启动失败 (WAL preallocate) | HMDFS 不支持 fallocate | TMPDIR 指向 /data/storage/el2/base/cache | R23 |

## 上游测试

通过自举 Go 工具链 + 手动组装的 envtest assets（从 dl.k8s.io 下载官方静态
kube-apiserver/kubectl、从 etcd 官方发行版下载 etcd，strip+签名）真实运行
了上游全部测试。**15 个顶层测试函数、37 个子测试全部 PASS，0 FAIL，0
SKIP，通过率 100%**。逐条明细与运行方法见
`reports/upstream-test-ledger.md`。

## 验证记录

- `conan create archives/k/kustomizer/2.2.1 -pr:b default -pr:h default`
  （OHOS 6.0 / armv8 / clang 15 profile）实际执行成功：包从源码构建、
  打包 `bin/kustomizer`（约 36 MB），生成 package revision。
- 本配方在补齐 test_package 后再次执行 conan create 以确认 test_package
  真实通过（见下方复跑记录与 reports）。

## 已知限制

1. kustomizer 面向 Kubernetes 集群（server-side apply 需集群 v1.20+），
   apply/diff inventory 等运行期命令需用户自备 kubeconfig；适配侧已通过
   envtest 本地控制平面验证这些命令的完整行为。
2. 工具链自举需联网下载约 71 MB 的 Go tarball 与 Go modules（走 goproxy.cn
   等代理）；CI 网络需可达 go.dev / golang.google.cn 与 module 代理。
3. 版本目录 status 为 built（未经赛事 CI upload，不标 published）。
