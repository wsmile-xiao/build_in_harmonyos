# k8sgpt 0.4.36 — OHOS aarch64 适配笔记

## TL;DR

- **结果**：`k8sgpt v0.4.36 (d33935a)` 纯 Go 交叉编译（CGO_ENABLED=0，Go 1.26.5 SDK 自举）在 OHOS aarch64 真机构建并运行成功；`conan create` 全量通过；状态 **built**（无 upload 步骤）。
- **源码合规（R39/PF5）**：conandata.yml 官方 GitHub 双端点 URL 列表（codeload 直链 + /archive/ 重定向，字节一致 sha256 相同）+ sha256 校验；conan 逐条回退，兼容 CI 镜像预下载（gh-proxy 对 github.com 域名自动注入）；产品代码零修改，唯一补丁仅触及 2 个上游测试文件（拨号目标与竞态等待），无 `__OHOS__` 宏。
- **R51 测试三步法**：57 文件 / 201 顶层 Test 函数；`go test -v -count=1 ./...` 实测 **363 PASS / 1 FAIL**（唯一失败为 gomonkey 运行时改码被 OHOS Seccomp W^X 阻断，平台硬限制，非缺陷回归）。
- **新知识（平台级，已沉淀 manifest.yaml）**：
  1. Go 1.26+ 二进制内嵌 `.codesign` 字面字符串 → 按内容判签名必误判，须无条件重签；
  2. 沙箱内 Go 进程 fork/exec 脚本文件被拒 → `go test -exec` wrapper 必须编译成 ELF；
  3. 自签名 ELF 不可读 `/etc/hosts` → Go 纯解析器查 `localhost` 直发 DNS → NXDOMAIN；
  4. gomonkey 依赖 mprotect(PROT_EXEC)，W^X 策略下不可用。

## 1. 环境证据（真机）

- 机器：aarch64 鸿蒙PC 真机；Python 3.12.9；Conan 2.29.1（OHOS 适配版）；clang 15.0.4
- 签名工具：`/data/service/hnp/bin/binary-sign-tool`（`sign -selfSign 1 ... -signAlg SHA256withECDSA`）+ `llvm-objcopy --remove-section .codesign`
- Go 工作区（非 HMDFS，E051/E046 规避）：`/data/storage/el2/base/haps/entry/files/k8sgpt-conan-go/0.4.36/`（GOCACHE/GOMODCACHE/TMPDIR/GOTMPDIR/link-out 全部重定向至此；配方 `OHOS_GO_WORKDIR` 默认即此路径）

## 2. 源码与版本（R37/R39）

- 上游：`k8sgpt-ai/k8sgpt` tag **v0.4.36**（tag commit `d33935a`，经 GitHub API 核实）
- 源码：`https://codeload.github.com/k8sgpt-ai/k8sgpt/tar.gz/refs/tags/v0.4.36`（备选 `https://github.com/k8sgpt-ai/k8sgpt/archive/refs/tags/v0.4.36.tar.gz`，双端点字节一致）
- sha256：`81b9fc2cb52ba44a3b80fe5d69cfcd43dd389ac29d5e2d46c14f9cfa6e2f87c2`（实测下载与 conandata 一致）
- go.mod：`go 1.26.3` + `toolchain go1.26.5` → 配方以 `GOTOOLCHAIN=local` + 自举 Go **1.26.5** SDK（golang.google.cn → mirrors.aliyun.com → dl.google.com 三级回退，sha256 双架构固定）
  - linux-arm64: `fe4789e92b1f33358680864bbe8704289e7bb5fc207d80623c308935bd696d49`
  - linux-amd64: `5c2c3b16caefa1d968a94c1daca04a7ca301a496d9b086e17ad77bb81393f053`

## 3. 构建命令（与上游 Makefile 对齐）

上游 Makefile L57（官方构建）：

```
go build -trimpath -ldflags "-s -w -X main.version=dev -X main.commit=$COMMIT -X main.date=$DATE"
```

配方等价执行（纯 Go，`CGO_ENABLED=0 GOOS=linux GOARCH=arm64`）：

```
go build -trimpath -ldflags "-s -w -X main.version=v0.4.36 -X main.commit=d33935a -X main.date=$(date +%FT%TZ)" -o <link-out>/k8sgpt .
```

