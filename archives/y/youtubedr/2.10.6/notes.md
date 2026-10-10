# youtubedr 2.10.6 适配笔记

## 轮次 1（2026-09-29）：初始适配——创建缺失的 archive 代码树

### 本轮定位
hmbs-preflight 判定 `incomplete`，失败阶段 `evidence`，原因：**无法读取当前 archive
代码树，不能启动真机预检**。检查工作树：`archives/y/youtubedr/` 完全不存在（新库，
首个 PR）。根因是缺少整个适配目录。

### 源码核实（SHA256 校验通过）
- 来源：https://github.com/kkdai/youtube/archive/refs/tags/v2.10.6.tar.gz
  sha256=c334c04c07c3576e911d78b65b068b574e81e33e385f63a86b4862022391240d
- 纯 Go 项目：module `github.com/kkdai/youtube/v2`，go 1.26
- CLI 入口：`cmd/youtubedr`（cobra，含 version/info/list/download 子命令）
- 官方测试：Makefile `test-unit` = `go test -v -cover ./...`
- 31 个非 integration 的 func Test（根包 27 + downloader 包 4）：
  - 离线纯逻辑/解析：ExtractVideoId / findVideoID / GetItagInfo / FormatList Filter+Sort /
    getVideoAudioFormats / DownloadWithHighQualityFails / SanitizeFilename / GetChunks /
    ProtoBuilder / PlayerCache / extractPlaylistID / Errors 等
  - 直接访问 YouTube 网络端点（真实 GetVideo/GetPlaylist/GetStream/字幕/下载）：
    ParseVideo / GetVideoWithoutManifestURL / WebClientGetVideo / GetVideoWithManifestURL /
    GetVideo_MultiLanguage / GetStream / GetPlaylist / GetBigPlaylist / httpGetBodyBytes /
    SimpleTest / Download_Regular / Download_WhenPlayabilityStatusIsNotOK /
    Download_SensitiveContent / Parse_PublishDate / Transcript / TranscriptOtherLanguage /
    downloader Download_FirstStream
- integration 标签（`build integration`）：downloader/downloader_hq_test.go 的
  TestDownload_HighQuality —— 不计入（go test ./... 默认不编译 integration 标签）

### 本轮改动（仅工作树，未 commit/push）
1. `archives/y/youtubedr/README.md` — 软件级说明
2. `archives/y/youtubedr/manifest.yaml` — 软件级 manifest（custom build_system）
3. `archives/y/youtubedr/commands.json` — 软件级 CLI 声明（type=tool，versions 含
   2.10.6，binary=true，参照 verovio/goenv 先例），满足 L0k/R38
4. `archives/y/youtubedr/2.10.6/conanfile.py` — 参照 murex 先例的 Go 配方：
   - 自包含下载 go 1.26.3（aliyun 镜像，sha256 已验证）
   - CGO_ENABLED=0 + GOOS=linux + GOARCH=arm64，`go build ./cmd/youtubedr`
   - ldflags `-X main.version=2.10.6`
   - build() 内跑 `go test ./... -timeout 30m -v -exec=<签名wrapper>`，
     逐行解析 `=== RUN` / `--- PASS|FAIL|SKIP` 生成 HMBS_UPSTREAM_TEST_RESULT
     （计数唯一来源 go test -v 输出，不数数相减、不做猜测修正）
   - 整包编译失败（discovered==0）抛 ConanException；运行时失败/跳过不抛，
     以 gap 如实上报，让 hmbs 读到真实标记
   - OHOS 产物与测试二进制用 binary-sign-tool 签名
5. `archives/y/youtubedr/2.10.6/conandata.yml` — source URL+sha256 + go_toolchain
6. `archives/y/youtubedr/2.10.6/manifest.yaml` — 版本级 manifest
7. `archives/y/youtubedr/2.10.6/test_package/` — conanfile.py + test.sh + MANIFEST.yml
   （test.sh 跑 youtubedr version 断言 2.10.6 与 Version 字段、--help 断言程序说明）

### 设计要点（避免伪造通过）
- 不把网络测试包装成通过：17 个 YouTube 网络端点用例在无外网/受限的 OHOS 沙盒
  按 test_failure/ohos_feature gap 上报；纯逻辑用例如能全过则如实全过。
- 计数常量与恒等式：passed+failed==executed、executed<=discovered（用 --- PASS/FAIL/SKIP
  行求和），不凑数、不减法推导。
- 上游测试以真机 go test 输出为准，PR 正文通过率用真机实测，不估不抄。

### 下一步
工作树修改保持未提交。HMBS 同步代码树到真机复跑预检：
- 预期 conan create 能读取 resolve 的 archive → 自包含下载 go 1.26.3 → go build 成功 →
  go test ./... 跑出真实计数器 → conan test 跑 test.sh → hmbs 读到标记
- 预检通过或暴露真机具体失败后，由 HMBS 统一管理后续轮次与提交。

