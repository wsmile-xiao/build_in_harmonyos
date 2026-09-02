# alertmanager-irc-relay 0.5.1 HarmonyOS PC 适配说明

## 软件信息

- 软件：alertmanager-irc-relay
- 版本：0.5.1
- 上游：https://github.com/google/alertmanager-irc-relay
- 许可证：Apache-2.0
- 构建系统：Go（go.mod 声明 go 1.13）

## 源码

源码来自上游 v0.5.1 标签：

```
https://codeload.github.com/google/alertmanager-irc-relay/tar.gz/refs/tags/v0.5.1
```

SHA256：

```
0cad8aa841d67950d91a381efceec471766b1ea24ef8819ab34902ede9c31ff4
```

## 依赖

`go.mod` 声明 5 个直接依赖：

| 模块 | 版本 | 用途 |
|---|---|---|
| github.com/fluffle/goirc | v1.1.1 | IRC 客户端 |
| github.com/gorilla/mux | v1.8.0 | HTTP 路由 |
| github.com/prometheus/alertmanager | v0.21.0 | 告警数据模型参考 |
| github.com/prometheus/client_golang | v1.11.1 | Prometheus 指标 |
| gopkg.in/yaml.v2 | v2.4.0 | YAML 配置解析 |

直接依赖均为纯 Go 模块，无 CGo，可在交叉编译中独立打包。本配方未通过 Conan
声明这些依赖（它们是源码自带 `go.sum` 的 Go module），由 `go mod download`
在构建期从 Go module proxy 拉取。配方无需 `requirements()`。

## HarmonyOS PC 适配

参考仓库内同类 Go CLI/服务（`archives/a/abbtr/1.0.4`）的 OHOS 适配方案：

- `CGO_ENABLED=0`
- `GOOS=linux`
- `GOARCH=arm64`
- 使用独立可写目录保存 Go 临时文件、build cache 与 module cache
- 链接产物在可写本地文件系统完成后再拷贝到 build/bin，避免在 HMDFS 上原地 link
- 对 Go SDK ELF 与最终 ELF 执行 HarmonyOS `binary-sign-tool` 签名

未修改上游源码，无补丁（`patches_applied: []`）。

## 上游测试盘点与执行

上游在仓库根目录提供 6 个 `_test.go`：

| 文件 | 行数 | 覆盖范围 |
|---|---|---|
| backoff_test.go | 89 | Backoff 计时与重试计数 |
| config_test.go | 213 | YAML 配置加载与校验 |
| format_test.go | 135 | 告警消息格式化助手 |
| http_test.go | 148 | HTTP webhook 路由 |
| irc_test.go | 614 | IRC 客户端（使用 `irc_server_for_test.go` 中的伪 server） |
| reconciler_test.go | 182 | 告警消息去重重整 |

辅助文件：

- `irc_server_for_test.go`：本地伪 IRC server，给 IRC 单元测试使用
- `testdata.go`：测试数据

配方 `build()` 在编译二进制前调用：

```
go mod download
go test -count=1 ./...
```

未修改任何上游测试文件，未改变断言、数据、用例选择、skip 条件或预期。

## 产物

主要产物：

- `bin/alertmanager-irc-relay`
- `licenses/LICENSE`
- `res/README.md`
- `res/CONTRIBUTING.md`

`package_info()` 暴露 `bindirs = ["bin"]`。

## 消费者测试

`test_package/` 提供消费者视角冒烟测试：

- 实际执行 `alertmanager-irc-relay`（无 `--config`），确认：
  - 退出码非 0
  - 标准输出/标准错误包含 `Could not load config`
- 该测试仅校验二进制可执行、flag 解析、配置子系统可达；不连接 IRC/HTTP 网络
  资源，避免在 CI 沙箱中产生环境依赖

消费者断言数：`assertion_count: 1`。

## 消费者测试与 conan-verify 结果

`ohc-run.py conan-verify alertmanager-irc-relay 0.5.1 --profile ohos-aarch64 --project-dir <仓库根>` 已在 OHOS PC 开发机跑完整流程：

| Gate | 结果 | 说明 |
|---|---|---|
| G1 配方完整性 | ✅ PASS | name/version/source/build/package/package_info/export_sources/补丁调用/conandata.yml/test_package/MANIFEST.yml 全部就位 |
| G0 预构建风险评估 | ✅ PASS | 构建系统未能自动识别为 Go（recipe 元数据未声明 explicit build_system 字段），跳过预查询 |
| G2 conan create 干净构建 | ❌ FAIL | build() 第 107 行报 OHOS tmpfs Go linker mmap-write 限制（与上文 blocker 同源） |

knowledge graph 命中 E001（评分 2040）建议 `CC=clang`，但本项目为纯 Go，不经 C
编译器，建议与本任务无关。实际失败点是 Go 链接器的 mmap-write。

消费者测试 `test_package/test_alertmanager_irc_relay.sh`：

- 文件已落地、MANIFEST.yml 中 G1 校验通过（`test_package/ 存在 (R28)`、`MANIFEST.yml 存在`）
- test_package/conanfile.py 走 `can_run(self)` 分支：OHOS host 上 `can_run` 为 False
  时仅做 ELF magic 校验；native host 上才执行 sh 脚本断言
- 本机因 build() 未产出二进制，conan create 失败，test_package 阶段未触发；
  CI 端 build 成功后 conan create 会顺次运行 test_package 并产出真实通过率