真机实测：`go mod download`（goproxy.cn，1.8G 模块缓存）≈ 21s；全量编译 ≈ 68s；产物 114 MB（含 k8s client-go、helm、多 AI SDK）。

冒烟：

```
$ k8sgpt version
k8sgpt: v0.4.36 (d33935a), built at: 2026-10-02T04:36:28Z
```

## 4. R51 上游测试三步法

### 一步：清点
- `*_test.go`：**57 个文件**；顶层 `func Test*`：**201 个**（逐文件申报见 `test_package/MANIFEST.yml`）
- 上游 `make test` = `go test ./...`（无 -race；-race 需 cgo，与 CGO_ENABLED=0 冲突，上游也未使用）

### 二步：实测（原样 + 必要基础设施补丁后）
命令：`go test -v -count=1 -exec <wrapper-elf> ./...`

| 指标 | 数值 |
|---|---|
| --- PASS | **363** |
| --- FAIL | **1**（`pkg/analysis.TestVerbose_NewAnalysisWithoutExplain`） |
| --- SKIP | 0 |
| 通过率 | 363/364 ≈ **99.7%** |

### 三步：唯一失败项根因（逐项说明）

`TestVerbose_NewAnalysisWithoutExplain`（pkg/analysis/analysis_test.go:426）：
- 失败机制：`gomonkey/v2@v2.13.0 modifyBinary` → `panic: invalid argument`
- 根因：gomonkey 通过 `mprotect(PROT_EXEC)` 改写函数机器码实现运行时打桩；OHOS Seccomp W^X 策略禁止对数据页加执行权限，`mprotect` 返回 EINVAL
- 定性：**平台硬限制**（沙箱内存保护策略），非 k8sgpt 缺陷、非适配缺陷；gomonkey 类用例在任何 OHOS 沙箱内均无法执行（与 ain 条目 E 系列 Seccomp 限制同族）
- 该测试不涉及业务逻辑回归：同包其余分析器测试（含 sanitize/AI 结果合并等）全部通过

### 补丁说明（仅测试基础设施，不改断言语义）

`patches/0001-pkg-cache-interplex_based_test.go.patch + 0002-pkg-server-server_test.go.patch`：
1. `pkg/server/server_test.go`、`pkg/cache/interplex_based_test.go`：拨号目标 `"localhost:..."` → `"127.0.0.1:..."`（4+1 处）
   - 根因：OHOS 沙箱按二进制标签做文件访问控制，**自签名 ELF 读 `/etc/hosts`（符号链接 → /data/service/el1/public/...）返回 EACCES**（系统签名的 cat 可读）；Go 纯解析器（CGO_ENABLED=0）hosts 查找失败后直接走 DNS（114.114.114.114/8.8.8.8），`localhost` 并非公网域名 → NXDOMAIN。证据：`GODEBUG=netdns=2` 下 `hostLookupOrder(localhost) = files,dns` 且 `os.ReadFile("/etc/hosts") → permission denied`（cat 同文件可读）
2. `interplex_based_test.go`：mock gRPC 服务端启动后增加就绪探活（最多 10s，失败语义保持 `t.Fatalf`）
   - 根因：上游在 `go func(){net.Listen...}` 后立即拨号且 select/default 不等待——**上游自带竞态**；真机实测未打补丁时 4/5 通过、1/5 connection refused（TestLoad 反而收到服务端响应，证明服务端迟于首拨号就绪）；打补丁后 10/10 稳定通过

## 5. 平台差异与规避（适配核心）