## 轮次 2（2026-09-29）：修复 test_package 真机失败（rule4 计数矛盾）

### 本轮定位（hmbs-preflight evidence incomplete）
真机 `conan create` 中上游 go test 正常（31 发现/13 通过/18 失败/0 跳过，已按 gap 如实上报），
但 test_package 失败：
- test.sh 前两项 version 断言通过；第三项 `--help` 前出现大量
  `job-working-directory: error retrieving current directory: getcwd: cannot access parent
  directories: Not supported / Bad file descriptor`，之后脚本以非 0 退出，`[ok] --help` 未打印。
- HMBS_TEST_PACKAGE_RESULT 输出 `{"passed": false, "discovered": 3, "passedCount": 3}`——
  passed=false 却 passedCount=3，被 rule4 判"计数矛盾"。

### 根因
HMBS 平台诊断明确：HNP bash/sh 无法对 conan 测试构建目录（HMFS/HMDFS 路径）getcwd()。
test.sh 用 `#!/usr/bin/env bash` + `set -euo pipefail` 直接在 HMFS cwd 下逐条运行二进制，
`--help` 那次子进程因 getcwd 失败以非 0 退出被 set -e 掐死 → self.run 抛异常 → passed=false；
而 conanfile 又硬编码 passedCount=3，与 passed=false 自相矛盾。

### 本轮改动（仅工作树，未 commit/push）
1. `test_package/test.sh`：
   - shebang 改 `#!/bin/sh`（POSIX，规避 HNP bash 的 shell-init/job-working-directory getcwd 报错）
   - 脚本一开始 `cd` 到可 getcwd 的可靠目录（hmbs 注入 TMPDIR，回退 /），让 version/--help
     子进程继承有效 cwd（直击 HMFS/HMDFS getcwd 约束，断言未删、真实执行）
   - 去掉 `set -e`（改用显式逐条计数），保留 `set -u`；3 项断言保持原样并逐条统计
     total/passed，把真实计数写到结果文件（${TEST_PACKAGE_RESULT_FILE} 优先，回退 $TMPDIR）
   - 退出码按 passed==total 决定（0 通过 / 非 0 失败），真实反映结果
2. `test_package/conanfile.py`（test()）：
   - 执行改用注入的 `sh`（不用 HNP bash）
   - 设 `TEST_PACKAGE_RESULT_FILE`（TMPDIR 下）传结果文件路径
   - run 后从结果文件读回真实 total/passed，标记用 discovered=total、passedCount=passed，
     passed=(run_error is None and passed==total>0)，杜绝 passed=false 与 passedCount=3 的矛盾
   - 一致性问题（run 抛异常时）仍在 run 后统一输出一次标记再 re-raise，保证 there is marker

### 预期
test_package 在真机重跑：version 两项 + --help 一项全部真实通过 → discovered=3/passedCount=3/
passed=true，rule4 通过。上游 go test 计数不变（31/13/18 已如实上报）。

## 轮次 3（2026-09-29）：修复源码归档下载超时（真机 compile 阶段失败）

### 本轮定位（hmbs-preflight compile failed）
conan create 的 source() 阶段直连 https://github.com/kkdai/youtube/archive/refs/tags/v2.10.6.tar.gz
多次 30s connect timeout 后失败，无法进入 build/test 阶段（ConanException in source() line 84）。
真机没有应用 CI 的自动镜像改写，需要把 conandata.yml 的 source.url 改成带加速镜像的和官方
兜底的有序列表。

### 根因
真机/CI 执行环境无法直连 github.com 下载源码归档（连接超时）。conandata.yml 只有单条官方
URL，无镜像 fallback，Conan get() 直接超时失败。

### 本轮改动（仅工作树，未 commit/push）
1. `conandata.yml` sources.url 单值 → 有序列表：gh-proxy.com 加速镜像在前、官方原始 URL
   最后兜底；sha256 保持不变（镜像与官方归档逐字节一致）。遵循 CI build_and_test.sh 的
   GitHub 镜像映射（gh-proxy.com + 官方直连兜底）。
2. `2.10.6/manifest.yaml` source.url 同步改为前置镜像 URL（gh-proxy.com），与 conandata.yml 一致。

### 预期
预检 conan create 从 gh-proxy.com 镜像正常下载源码归档（sha256 校验不变），进入 build/test 阶段。


## 轮次 4（2026-09-29）：修复真机 chmod 失败（PermissionError: go/bin/go）

### 本轮定位（hmbs-preflight compile failed）
conan create 的 build() 阶段在 `_ensure_go_toolchain_permissions()` 里对自包含下载的
Go 工具链 `go/bin/go` 执行 os.chmod() 时抛：
`PermissionError: [Errno 13] Permission denied: '/data/storage/el2/base/cache/conan-go-build/youtubedr-2.10.6/go-toolchain/go/bin/go'`
（链：_go_executable -> _bootstrapped_go_executable -> _ensure_go_toolchain_permissions
-> _chmod_read_exec -> os.chmod(line 343)）。

