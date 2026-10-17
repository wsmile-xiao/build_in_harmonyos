# OHOS 上自举的 Go 工具链自身 ELF 必须批量自签后才能执行 go build

> **状态**: 草稿（未审核、未合入正式知识库）
> **来源事件**: kubeadm 1.36.2 适配（PR #12137），k8s.io/kubernetes cmd/kubeadm
> **KV**: [DRAFT-kubeadm-go-toolchain-sign.kv](DRAFT-kubeadm-go-toolchain-sign.kv)

## 问题面

CI worker 无预装 Go（`go: not found`），按 E250 的 `download-go-sdk` 方案在
recipe 内 `get()` 下载 Go SDK 后，直接调用仍失败：

```
sh: /…/go-sdk/go/bin/go: Permission denied      # exit 126
```

根因：OHOS 内核拒绝加载**未签名 ELF**。Go SDK 官方 tarball 内
`bin/go`、`bin/gofmt` 及 `pkg/tool/linux_arm64/*`（kubeadm 实测共 10 个 ELF）
全部是未签名静态 ELF。E250 方案止于"下载 + 设 GOROOT/PATH"，E318 只签
go test 产物——**工具链本体的签名环节两处都缺**。

## 解决方案（完整自举链路）

1. **下载**：`get()` 镜像列表（先 `golang.google.cn`，后备 `dl.google.com`），
   sha256 校验。注意 conan 2.29.1 无 `conan.tools.go`、无 `unpack()`，
   用 `conan.tools.files.get()` 即可；codeload/gitee 类镜像对
   python-requests UA 可能返回 HTML 拦截页，dl.google.com 对任意 UA 返回
   真实 tarball（实测 go1.26.4.linux-arm64.tar.gz 63,740,285 B 通过校验）。
2. **批量自签**：对工具链全部 ELF（ELF 魔数判定 + 无 `.codesign`/`.note.ohos`
   段才签）逐个 `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA`，
   签后 `chmod 755`；`.ohos-signed` marker 避免重入时重复签名。
3. **校验**：签名后 `go version` 正常（实测 `go1.26.4 linux/arm64`），
   再进入 build。

## 环境变量面（与签名同等必要）

| 变量 | 值 | 原因 |
|------|-----|------|
| CGO_ENABLED | 0 | 静态链接，OHOS 上无需 cgo |
| GOOS / GOARCH | linux / arm64 | OHOS 目标映射 |
| GOPROXY / GOFLAGS | off / -mod=vendor | 源码自带 vendor/ 时离线编译 |
| GOTOOLCHAIN | local | go.mod 要求 go >= 1.26.0，低版本会触发 toolchain 自动下载 |
| GOSANDBOX | off | 关闭 go 沙箱 |
| TMPDIR/GOTMPDIR/GOCACHE/GOMODCACHE | 可写 workspace | /tmp 只读；HMDFS fallocate EACCES（E523） |

链接输出文件同样放可写 workspace 目录（linker 对输出文件做 RWX mmap，
E523 同签名）。

## 禁止策略

- ❌ `which go or "go"` 静默回退：掩盖自举缺失，报 "go: not found" 误导排查
- ❌ 只下载不签名：E250 方案不完整之处，自举链路断在第一步

## 实测证据

- arm64 工具链 10 个 ELF 自签后 `go version` → `go1.26.4 linux/arm64`
- 小规模 go build（go mod init + vendor 全链路 compile+link）通过
- 参考先例：adbtuifm 0.5.8 / abbtr 1.0.4（同模式，published）

## 关系

- 上游: E250（工具链缺失 → 下载，本稿补签名环节）
- 相似: E318（测试产物签名）、E523（linker fallocate/RWX）、E128
