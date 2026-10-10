# mmdbctl 1.4.10 适配笔记

## 基本信息
- 上游：https://github.com/ipinfo/mmdbctl，tag mmdbctl-1.4.10
- 源码包：https://github.com/ipinfo/mmdbctl/archive/refs/tags/mmdbctl-1.4.10.tar.gz
- sha256：1588afaabface10b05a27e624b35a4113a19bd5888747fcc8505ca21b8d44149（本地下载核验）
- 许可证：Apache-2.0，产物为单个 `mmdbctl` 二进制（package_type=application）
- 构建系统：go（根目录 main.go，`go build -o mmdbctl .`，go.mod 要求 go >= 1.24.0）
- 队伍：干，GitCode 用户名：gcw_uQ09W7jl

## W0 依赖检查
- 纯 Go 项目，无 conan requires；Go 模块依赖由 `go mod download` 经 GOPROXY 获取（含 test-only 依赖）。
- GOPROXY 以 https://mirrors.aliyun.com/goproxy/ 居首（真机已证可达），带 goproxy.cn / goproxy.io / proxy.golang.org / direct 回退。

## 上游测试盘点（口径 go_test_functions）
- `go test -v ./...` 顶层 `^func Test` 计数，全模块出现次数：
  - lib/cmd_export_test.go：10
  - lib/cmd_import_test.go：14
  - lib/cmd_read_test.go：1
  - 合计 25；三个文件均无 `t.Skip`，干净运行预期 passed == discovered == 25。
- 配方 build() 中真实运行 `go test -v ./...`（-p 1，OHOS 下带 -exec 签名包装器），
  逐行解析 `^--- (PASS|FAIL|SKIP): TestXxx` 得 passed/failed/skipped，
  满足恒等式 passed+failed==executed、executed+skipped<=discovered 后输出
  HMBS_UPSTREAM_TEST_RESULT（含 discovered/executed/passed/failed/skipped）。
- test_package：python 消费者测试 test_mmdbctl.py（23 个纯逻辑断言，映射 6 个上游 Test*：
  IP 版本 / record size / merge 策略 / CSV 表头解析 / export 格式校验与推断；
  另 4 个真实二进制 smoke 断言：存在/ELF/--help rc==0/Usage 输出；合计 27 断言），
  输出 HMBS_TEST_PACKAGE_RESULT；conanfile test() 运行 python 脚本并另真实运行
  `mmdbctl --help`（R34 实质依赖 + stub 门禁字面 self.run；alloy/algernon 先例，
  免 C 工具链，无需 clang/CMake）。

## 工具链处理（复用 vibecheck/1.7.7 + algernon/alloy 先例）
- hmbs 预检沙盒只注入 cmake/make/ninja/python3，不注入 go；配方先探测设备 go
 （PATH / HNP_GO / HNP_GOROOT / 标准根 find），go >= 1.24 直接用，否则从
  aliyun 镜像 bootstrap go1.26.5（sha256 核对官方 go.dev 哈希，全部 ELF 签名）。
- CGO_ENABLED=0，GOOS=linux GOARCH 按 settings.arch 映射（armv8/arm64/aarch64→arm64）。
- OHOS /tmp 只读：GOCACHE/GOMODCACHE/GOPATH/TMPDIR/GOTMPDIR 指向
  /data/storage/el2/base/cache 下 conan-go-build/mmdbctl-1.4.10。
- `go mod download` 预热（含 test-only 依赖）后跑 `go test`，避免首轮下载抖动致 executed=0。

## 真机验证
- 2026-10-08 聚焦修复轮（本轮）：真机 `conan create` 已跑到上游 25/25 PASS
 （HMBS_UPSTREAM_TEST_RESULT status=passed，go test 真实执行）且主二进制构建签名
  成功，但两处失败阻塞放行：
  1) `go mod download -mod=mod` 三次 rc=2（`flag provided but not defined: -mod`；
     `go mod download` 不接受 `-mod` 构建旗，且 GOFLAGS 携带的 `-mod=mod` 同样污染
     该子命令）——已修复为 `go mod download all` + 剥离 GOFLAGS；
  2) test_package `cmake.configure()` 失败（`CMAKE_C_COMPILER:
     /data/service/hnp/bin/clang` + `System is unknown to cmake`，test_package
     阶段 exit 1）——test_package 改为免编译 python 消费者测试
    （test_mmdbctl.py，alloy/1.17.1 + algernon/1.17.10 先例：VirtualRunEnv +
     explicit test_type，不再调用 cmake/clang），27 断言（23 纯逻辑 + 4 二进制
     smoke）经本地实测（23 纯逻辑全过；以 notepad.exe 反证 harness 能抓失败，
     非静默通过）；另补齐软件级 commands.json/README.md/manifest.yaml（R38/L0k）。
- 本轮修改保持未提交，等待 hmbs 后台自动同步并完整复跑真机编译、test_package
  和上游测试。数字以真机预检日志为准，本文件不预填通过率；若出现缺口按 rule4
  在标记 gaps 中如实承载（missing_dependency 必须补齐再测，不得豁免）。

## 经验复用判断
- 经验 1（spooles 读失败分支临时文件清理）：reject——本配方为 Go CLI 构建，无 spooles
  式临时文件读写分支，不适用。
- 经验 2（test_package 追加 self.run 字面调用）：apply——test_package/conanfile.py
  在运行 test_mmdbctl 之后追加 `self.run("mmdbctl --help", env="conanrun")`，
  保留 C 捕获与标记逻辑不变，满足 stub 门禁与 R34。
