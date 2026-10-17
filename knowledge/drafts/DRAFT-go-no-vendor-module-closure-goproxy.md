# DRAFT — 无 vendor/ 的 Go 模块在 conan/OHOS CI 构建必须显式拉取模块闭包（GOPROXY+-mod=mod），否则 import 解析硬失败

状态：草稿（Builder 落稿，2026-09-23）；Exxx 编号由知识库主编定稿时分配。
申报域：依赖闭包（兼构建系统语义）；准入层级 L1（单库发现即可申报，Curator 判定 1.2）。
案例库：kubeaudit 0.22.2（首次权威 CI 前，真机探针实证）。

## 可复现症状与稳定错误签名

- 稳定签名（PROBE1 实测，40 行同型）：
  `pkg/k8s/types.go:4:2: module lookup disabled by GOPROXY=off`
  （internal/k8sinternal、internal/sarif、auditors/*、cmd/commands/* 各包逐 import 重复）
- 同族签名（GOPROXY 缺省或代理不可达时）：`cannot find module providing package ...`；
  go.sum 不完整时：`missing go.sum entry ...`。
- 触发条件：`go build` / `go test -c` 于 conan 配方 build() 内，源码树无 `vendor/`，
  CI worker `GOMODCACHE` 为空。

## 根因与最小复现（机理链）

1. Go 1.16+ 默认 `-mod=readonly`，且编译需要完整模块图（go 命令语义）。
2. conan 源码模型只含上游 tarball：上游未带 `vendor/`（Go 生态 vendor 可选且非默认，
   k8s 系依赖普遍无 vendor），CI worker `GOMODCACHE` 为空。
3. import 解析被迫发起模块查找；GOPROXY 缺省/`off` 或代理与 sumdb 不可达
   （中国网络访问 proxy.golang.org / sum.golang.org 受限）→ 第一个 import 处硬失败。
4. 归类：构建失败类阻塞；根因 = Go 模块解析语义 × conan 自足源码模型 × CI 新环境/
   中国网络，三重叠加。复发面由 Go 生态保证（vendor 非默认），任何后续无 vendor Go
   库同型。

最小复现（PROBE1，真机 2026-09-23，日志
`/storage/Users/currentUser/tmp/oh-device-porting-v2/curator-kubeaudit-probe/probe1-goproxy-off.log`）：
空 `GOMODCACHE` + `GOPROXY=off` 下 `go build ./cmd/`，40 行
`module lookup disabled by GOPROXY=off`，构建硬失败。

## 已尝试方案（含失败方案及结果）

| 方案 | 结果 |
|---|---|
| GOPROXY=off / 缺省直接 go build（PROBE1） | `module lookup disabled by GOPROXY=off` 40 行，硬失败（反模式，禁用） |
| `-mod=vendor` 而树内无 vendor/ | 无闭包可用，与 off 同型必失败（反模式，禁用） |
| GOPROXY=goproxy.cn,direct + GOSUMDB=sum.golang.google.cn（PROBE2/2B） | 从空缓存拉通 53 个模块、编译通过；GOTMPDIR/链接输出路由 go-workspace 后 PROBE2B-BUILD-OK（产物 45,443,989 字节）→ 采纳 |
| （相邻面，非本条）未路由 GOTMPDIR 直接在 /storage(HMDFS) 链接 | `link: mapping output file failed: permission denied` —— E124/E134/E166 已覆盖条目的活体再证，路由 go-workspace 后消除 |

## 最终方案、输入输出与真实验证

conan 配方 `build()` 内，构建产物之前显式拉取闭包：

```python
# 环境（generate()/build() 一致）
env["GOFLAGS"]   = "-mod=mod"
env["GOPROXY"]   = "https://goproxy.cn,direct"
env["GOSUMDB"]   = "sum.golang.google.cn"
env["GOTOOLCHAIN"] = "local"          # 防 go.mod 触发工具链自动下载
env["GOCACHE"] / env["GOMODCACHE"] / env["GOTMPDIR"] = 可写 go-workspace
# build() 序列
go mod download                                   # 闭包一次性拉取，日志可审计
go build -trimpath -mod=mod -ldflags "..." -o <workspace>/link-out/<bin> ./cmd
```

- 输入：上游 tarball（无 vendor/）+ 完整 go.sum（go.mod 同源）。
- 输出：GOMODCACHE 填充的模块闭包 + 静态链接产物（OHOS 上签名后可执行）。
- 真实验证：kubeaudit 0.22.2 首次权威 CI 全绿（conan create 内 `$ go mod download`
  见 `tmp/oh-device-porting-v2/kubeaudit-0.22.2-evidence/go-mod-download.log`；
  上游测试 21 包 379/379；L0-L5 pass）。PROBE2B 从空缓存拉通 53 模块
  （`tmp/oh-device-porting-v2/curator-kubeaudit-probe/`）。

## 自包含验证脚本（任何新 shell 可跑）

```zsh
# 前置：Go >= 1.22 工具链与上游源码包（以 kubeaudit 0.22.2 为例）
GO=/storage/Users/currentUser/usr/local/go/bin/go
TGZ=kubeaudit-0.22.2.tar.gz            # SHA256 90752d42c4d502ab6776af3358ae87a02d2893fc2bb7a0364d6c1fdcd8ff0570
V=/tmp/kubeaudit-goproxy-verify; W=<可写 go-workspace，如 /data/storage/el2/base/haps/entry/files/kubeaudit-conan-go/0.22.2>
rm -rf "$V" && mkdir -p "$V/src" "$V/empty-gomodcache" "$W/tmp" && tar -xzf "$TGZ" -C "$V/src"

# PROBE1（预期失败面：输出计数 > 0）
cd "$V/src/kubeaudit-0.22.2" && env GOTOOLCHAIN=local GOFLAGS=-mod=mod \
  GOMODCACHE="$V/empty-gomodcache" GOPROXY=off $GO build ./cmd/... 2>&1 \
  | grep -c "module lookup disabled by GOPROXY=off"

# PROBE2B（预期成功面：BUILD-OK 且产物为非空 ELF）
cd "$V/src/kubeaudit-0.22.2" && env CGO_ENABLED=0 GOOS=linux GOARCH=arm64 \
  GOTOOLCHAIN=local GOFLAGS=-mod=mod GOPROXY=https://goproxy.cn,direct \
  GOSUMDB=sum.golang.google.cn GOMODCACHE="$W/go-mod-cache" \
  GOCACHE="$W/go-build-cache" GOTMPDIR="$W/tmp" \
  $GO build -trimpath -mod=mod -o "$W/link-out/kubeaudit-verify" ./cmd \
  && echo PROBE2B-BUILD-OK
```

## 适用范围、反例、解除条件与风险

- 适用：任何无 `vendor/` 目录的 Go 模块在 OHOS conan CI 的 conan 配方构建。
- 反例：上游自带 `vendor/` 的库应沿用 `-mod=vendor` 全离线构建（先例
  kubeconform 0.7.0），不要引入网络依赖。
- 解除条件：上游未来附带 vendor/ 或 CI 机预置该模块闭包时，显式拉取步骤自动冗余
  （`go mod download` 幂等，保留无害）。
- 风险：构建期需要外网（goproxy.cn 可达性）；完全离线环境用 fallback（预
  `go mod vendor` 后 `-mod=vendor`，诚实权衡：把网络依赖前移固化进构建树，掩盖而非
  消除）。

## 方案空间（分层）

- **rec**（优先）：build() 内显式 `go mod download` + `GOFLAGS=-mod=mod` +
  `GOPROXY=https://goproxy.cn,direct` + `GOSUMDB=sum.golang.google.cn`（CN 镜像选择
  与 E250 的 SDK 下载先例对齐）；`GOTOOLCHAIN=local`。
- **fallback**：构建树内预 `go mod vendor` 再 `-mod=vendor`（离线兜底，见风险权衡）。
- **forbid**：① 无 vendor/ 时 `GOPROXY=off`（或缺省不可达代理）直接 go build；
  ② 树内无 vendor/ 而用 `-mod=vendor`。

## 知识库查重与新增价值

- Curator 查重（2026-09-23）：`grep -rn -i -e goproxy -e mod=mod -e mod=vendor -e
  "go mod download" -e mod=readonly knowledge/graph/ knowledge/drafts/` → 0 命中；
  Builder/Scout 检索 E124/E128/E134/E166/E250/E318 全为相邻面（SDK 自举、link mmap、
  测试 ELF 签名），build-chain-pitfalls.md 无 Go 条目，经验仓 grep 零命中。
- 诊断端价值：「module lookup disabled by GOPROXY=off」/「cannot find module」直接
  映射本条，免排障；修复端价值：配方 env+命令可直接套用（E250 背书 CN 镜像）。
- 非一次性补丁：配方层模式（rec+fallback+forbid 完整方案空间），适用于全部后续
  无 vendor Go 库（E250 工具链缺失之后 Go 生态第二常见阻塞面）。

## 挂钩与关系

- principles：P017（ELF 签名，运行/测试阶段相邻约束——拉取的闭包编译产物在 OHOS
  仍须签名后才能 execve）。
- similar_to：E250（CI 新环境缺失资源 → 显式拉取同族：Go SDK 自举）、E318（测试
  ELF 签名运行）、E124/E134/E166（链接落地 HMDFS 面）。

## 证据路径索引

- PROBE1 失败日志：`/storage/Users/currentUser/tmp/oh-device-porting-v2/curator-kubeaudit-probe/probe1-goproxy-off.log`
- PROBE2/2B 成功面：同目录 `kubeaudit-0.22.2/`、`kubeaudit-probe-bin`（45,443,989 字节）
- CI 正向证据：`/storage/Users/currentUser/tmp/oh-device-porting-v2/kubeaudit-0.22.2-evidence/{go-mod-download.log,upstream-go-test.log}`
- 配方实例：`archives/k/kubeaudit/0.22.2/conanfile.py`
- Curator 判定：`reports/curator/curation-report.md`（run kubeaudit-0.22.2）
