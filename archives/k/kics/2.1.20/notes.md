# 适配笔记 — kics 2.1.20 (HarmonyOS PC / OpenHarmony)

## 任务类型
积分赛：kics 2.1.20 向 OpenHarmony / HarmonyOS PC (aarch64) 的 conan 适配与打包。

## 依赖拓扑结论（W0 只读分析）
- kics 2.1.20 为**纯 Go 静态二进制**，**零 conan 强制第三方依赖**。
- 唯一构建期需求是 **Go 工具链**（go1.25.x），按 OHC 先例（`aiac`/`addchain`/`ahoy`/`ain`）
  由配方在 `generate()/_ensure_go_toolchain()` 内下载并 OHOS 自签名，**不立 conan 包**。
- go.mod 声明 `go 1.25`，直接依赖 45 + 间接 225 共 270 个 Go 模块；**无任何 CGO / 系统 C 库依赖**
  （仅 `mattn/go-{colorable,isatty,runewidth}` 纯 Go 终端包）。
- 270 个 Go 模块在构建期经 `go mod download` + GOPROXY 拉取，非 conan 依赖。

## 源码与构建入口核验
- 官方归档（版本化）：`https://github.com/Checkmarx/kics/archive/refs/tags/v2.1.20.tar.gz`
  - 实测 http_code=200，size=94,315,043，sha256=`7424ca07901a8534f6aa9b9d21b4c3aa873a027cf22e4bf334c5cf7fba134ae3`
  - 顶层目录 `kics-2.1.20/`，配方 `source()` 用 `strip_root=True`。
- 模块路径：`github.com/Checkmarx/kics/v2`；主程序入口 `cmd/console/main.go`。
- 版本注入变量：`github.com/Checkmarx/kics/v2/internal/constants.Version`（默认 "development"），
  ldflags：`-X ...constants.Version=v2.1.20`。
- **查询资源加载方式（实测澄清）**：仅 `assets/libraries/*.rego|*.json` 与 secrets 正则经 `//go:embed`
  编入二进制；**完整查询库 `assets/queries` 走文件系统 `--queries-path`（默认 `./assets/queries`）**。
  因此 `package()` 必须随二进制打包 `assets/`，否则消费者扫描报 `unable to find queries`。

## OHOS 平台适配要点
1. **Go 工具链自签名**：下载的 `go` 二进制及 `pkg/tool/linux_arm64/*` 在 OHOS 上必须携带 `.codesign`
   段，否则 fork/exec 被静默拒绝（execv 返回 exit 1）。配方 `_sign_elf_if_ohos` / `_sign_go_sdk_if_ohos`
   调用 `binary-sign-tool sign -selfSign 1 -signAlg SHA256withECDSA`
   （工具实测位于 `/data/service/hnp/bin/binary-sign-tool`）。
2. **链接输出落 ext2 工作区**：HMDFS 的 mmap 限制使链接阶段 `mapping output file failed: permission denied`，
   链接产物写到 el2 可写工作区（`/data/storage/el2/base/haps/entry/files/kics-2.1.20-go/link-out`）。
3. **GOOS/GOARCH**：OHOS → `GOOS=linux GOARCH=arm64`，产出 linux/arm64 静态二进制（CGO_ENABLED=0）。
4. **GOPROXY**：`proxy.golang.org` 在本沙箱不可达（000），配方默认 `https://goproxy.cn,https://proxy.golang.org,direct`，
   `goproxy.cn` 实测可达，模块拉取正常。
5. **自签名 ELF 的系统调用限制（实验确证，影响测试执行方式）**：
   - 自签名进程**不能 `execve` 另一个二进制** → `go test -exec <wrapper>` 不可用（wrapper 的
     `syscall.Exec(testBinary)` 报 `permission denied`）。因此上游测试采用
     **逐包 `go test -c` 编译 → 自签名 → 以 conan 子进程直接运行**（与 kics 自身同一可信链）。
   - 自签名进程**对软链的 `symlink()/lstat()` 被拒** → kics 经 go-getter 对本地路径建软链的抽取流程
     在 OHOS 必然失败。**补丁 1**：`build()` 内 patch `pkg/engine/provider/extract.go` 的 `GetSources`，
     对本地已存在路径（去 `file://` 前缀后 `os.Stat` 命中）直接短路引用，跳过 go-getter 软链
     （仅改目标库自身源码，幂等，见 conanfile.py `_patch_ohos_extract`）。
6. **查询路径解析补丁（补丁 2）**：kics `internal/console/helpers/helpers.go` 的 `GetFullPath` 用
   「把 cwd 在首个 `"kics"` 组件处截断」的启发式定位仓库根（上游约定检出目录名为 `kics`）；
   conan 哈希布局（如 `.conan2/p/b/kics<hash>`）下失效 → 默认查询路径与 remediation 模板全部解析失败。
   **补丁**：`GetFullPath` 增加两步回退——① 探测 exe 目录父级（conan 包布局 `assets/` 与 `bin/` 同级，
   发行二进制在 OHOS 任意目录运行时受益）；② 从 cwd 向上逐级查找 `partialPath`；原启发式保留兜底
   （见 conanfile.py `_patch_ohos_helpers`）。该补丁同时修复 206 个 terraform positive 集成测试的
   `SelectedRemediationNumber: expected N, actual 0` 假失败（仅 terraform 查询带 remediation 模板）。
7. **测试工作目录**：每个测试二进制必须**从其所属包目录**运行（与原生 `go test` 一致），
   否则依赖相对路径测试数据的功能性测试集体假失败（实测 analyzer 包失败 20→5）。
