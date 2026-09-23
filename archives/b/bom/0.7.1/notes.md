# bom v0.7.1 适配笔记

## 基本信息

- 上游: https://github.com/kubernetes-sigs/bom （kubernetes-sigs/bom）
- 版本: v0.7.1
- 许可证: Apache-2.0
- 构建日期: 2026-09-06
- 工具链: go1.25.12 linux/arm64，配方内自举（chkbit/caddy 既定模式）。固定 URL
  （golang.google.cn/dl 优先、dl.google.com 兜底）+ 固定 SHA256
  （8b5884aef89600aef5b0b051fb971f11f49bb996521e911f30f02a66884f7bd2，设备侧下载复验一致），
  下载到沙箱可写工作区 go-sdk/，go/gofmt/pkg/tool/* 逐 ELF binary-sign-tool 自签后使用。
  本地/开发环境可经 GO、GOROOT、~/usr/local/go/bin/go 或 PATH 提供已装 go（>=1.24 即可），
  跳过下载。官方 CI 无任何可发现的 go（沙箱 PATH 不含 go；用户目录
  ~/usr/local/go/bin/go 权限 rwxr-x---，uid 100 不可执行），配方内自举是唯一可靠供给路径。
- 模块代理: goproxy.cn（GOSUMDB=sum.golang.google.cn，GOTOOLCHAIN=local，模块校验经代理透明完成）
- 归档: https://github.com/kubernetes-sigs/bom/archive/refs/tags/v0.7.1.tar.gz
  SHA256=3893c25e7ea3b625c7c7c7d2f89cdd53fe6d8d43fac8c587a8f81c920498cca2（设备侧复验一致）

## 构建方式

纯 Go（无 cgo），conanfile.py generate() 生成 bom_go_env 环境脚本，build() 执行
`go build ./cmd/bom`：

```bash
CGO_ENABLED=0 GOTOOLCHAIN=local GOPROXY=https://goproxy.cn,... go build -o bom ./cmd/bom
```

GOCACHE/GOMODCACHE/GOTMPDIR/TMPDIR 统一置于沙箱可写工作区（OHOS_GO_WORKDIR 可覆盖，
默认 /data/storage/el2/base/haps/entry/files/bom-conan-go，chkbit/caddy 先例）；
OHOS 下链接产物先写入工作区 link-out/，自签后拷回构建目录，测试 ELF 置于工作区
test-out/（避开 conan 构建目录受限路径）。

go.mod 声明 `go 1.24.0`，无独立 toolchain 行，go1.25.12 + GOTOOLCHAIN=local
直接满足，未打任何 patch。

## ELF 签名（E318）

HarmonyOS 拒绝执行未签名 ELF（实测 /data/cache 与 /storage tmpfs 均 RC=126）。
设备 clang 自动为产物附加 .codesign，Go 链接器不会。因此 conanfile build() 对
bom 主程序、每个 go test -c 产物以及自举 SDK 内的 go/gofmt/pkg-tool ELF 执行
binary-sign-tool 自签：

```bash
binary-sign-tool sign -inFile X -outFile X.signed -selfSign 1
mv X.signed X && chmod 755 X
```

签名后全部可正常执行（binary-sign-tool 位于 /data/service/hnp/bin，已纳入
conan profile buildenv PATH，配方按 PATH → generators 目录物化的 buildenv PATH →
常规工具目录顺序自动探测）。

## 上游测试结果（真机实测）

按 E318 逐包编译-签名-运行（-test.count=1），测试日志留存于移植环境临时证据目录：

| 包 | 结果 |
|----|------|
| pkg/license | PASS（9 用例） |
| pkg/osinfo | PASS（14 用例） |
| pkg/provenance | PASS（14 用例） |
| pkg/query | PASS（5 用例） |
| pkg/spdx | 31 用例 PASS，3 个网络依赖用例跳过 |

### 网络依赖用例（NOT_RUN，环境阻塞非移植缺陷）

- TestPullImagesToArchive（spdx_unit_test.go）：拉取
  registry.k8s.io 镜像经 asia-east1-docker.pkg.dev，dial tcp i/o timeout
- TestGetImageReferences（spdx_unit_test.go）：同上端点，dial tcp i/o timeout
- TestToSPDXPackage（gomod_test.go）：x/tools/go/vcs 解析 golang.org/x/term 的
  ?go-get=1 元数据需直连 golang.org，设备不可达（unrecognized import path）

设备仅可达国内代理（goproxy.cn 正常），无可信容器仓库/ vanity import 代理，
穷尽替代后按 -test.skip 显式声明并在 CI 日志保留证据。跳过命令：

```bash
./spdx.test -test.skip='^(TestPullImagesToArchive|TestGetImageReferences|TestToSPDXPackage)$'
```

## 功能验证

- `bom version` 正常输出（GitVersion: devel，tarball 构建无 git tag，预期）
- `bom generate -f <file> -o out.spdx` 生成合法 SPDX-2.3 文档（真机验证）
- test_package 消费者测试：bom version + bom generate 生成并校验 SPDX 文档

## 已知限制

- GitVersion 显示 devel（需 mage/git 注入 ldflags，tarball 构建无此信息，不影响功能）
- 三个网络依赖测试在离线/受控网络环境不可运行（见上）