### 根因
hmbs 平台能力诊断：`HMBS_PLATFORM_CAPABILITIES={"chmod":0,...}`，对应注入 `HMBS_CAP_CHMOD=0`。
真机 el2 base cache 为 HMFS/fuse 挂载，**不允许 chmod**（EPERM -> Python PermissionError），
而 use 的 Go 工具链下载/解压到该挂载下。murex 先例同构，但其真机 worker 的 el2 挂载允许 chmod；
本轮 worker1 的挂载 chmod=0，os.chmod 硬抛。知识库 E046/SKILL R49 一致：HMFS chmod 被忽略/拒绝。

### 本轮改动（仅工作树，未 commit/push）—— `2.10.6/conanfile.py`
1. 新增 `_platform_supports_chmod()`：读 `HMBS_CAP_CHMOD`，值为 0/false/no/空视为不支持，
   未设置（Linux/ext4 worker）默认支持，保持旧行为。
2. `_chmod_read_exec()`：chmod 不支持时直接返回（不动 mode，仅 debug 提示）——Go 工具链
   tar 归档自带 exec 位，解压即保留，无需 chmod。
3. `_build_binary()` 对产物 output_path 的 os.chmod 同样包上 `_platform_supports_chmod()`。
4. `_go_test_exec_wrapper()`：chmod 不支持时（新写脚本无可执行位且无法 chmod），
   `-exec=` 改为经 `/bin/sh <wrapper>` 执行（go 的 -exec 值按空白拆 argv），
   不依赖脚本 +x，保证 OHOS 测试仍能经签名 wrapper 运行。
5. `os.access(go, os.X_OK)` 校验保留——go 从 tar 解压自带 exec 位，el2 挂载按其 mode
   判定可执行；若真不可执行则如实抛错，不伪造。

### 预期
chmod 不支持（HMBS_CAP_CHMOD=0）的真机上：跳过非法 chmod，工具链 exec 位靠 tar 保留，
`go build`/`go test -exec=/bin/sh wrapper` 正常执行；chmod 支持的真机行为与 murex 一致。



## 轮次 5（2026-09-29）：修复 test_package `--help` 断言字符串（cobra Long 覆盖 Short）

### 本轮定位（hmbs-preflight evidence incomplete，rule4 新增测试不足 100%）
真机 conan create：
- 上游 go test 正常（31 发现 / 13 通过 / 18 失败 / 0 跳过，网络用例已按 ohos_feature/test_failure gap 如实上报）。
- test_package 冒烟测试 `--help` 一项失败 → `[FAIL] youtubedr smoke test: 2/3 passed`，
  HMBS_TEST_PACKAGE_RESULT `{"executed": true, "passed": false, "discovered": 3, "passedCount": 2}`。
  真机日志 --help 输出尾部只有 flags 块与 "Use ... --help for more information"，无 "Youtube downloader"。

### 根因
cmd/youtubedr/root.go 的 rootCmd 同时设置了 `Short: "Youtube downloader written in Golang"`
和 `Long: "This tool is meant to be used to download CC0 licenced content..."`。cobra 生成 help
时，当 Long 非空时用 Long 显示在头部，Short 不出现。所以 `youtubedr --help` 输出里根本没有
"Youtube downloader" 这个串，test.sh 第 3 项断言字符串选错了，grep 必然失败（断言本身未误删，
是断言字符串与真实输出不符）。本机用 go1.26.3 + 相同 conan ldflags 重建二进制复现：--help 确定
不含 "Youtube downloader"，而含 "for more information about a command"（cobra 模板稳定行）。

### 本轮改动（仅工作树，未 commit/push）
1. `test_package/test.sh`：
   - 第 3 项断言字符串 `"Youtube downloader"` → `"for more information about a command"`
     （cobra help 模板稳定出现的行，独立于二进制路径/长短描述，反空壳语义不变：验证 help 真实渲染）。
   - 同步更新头部注释说明原因。
2. `test_package/MANIFEST.yml` / `test_package/conanfile.py`：同步更新 --help 断言描述，保持一致。
3. 断言数量仍为 3（version->2.10.6、version->Version:、--help->cobra help 行），未删断言未跳过。

### 本机验证
用 go1.26.3（GOTOOLCHAIN=local、GOPROXY=goproxy.cn）交叉编译 cmd/youtubedr（ldflags -X
main.version=2.10.6），跑修改后的 test.sh：
- version 输出 `Version:     2.10.6` → 两项断言通过；
- --help 输出含 "for more information about a command" → 断言通过；
- total=3/passed=3，脚本退出码 0 → HMBS_TEST_PACKAGE_RESULT 将如实为 passed=true/discovered=3/passedCount=3。

### 预期
下一次真机预检：test_package 3/3 全过（passed=true），rule4 新增测试 100%。上游 go test 计数不变
（31/13/18 已如实上报），PR 正文按真机实测填写。