8. **`test/` 集成包专属超时**：该包（注意：位于仓库根 `test/`，非 `pkg/test`）需枚举全部查询做
   元数据校验 + 数千个扫描子测试，配方给它单独 2400s 超时；120s 默认会拦腰截断其输出
   （实测同配方冷/热 I/O 分别仅计入 8 / 3628 例，属 harness 伪影）。

## 上游测试入口与 OHOS 执行方式
- 上游入口：`go test -v -count=1 ./...`（testify，69 个含测试的包）。
- OHOS 等价复刻：`go test -c`（逐包编译）+ 自签名 + 从各包目录直接运行；
  完整输出写入 `build_folder/upstream_test_full.log`，并打印 `HMBS_UPSTREAM_TEST_RESULT`。

## 测试统计（单独汇报口径，权威 = attempt 8 最终构建）
- 命令：`<go> test -c`（逐包）+ `<bin>.test -test.v -test.count=1`（从各包目录直接运行，4 线程并行）。
- **总计（attempt 8 全量轮）：PASS=8286 / FAIL=18 / SKIP=1（8305 例，69 包，通过率 99.78%）**；
  W3 干净重建复现：PASS=8286 / FAIL=17 / SKIP=1（8304 例，差 1 例 console 性能阈值用例
  TestScanPerformance 未复现失败，其余逐包结果一致；reports/w3-local-ci.log:311,382）。
  `HMBS_UPSTREAM_TEST_RESULT={"status":"failed","discovered":8305,"executed":8305,"passed":8286,"failed":18,"skipped":1}`。
- 逐包：66/69 包无失败判定（53 ok + 13 无测试用例；3 个失败包 analyzer/console/test）；`pkg/remediation`（10,0,0）与 `internal/console/helpers`（27,0,0）经补丁 2 修复转绿。
- **18 例失败全部定性（每例有日志取证）**：
  - **9 例 pkg/analyzer —— OHOS 平台限制**（`analyze_test_dir_single_path{,_types_value,_exclude_type_value}`、
    `ignore_pnpm_lock_yaml_file`、`ignore_dead_symlink`、`FileStats` 两例等）：夹具含 `dead_symlink`，
    报错 `lstat .../dead_symlink: permission denied` —— 自签名进程禁触软链，非适配缺陷。
  - **7 例 internal/console —— 本地源树夹具丢失（环境假象）**：`kics_test.go` 硬编码引用
    `../../assets/queries/terraform/aws/alb_is_not_integrated_with_waf`，该目录在本机抽取树中缺失；
    经 GitHub contents API 核验**该目录在上游 v2.1.20 tag 中真实存在**
    （metadata.json sha 433d2392…、query.rego sha bca984dc…）→ 属本机 HMDFS 抽取/持久化异常，
    非上游缺陷、非适配缺陷。
  - **2 例 test/（TestInspectorSimilarityID）—— 同类本地夹具丢失**：`test/fixtures/tc-sim01/positive1.tf`
    在本机抽取树中幻影丢失（同目录 positive2.tf/query.rego 带归档原始 mtime 幸存）；
    GitHub contents API 核验该文件在上游 v2.1.20 tag 中存在（sha d749ce1b…，561 字节）。
    ~~此前 notes 误判为"上游 tarball 内容缺陷"，经上游 tag API 裁决予以更正。~~
- **闭环验证（恢复夹具后直接重跑受影响二进制）**：见
  `.workbuddy/tmp/kics-2.1.20/supplement_rerun.log`（console 与 test/ 两包恢复夹具后重跑结果）。
- test_package（消费者可行性，非替代品）：2/2 PASS —— `kics version`=2.1.20；
  真实 `kics scan` terraform：`queries_total=1099`、`queries_failed_to_execute=0`、
  REPORT_BYTES=9604、`ALL_CONSUMER_TESTS_PASSED`。

## test_package（消费者用例可行性）
- `test_package/conanfile.py` + `test.sh`：运行打包后的 `kics` 二进制：
  1) 断言 `kics version` 退出码 0 且含 `2.1.20`；
  2) 复制打包内 `assets/` 到 el2 同文件系统工作区，对真实 terraform 文件执行
     `kics scan --type terraform --queries-path ... --libraries-path ... --report-formats json`，
     校验扫描引擎、查询加载与报告输出在 OHOS 上端到端可用 —— 即"HarmonyOS 消费者用例可行性"测试。

## 已知风险 / 备注
- 18 例失败已逐一取证归因（9 平台限制 + 9 本地环境假象）；无网络依赖类失败。
- **环境陷阱（新维度，重要）**：本机 HMDFS 对 /storage 上新写入的大目录树存在**进行性文件丢失**
  （.conan2 最新活跃条目的 assets/queries 从单目录 → 整树在约 1 小时内消失；更早的 conan 条目
  与仓库其他目录不受影响）。已用 GitHub contents API 证明丢失文件全部存在于上游 v2.1.20 tag。
  判定上游归因前必须先以上游 tag API 核对文件存在性。**全部构建/测试证据已备份至**
  `/data/storage/el2/base/haps/entry/files/kics-evidence/`（el2 稳定区），日志含
  upstream_test_full.log（29050 行）、conan-create8.log（528 行）及全部配方/报告/test_package。
  本地 .conan2 中 attempt-8 包缓存事后受损（assets 被吃），不影响 CI 侧从配方重建。
- attempt 7 的 `internal/console (0,0,0)` 为**静默空转误判**（旧启发式下扫描卡查询解析、120s 超时
  截断、无用例行产出被计为 ok）——"0 用例的 ok"必须视为异常信号而非通过。
- 配方同时声明 arm64 / amd64 工具链归档，CI 构建宿主为 aarch64 时取 arm64。
---

**编译结束**: 2026-09-18 03:11
**最终状态**: built