| # | 平台约束 | 规避 | 记录 |
|---|---|---|---|
| 1 | 所有 fork/exec 的 ELF 必须带 `.codesign` 段，未签名产物 exec 即 EACCES | SDK 全部 10 个 ELF（go/gofmt/pkg/tool/linux_*/*）+ 主二进制 + `.test` 二进制统一 `binary-sign-tool` 自签 | E128/E250/E318 |
| 2 | **Go 1.26+ 二进制内嵌 `.codesign` 字面字符串**（linker 元数据），按内容 grep 判断"已签名"会把全部未签名 Go 二进制误判跳过（Go 1.24 无此字符串，ali/ain 旧法失效） | 配方**无条件** objcopy 剥段 + 重签（签名幂等，永安全）；`.ohos-signed` marker 防重复遍历 | 本条目新沉淀 |
| 3 | 沙箱内 Go 进程 fork/exec **脚本文件**（shebang）被 EACCES（bash 直接执行同脚本可行；fork/exec 签名 ELF 正常——go 工具链自身 spawn compile/link 即证明） | `go test -exec` wrapper 改为 **C 源码内嵌配方 → clang 编译 ELF → 自签**；逻辑与 ali shell wrapper 等价（重签测试二进制后 exec） | 本条目新沉淀 |
| 4 | Go linker 在 HMDFS 上 mmap 失败 | 链接输出进 `link-out`（/data 非 HMDFS）；GOCACHE/GOMODCACHE/TMPDIR/GOTMPDIR 同步重定向 | E051/E046 |
| 5 | `/tmp` 只读 | TMPDIR 兼容处理（test.sh 多级回退） | 常规 |

## 6. test_package（R28/L0e）

- `test.sh`：`k8sgpt version`（严格 grep v0.4.36）/ `--help` / 无参数 Usage 提示，3 项冒烟，emit `HMBS_TEST_PACKAGE_RESULT`
- `conanfile.py`：显式 test_type + 每次运行重发 `HMBS_UPSTREAM_TEST_RESULT`（缓存命中时从包内 `res/hmbs_upstream.json` 复原，防证据门禁 discovered=0）
- `MANIFEST.yml`：57 个上游测试文件逐文件申报 + assertion_count 364

## 7. CI 检视意见修复记录

- **test_package/test.sh:33-36（Medium，已采纳）**：原 `k8sgpt --help ... && echo OK` / `k8sgpt ... | grep -q Usage: && echo OK` 依赖 `set -e`，但 `&&` 链中非末位命令失败被 errexit 豁免（与版本检查行的 `|| { FAILED; exit 1; }` 守卫风格不一致），检查失败时脚本仍以 0 退出。修复：两条检查均补 `|| { echo "... check FAILED"; exit 1; }` 兜底。修复后真机验证：A(--help 失败)→exit 1、B(Usage 缺失)→exit 1、C(全正常)→exit 0+marker；conan-verify G2 复验 3/3 PASS。
- **G0 configure exit 127（结构性不适用，非阻塞）**：G0 干净构建验证面向 autotools 项目（./configure），Go 项目无此脚本（exit 127 = ./configure 不存在）。clean_verify.py 的"预期失败"白名单依赖 conanfile 含 replace_in_file，Go 配方无该项故报硬失败；管线继续执行，conan-verify G2（conan create 全链路）为 conan 配方的等价权威验证。ali/ain/aliyun-cli 等 Go 先例同样无 replace_in_file。
- **submit 就绪预检 3 项**：test-report.md 已按真实数据补齐（reports/test-report.md，本地工件不入库，同 .ci-result.json）；.staging-verified 按管线自愈指引补建（dispatch 状态机 built 标记）；packaging/ 对 conan 交付的 Go 应用不适用（CI 只读 conandata/conanfile/test_package/patches/commands.json，发布走 conan upload，无 hnp 打包环节；ali 等先例均无）。

## 8. 交付物清单

```
archives/k/k8sgpt/
├── commands.json                        # R38 软件级命令注册
└── 0.4.36/
    ├── conanfile.py                     # Go 自举 + 无条件签名 + ELF test wrapper + HMBS 标记
    ├── conandata.yml                    # 官方源 + sha256 + 测试基础设施补丁
    ├── manifest.yaml                    # built + 知识沉淀（5 条）
    ├── notes.md                         # 本文件
    ├── patches/0001-pkg-cache-interplex_based_test.go.patch + 0002-pkg-server-server_test.go.patch
    └── test_package/{conanfile.py,test.sh,MANIFEST.yml}
```

## 9. 遗留事项

- gomonkey 用例（1/364）为平台硬限制，随上游更新若移除 gomonkey 依赖即可 100%；不建议为绕过而修改产品测试策略（mock 方式属上游测试设计）
- `auth analyze` 等需真实 K8s 集群/AI 后端的功能不在冒烟范围（无集群环境）；核心 CLI/配置/分析引擎单元测试已全量覆盖
---

**编译结束**: 2026-10-03 15:19
**最终状态**: built
