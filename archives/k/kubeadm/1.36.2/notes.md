# kubeadm 1.36.2 适配笔记

## 编译环境
- 构建系统: Go (go build, CGO_ENABLED=0 静态链接)
- 编译日期: 2026-09-23
- Go 工具链: 1.26.4（recipe 自举下载 + binary-sign-tool 自签）
- 状态: built（CI #60613 conan create + test_package 通过，L0/L1 门禁通过）

## 项目说明

kubeadm 是 Kubernetes 集群引导工具（kubernetes/kubernetes 仓库 `cmd/kubeadm`，
module `k8s.io/kubernetes`）。v1.36.2 的 go.mod 声明 `go 1.26.0`，
需要 Go 1.26 工具链。源码归档自带完整 `vendor/` 目录，
使用 `-mod=vendor` + `GOPROXY=off` 离线编译，无需从 proxy 下载依赖。

## Go 工具链自举

CI worker 无预装 Go（此前 CI 报 `go: not found`），且 conan 2.29.1
无 `conan.tools.go`、无 `unpack` 方法。recipe 按 adbtuifm/abbtr 已发布
先例自举：

1. 有界下载器（urllib + curl 风格 UA，120s 超时 x 2）按镜像列表下载
   go1.26.4.linux-arm64.tar.gz（先 golang.google.cn，后备 dl.google.com），
   sha256 校验：`ef758ae7c6cf9267c9c0ef080b8965f453d89ab2d25d9eb22de4405925238768`（63,740,285 B）
2. OHOS 拒绝加载未签名 ELF（E318）：对工具链全部 ELF
   （bin/go、bin/gofmt、pkg/tool/linux_arm64/* 共 10 个）用
   `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA` 自签，
   `.ohos-signed` marker 避免重复签名
3. 链接产物输出到可写 workspace（`/data/storage/el2/base/haps/entry/files/`），
   签名后拷贝到 `build/bin/kubeadm`

本地适配机已验证：arm64 工具链签名后 `go version` 正常
（go1.26.4 linux/arm64）、go.mod `go 1.26.0` 满足要求、
vendor 树完整（-mod=vendor 离线可用）。

## 编译步骤

1. 下载源码（有界下载器，每镜像 120s 超时 x 2 次）:
   主源 gitee 镜像 `https://gitee.com/mirrors/kubernetes/repository/archive/v1.36.2.tar.gz`
   （sha256: `dbfd3b50644f2e14046110901d032986e829d2726de19b8aedbf3b1f7389f732`，
   实测全量 15s，顶层目录 `kubernetes-v1.36.2`，含 vendor/）；
   后备官方 codeload `https://codeload.github.com/kubernetes/kubernetes/tar.gz/refs/tags/v1.36.2`
   （sha256: `ffbc46612cf32ad08a3b606de064b63afc350ae1dd1a691e99b5cd127d716c26`，顶层目录
   `kubernetes-1.36.2`）。两者内容相同但 tar 元数据不同，sha256 不同，recipe 对两者都校验。
2. 解压（stdlib tarfile，剥离顶层目录；不用 conan `get()` —— CI 设
   `CONAN_REQUEST_TIMEOUT=300 + CONAN_RETRY=10`，单 URL 最坏 10x330s 重试可击穿 3600s 窗口）
3. 编译（版本号经 ldflags 注入，不依赖 git 元数据）:
   ```bash
   CGO_ENABLED=0 GOOS=linux GOARCH=arm64 GO111MODULE=on GOPROXY=off \
     GOFLAGS=-mod=vendor GOSANDBOX=off GOTOOLCHAIN=local \
     go build -trimpath \
     -ldflags="-w -s \
       -X k8s.io/component-base/version.gitVersion=v1.36.2 \
       -X k8s.io/component-base/version.gitCommit=unknown \
       -X k8s.io/component-base/version.gitTreeState=clean \
       -X k8s.io/component-base/version.buildDate=2026-09-23" \
     -o kubeadm ./cmd/kubeadm
   ```
4. package(): 拷贝 `kubeadm` 到 `bin/`、`LICENSE` 到 `licenses/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI 报 `go: not found` | CI worker 无预装 Go 工具链 | recipe 自举 Go 1.26.4（镜像列表下载 + sha256 校验），参考 adbtuifm/abbtr 已发布先例 |
| 2 | go1.26.4 工具链二进制在 OHOS 上 Permission denied | OHOS 对未签名 ELF 拒绝执行（E318） | 工具链全部 ELF（bin/go、gofmt、pkg/tool/*）binary-sign-tool 自签，签名后 `go version` 正常 |
| 3 | 链接阶段 `mapping output file failed: permission denied` | go linker 对输出文件做 RWX mmap，沙箱/默认 /tmp 受限 | 链接输出改放可写 workspace link-out 目录 + `GOSANDBOX=off` |
| 4 | go.mod 声明 go 1.26.0，低版本工具链触发 toolchain 自动下载 | Go toolchain 管理 + 网络限制 | 直接用 Go 1.26.4（>= 1.26.0）+ `GOTOOLCHAIN=local` 禁止切换下载 |
| 5 | 离线环境 go build 默认访问 GOPROXY | vendor 目录未被默认启用 | `GOFLAGS=-mod=vendor GOPROXY=off` 强制离线 vendor 编译 |
| 6 | gitee mirrors 对 python-requests UA 返回 HTML 拦截页 | gitee 仅对 curl 风格 UA 放行真实 tarball | recipe 有界下载器显式发 `User-Agent: curl/8.5.0`，gitee 作主源（实测 15s），codeload 作后备 |
| 7 | CI worker 无 curl，CI pre-download 全部秒败（Errno 2） | pre-download 依赖 curl 二进制 | recipe 自实现有界下载器（urllib）不依赖外部工具；CI pre-download 命中时走 file:// 直通校验解压 |
| 8 | conan get() 受 CI `CONAN_REQUEST_TIMEOUT=300 + CONAN_RETRY=10` 约束，单 URL 最坏 10x330s，可击穿默认 3600s 窗口 | conan get() 重试无界 + 源站慢 | recipe 自实现有界下载器（120s 超时 x 2/镜像），最坏下载 ~16min，默认窗口足够，不改框架 build_timeouts.txt |

## 源码修改

无源码修改，无需补丁。Go 项目在 OpenHarmony 上以 GOOS=linux GOARCH=arm64 原生编译。

## 依赖版本

- go/1.26.4（recipe 自举下载，非 conan registry 依赖）
- 其余依赖全部来自源码自带 vendor/ 目录，离线编译

## 验证结果

test_package 断言 `kubeadm version` 输出包含 ldflags 注入的 v1.36.2。
交叉构建（host 无法运行 OHOS 二进制）时退化为 ELF 魔数校验。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/kubeadm | 单二进制，静态链接（CGO_ENABLED=0），已自签 |

## 注意事项

- kubeadm 是纯 Go 项目，CGO_ENABLED=0 静态编译即可在 OpenHarmony 上运行
- kubernetes 归档 40MB + 工具链 64MB，最坏下载 ~16min（有界下载器），
  20 核设备本地实测完整 conan create 82s（编译本体 39s），默认 3600s 窗口足够，
  无需框架超时条目
- `kubeadm version` 在无集群环境下可独立运行，适合作为冒烟验证（L2）

---

**编译结束**: 2026-09-23
**最终状态**: built（CI #60613 通过：conan create + test_package，L0/L1 门禁通过）
