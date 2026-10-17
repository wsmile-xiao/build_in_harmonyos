# kubo-migration 0.42.0 适配笔记

## 软件定义

`kubo-migration` 是 Alpine Linux kubo 0.42.0 包的 `kubo-migration` 子包，对应上游
[ipfs/fs-repo-migrations](https://github.com/ipfs/fs-repo-migrations) 仓库 tag
`fs-repo-15-to-16/v1.0.0`（仓库内 `fs-repo-15-to-16/` 子目录）中的 IPFS repo
15→16 迁移工具（fs-repo-15-to-16）。它把 IPFS 仓库从 repo v15 迁移到 v16：
在 `config` 的 `.Addresses`（Swarm/Announce/AppendAnnounce/NoAnnounce）中为每个
`/udp/<port>/quic-v1` 追加同端口的 `/udp/<port>/webrtc-direct` 监听，同时保留
`config.15-to-16.bak` 备份支持回退（`-revert`）。这是纯 Go CLI，无 C/C++ 代码。

- 上游源码（唯一权威）：`https://github.com/ipfs/fs-repo-migrations/archive/refs/tags/fs-repo-15-to-16/v1.0.0.tar.gz`
  （tag 名含斜杠，GitHub archive 路径按原样编码；git clone 等价命令
  `git clone --branch fs-repo-15-to-16/v1.0.0 https://github.com/ipfs/fs-repo-migrations`）
- 源码 sha256：`a1eab2531302921eb817d13f19febbdef45596722a1a70968ff2c5133ffec9ef`
  （GitHub archive URL 与 codeload URL 下载字节一致，均实测验证）
- 仓库结构：Makefile、go.mod（module `github.com/ipfs/fs-repo-migrations/fs-repo-15-to-16`,
  go 1.22）、go.sum、main.go、atomicfile/、migration/、test-e2e/（test.sh +
  repo-v15/ + repo-v16/ fixtures）、vendor/

## 编译环境

- 构建系统: go（`go build`，与 Alpine APKBUILD 一致）
- 编译日期: 2026-09-21
- 编译器: Go 1.26.3（本机工具链，linux/arm64）
- 工具链: GOTOOLCHAIN=local
- 状态: built

## 编译步骤

```bash
export GOTOOLCHAIN=local CGO_ENABLED=0 GOOS=linux GOARCH=arm64
export PATH=<go 工具链 bin 目录>:$PATH
# GOCACHE/TMPDIR 与链接输出放到可写本地文件系统（避开 HMDFS mmap 限制）：
export GOCACHE=/data/storage/el2/base/haps/entry/files/go/fsrm/cache
export TMPDIR=/data/storage/el2/base/haps/entry/files/go/fsrm/tmp

cd fs-repo-15-to-16
go build -mod=vendor -trimpath -o fs-repo-15-to-16 .
# OHOS 上签名后才能执行：
llvm-objcopy --remove-section .codesign fs-repo-15-to-16 2>/dev/null || true
binary-sign-tool sign -selfSign 1 -inFile fs-repo-15-to-16 \
  -outFile fs-repo-15-to-16 -signAlg SHA256withECDSA
```

产物：单个静态可执行文件 `fs-repo-15-to-16`（arm64, 静态, ~3.7MB）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `go build` 报 `link: mapping output file failed: permission denied` | OHOS/HMDFS 上 Go linker 对输出文件 mmap 失败 | 链接输出放到可写本地文件系统（`/data/storage/el2/base/...`，非 HMDFS 的 userdata 分区），再复制回目标目录（与 abbtr/aliae/kubo 同款方案） |
| 2 | 运行未签名 ELF 报 `Permission denied` | OHOS 只执行带 OHOS 签名的 ELF（E046 同源限制） | 用 `binary-sign-tool`（`/data/service/hnp/bin/binary-sign-tool`）签名最终产物；go 工具链本身（已带签名）可直接执行 |
| 3 | 上游 e2e `test.sh` 用 `go run ..` 驱动，OHOS 上报 `fork/exec ... permission denied` | `go run` 生成的临时 ELF 未签名，OHOS 拒绝 exec | 不改源码；test_package 用已构建+已签名的安装二进制执行同语义测试（复制 repo-v15 → 正向迁移 → diff repo-v16 → 回退 → diff repo-v15） |

## 源码修改（patch）

**无需修改源码**。fs-repo-15-to-16 是纯 Go 应用：go.mod 声明 `go 1.22`，
与本地 Go 1.26.3 完全兼容（GOTOOLCHAIN=local 不触发工具链下载）；依赖
`github.com/ipfs/fs-repo-migrations/tools` 已完整 vendor；无平台相关 C 代码。
因此 `patches_applied: []`，不生成 patch 文件。

## 依赖版本

- Go: 1.26.3（linux/arm64）
- 目标: HarmonyOS PC (aarch64)，CGO_ENABLED=0 纯静态编译
- Go 模块依赖: `github.com/ipfs/fs-repo-migrations/tools v0.0.0-20211209222258-754a2dcb82ea`
  （已 vendor，构建离线，无 GOPROXY 依赖）

## R51 上游测试三步法申报表

### ① 适配前清点上游测试数量

| 测试类型 | 位置/命令 | 数量 |
|----------|-----------|------|
| Go 单元测试 | `go test ./...`（包 `.` / `atomicfile` / `migration`） | **0 用例**（3 个包均无 `*_test.go`，实测输出 `[no test files]`） |
| e2e 集成测试 | `test-e2e/test.sh`（Makefile `make test` 调它） | **1 个脚本**（含 2 个 diff 断言：正向 diff repo-v16 + 回退 diff repo-v15，外加 version 文件断言） |

> 清点依据：`find . -name "*_test.go"` 在 fs-repo-15-to-16 目录下无任何结果；
> `test-e2e/` 下仅有 `test.sh` + `repo-v15/` + `repo-v16/` fixtures。

### ② 实际运行上游测试

| 命令 | 运行方式 | 结果 |
|------|----------|------|
| `go test ./...` | 本地 Go 1.26.3 直接运行 | **0/0 通过**（exit 0，三个包均 `[no test files]`） |
| `test-e2e/test.sh` | 上游原样运行（`go run ..` 驱动） | **失败 1 次**：`fork/exec .../exe/fs-repo-15-to-16: permission denied` —— `go run` 生成的临时 ELF 未签名，OHOS 拒绝 exec（平台限制） |
| `test-e2e/test.sh`（适配运行） | 用已构建+已签名的二进制替换 `go run ..`，测试逻辑与上游逐行一致 | **1/1 通过**（2/2 diff 断言 + 2/2 version 断言全过，见下方实测日志） |

适配方式说明：上游脚本唯一差异是把 `go run ..` 换成已安装的 `fs-repo-15-to-16`
二进制；`cp -r repo-v15 repo-test`、`diff -r repo-v16 repo-test`、`-revert`、
`diff -r repo-v15 repo-test` 全部保留。这是 OHOS 上执行 Go 测试二进制的既定做法
（同 aliae/murex 的 `go test -exec` 签名 wrapper 思路），非跳过测试。

适配运行实测日志（摘要）：

```
Migration 15 to 16
applying 15-to-16 repo migration
  - verifying version is '15'
> Upgrading config to new format
updated version file
Migration 15 to 16 succeeded
diff -r repo-v16 repo-test      # 无差异输出 = 通过
Revert 16 to 15
reverting migration
lowered version number to 15
diff -r repo-v15 repo-test      # 无差异输出 = 通过
E2E_RC=0
```

### ③ 实测通过率

- Go 单元测试：N=0，实测通过 N′=0，通过率 100%（上游本就无单测，非跳过）
- e2e 测试：N=1，实测通过 N′=1（适配运行），通过率 **1/1 = 100%**
- 声明：**通过率 100%**；无因平台原因未跑、也无占位符。

## 本地验证（conan）

- `conan create .`（默认 profile os=OHOS/armv8）：构建成功
- `conan create` 自动触发 test_package：`-help` 冒烟 + 正向 15→16 迁移
  （version=16 + diff repo-v16）+ 回退（version=15 + diff repo-v15），全部通过
- 详细证据见 `conan create` 输出（`test_package` 阶段 `ALL TESTS PASSED`）

## 交付物

| 文件 | 说明 |
|------|------|
| `archives/k/kubo-migration/0.42.0/conanfile.py` | Conan 配方（Go 应用，OHOS 适配：本地文件系统链接 + ELF 签名） |
| `archives/k/kubo-migration/0.42.0/conandata.yml` | 官方源码 URL + sha256 + go 工具链兜底下载 |
| `archives/k/kubo-migration/0.42.0/test_package/` | 真实执行迁移的 test_package（含上游 fixtures） |
| `archives/k/kubo-migration/0.42.0/manifest.yaml` | 版本编译元数据 |
| `archives/k/kubo-migration/0.42.0/notes.md` | 本文档 |
| `archives/k/kubo-migration/manifest.yaml` / `README.md` / `commands.json` | 软件级元数据（R38 commands.json） |

## 注意事项

- 二进制名 `fs-repo-15-to-16`（与 Alpine `kubo-migration` 子包一致），不是
  `kubo-migration`。
- `-path` 为必选参数（迁移/回退都要指定 repo 路径）；`-help` 可查看全部选项
  （`-f` 强制、`-revert` 回退、`-verbose` 详细日志、`-no-revert`）。
- OHOS 上 `binary-sign-tool` 签名是执行的前提；conan 配方已内置签名逻辑。
- 上游 tag 名含斜杠 `fs-repo-15-to-16/v1.0.0`，源码 URL 按原样编码即可（GitHub
  会自动 302 到 codeload，字节一致）。