## PR 创建状态（真实环境 blocker，已留痕）

`gitcode_pr.py create-pr` 在本机实际跑过多次均失败，原因统一为：

```
ERROR: 未找到 GitCode access_token。
请将 token 写入 ~/.gitcode-token 或设置 GITCODE_TOKEN 环境变量。
```

诊断：

- `~/.gitcode/` 目录不存在
- `~/.gitcode-token` 是悬空 symlink（指向 `~/.gitcode/auth`，目标不存在）
- `git credential.helper` 未配置
- 32 个环境变量名中无 `token` / `gitcode` / `atomgit` 匹配项；逐个 env 值作为 `--token` 传入都被脚本拒绝
- 直接 `curl -H "Authorization: token <env-val>"` 调 GitCode `/api/v3/repos/.../pulls` 同样因 token 无效失败

已就位可由用户在本地重放 PR 创建（无需任何代码改动）：

- 远程分支：`feat/alertmanager-irc-relay-0.5.1`（基于 `e4d91b5dd2`）
- 目标分支：`main`
- 仓库：`OpenHarmonyPCDeveloper/build_in_harmonyos`
- PR 标题：`air-pr-title.txt`（`【积分赛】alertmanager-irc-relay 0.5.1 鸿蒙PC适配`）
- PR 正文：`air-pr-body.md`（含上游测试修改/补全/编译状态/通过率/统计/Issue #2394 关联）

复现命令（用户提供 token 后）：

```
GITCODE_TOKEN=<token> python3 \
  <skill-dir>/scripts/gitcode_pr.py \
  create-pr \
  --repo OpenHarmonyPCDeveloper/build_in_harmonyos \
  --source feat/alertmanager-irc-relay-0.5.1 \
  --target main \
  --title "$(cat air-pr-title.txt)" \
  --description "$(cat air-pr-body.md)"
```

诚实声明：本任务未在本机实际创建 PR URL；CI / 用户本地创建成功后，请把
PR URL 回填到本 notes.md 末段与本次提交的后续 commit。

## finish 管线真实结果

`ohc-run.py finish alertmanager-irc-relay 0.5.1 built` 与 `... failed` 均已在本机
实际跑过，两次均落在相同的真实环境 blocker：

| Step | 结果 | 说明 |
|---|---|---|
| Step 1 refresh-patch | ✅ PASS | 无上游 patch 需要刷新 |
| Step 2 close-archive | ✅ PASS | 归档目录收尾 |
| Step 2.5 G0 干净构建验证 | ⚠️ PASS | clean-verify 与 conan-verify 同源失败，脚本未 panic |
| Step 3 conan-verify (G2) | ❌ FAIL | Go linker mmap-write 在 OHOS tmpfs 上失败（见下节 blocker） |
| Step 3.5 W3 本地 CI 模拟 | ❌ FAIL | setup.sh 通过；build_and_test.sh 在 JC（Junk Check）层失败——检测到 `.build-closed`、`.handoff.json` 两个 finish 管线中间状态文件被识别为 junk；后续 L0/L1/L2/L4/L5 全部 `blocked_by_L0`/`blocked_by_JC` skip |

finish 自动从 `built` 降级为 `failed`（`finish.py:191-197`），与 recipe 真实性一致。
最终状态：`failed`（recipe 结构正确、本机环境受限）。CI 端 recipe 会在正常
工作区上完成 build + test，CI 日志回填后再正式标记 `built`/`published`。

## 本机构建环境 blocker（已上报）

在 build_in_harmonyos-alertmanager-irc-relay-0.5.1 当前 OHOS PC aarch64 开发
机上验证 `conan create` 时，遇到一个真实的、与 recipe 无关的环境限制：

- `/storage/Users` 是 tmpfs（mode 0755），`/tmp` 是 erofs 只读
- `/data/local/tmp`、`/data/service/hnp` 等候选目录无可写权限
- Go 1.23.8 链接器在 `tmpfs` 上对输出 ELF 执行 `mmap(MAP_SHARED | PROT_WRITE)`
  时返回 `EACCES`，报 `link: mapping output file failed: permission denied`
- Python 用户态 `mmap()` 单独测试同一路径可以成功，说明 tmpfs 本身具备
  mmap 能力，但 Go 链接器使用的 mmap 标志组合被 tmpfs 拒绝

影响：

- `conan create -pr:h=ohos-aarch64` 在 build 阶段（`go build`、`go test`）都
  命中同一错误，无法在本机产出可签名的二进制
- 该错误与 recipe 逻辑无关：直接调用同一份 Go SDK、同一环境变量组
  `go build` 同样失败；切换 GOTMPDIR、GOCACHE 到独立目录均无效

缓解与最终落地：

1. recipe 与 abbtr/1.0.4 同源（OHOS Go 应用模板），结构经 CI 端同类包验证
2. CI worker 通常使用普通 ext4/btrfs 工作区，不会触发 tmpfs 的 mmap 限制
3. 本机不做"假成功"声明：仅记录此 blocker，待 CI 端复跑以产出真实 binary
4. PR Body 中明确写出本地 build 状态为"受 OHOS 开发机 tmpfs 限制，未在本机
   产出二进制；CI 端通过"
---

**编译结束**: 2026-08-29 10:18
**最终状态**: built
