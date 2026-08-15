# git-who 1.3 适配笔记

## 编译环境
- 构建系统: custom (Go 项目，`go build .`)
- 编译日期: 2026-08-15
- 编译器: Go 1.23.8 (CGO_ENABLED=0，纯静态无 C 依赖)
- 状态: built

## 上游信息

- 仓库: https://github.com/sinclairtarget/git-who
- 版本: v1.3 (2026-01-24 发布，commit aa656b0)
- 语言: Go (100%)，module `github.com/sinclairtarget/git-who`，go 1.23
- 依赖: `doublestar/v4 v4.8.1`、`go-cmp v0.6.0`、`go-runewidth v0.0.16`、`x/term v0.28.0`、`x/sys v0.29.0`、`uniseg v0.2.0`
- 类型: Go CLI 工具（子命令 dump/parse/table/tree/hist，默认 table）
- License: MIT

## 上游测试统计

- 测试文件: 10 个 `*_test.go`
- `Test` 函数总数: 22 个
  - **19 个纯单元测试**（`internal/`，不依赖 git 二进制/subprocess）：cache/backends 4 + format 3 + git 4 + pathspec 3 + tally 5
  - **3 个集成测试**（`test/integration/git/args_test.go`）：需要 `test/repos/test-repo` git submodule（https://github.com/sinclairtarget/git-who-test-repo，103K，含 root tag + commit 6afef287...）；GitHub 源码 tarball 不含 submodule 内容，配方 build() 尝试用 `git clone` 拉取后运行；clone 失败则如实披露为未运行
  - **Ruby 功能测试**（`test/functional/*.rb`，Rakefile/minitest 套件）：8 个测试文件、23 个静态 `def test_` + table_test.rb 的 define_method 笛卡尔组合用例；需 ruby + minitest gem + gunicorn/test-repo submodule，OHOS 无 Ruby 运行时，无法在真机执行（如实披露，不计入通过）
- 真机可运行集合 = 19 个 internal/ 单元测试（命令 `go test -v -count=1 ./internal/...`；集成测试视 clone 结果追加）

## 编译步骤

1. 下载源码: 官方 GitHub tag `https://github.com/sinclairtarget/git-who/archive/refs/tags/v1.3.tar.gz`，sha256 `7af9950b8786a52e71e80457986f8b961064dc39923de1e330bc9fede42feef4`（conandata.yml 为 gh-proxy 镜像优先列表）
2. 探测设备 Go 工具链（PATH/GO/GOROOT/常见安装根）；找不到则下载 go1.23.8.linux-arm64.tar.gz（golang.google.cn / mirrors.aliyun.com / dl.google.com 镜像列表）
3. OHOS 下对 Go SDK 全部 ELF（go/gofmt/pkg/tool/*）做 binary-sign-tool 签名
4. 编译命令:
```bash
export GOOS=linux GOARCH=arm64 CGO_ENABLED=0 GOTOOLCHAIN=local
go mod download
go build -trimpath -ldflags "-s -w -X main.Version=1.3 -X main.Commit=aa656b0" -o bin/git-who .
```
5. OHOS 下链接输出重定向到非 hmdfs 工作区（TMPDIR），签名后复制回 build_folder/bin
6. 上游测试: `go test -v -count=1 ./internal/...`（OHOS 下带 `-exec` 签名包装脚本），解析 `--- PASS/FAIL/SKIP` 计数，输出 `HMBS_UPSTREAM_TEST_RESULT`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Go 工具链二进制 Permission denied | hmdfs 下无 .codesign 段 ELF 被 Seccomp 拦截 | binary-sign-tool 签名 go/gofmt/pkg/tool 全部 ELF 后执行（配方内 `_sign_go_sdk_if_ohos`，addchain 先例） |
| 2 | Go linker 报 mapping output file failed | linker mmap 输出文件在 hmdfs 失败（E051/E046） | 链接输出目录放到 TMPDIR 工作区（addchain/ain/aliyun 同款先例） |
| 3 | go test 0 用例运行 | OHOS 上 *.test 二进制未签名被 fork/exec 拒绝 | `go test -exec` 签名包装脚本（addchain 同款） |
| 4 | 上游测试如何界定 | 22 个 Test 中 3 个集成测试需 submodule（tarball 不含），配方 build() 先尝试 git clone git-who-test-repo 后运行；23 个 Ruby 功能测试需 Ruby/minitest | 单元 19 个全量接入真机执行；集成测试视 clone 结果；Ruby 功能测试在 MANIFEST.yml `test_suite_gaps` 与 PR 补充说明如实披露 |
| 5 | test_package case3 `git-who table` 报 "detected dubious ownership in repository at <TMPDIR>/git-who-test-$$" exit 128 | OHOS HMFS 目录属主上报与进程 euid 不一致，git 的 CVE-2022-24765 dubious ownership 防护把 TMPDIR 下新建临时仓库误判为不可信 | test.sh 顶部导出 `GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'`，环境配置与 GIT_CONFIG_GLOBAL/SYSTEM 独立，git-who fork 的 git 子进程同样生效；并显式校验初始提交子 shell 退出码，避免提交失败被静默吞掉 |

## 源码修改

无补丁（纯 Go 项目，CGO_ENABLED=0 静态编译，无平台分支代码）。

## 依赖版本

| 依赖 | 版本 | 说明 |
|------|------|------|
| Go SDK | 1.23.8 | linux-arm64，镜像优先下载，sha256 `9d6d938422724a954832d6f806d397cf85ccfde8c581c201673e50e634fdc992` |

## 验证结果

- 真机 `conan create` 通过（待 HMBS 预检确认）
- 上游 19 个单元测试全数执行（数字以真机预检日志为准）
- test_package: `git-who --version` 输出含 1.3、`git-who --help` 输出 Usage: git-who（2 条断言）

## 修复记录（2026-08-15，缺少 HMBS_UPSTREAM_TEST_RESULT 证据 — 缓存复用跳过 build()）

- 失败指纹（evidence 域）：preflight 日志显示 `git-who/1.3: Already installed! (1 of 1)`，
  即 conan 从 per-task 持久缓存（clients/<id>/conan-home）直接复用上一轮构建的包，
  `build()` 整段未执行——而 HMBS_UPSTREAM_TEST_RESULT 标记只在 build() 末尾 print，
  故本轮日志完全没有标记 → hmbs 判 incomplete（发现/执行/通过全为 0）。
- 根因：标记输出通道绑定在 build() 内，而 preflight 每轮复用缓存时 build() 会被跳过；
  配方/测试代码无任何失败（conan create 与 test_package 3 用例均通过）。
- 修复（对齐 aribb24/1.0.4 先例——标记必须在每轮必跑的 test_package 阶段裸 print）：
  1. conanfile.py `_run_upstream_tests()`：真机执行 go test 后把结果 dict 持久化为
     `build_folder/upstream_test_result.json`（保留 build() 内的 print 作为首轮证据）。
  2. conanfile.py `package()`：把 `upstream_test_result.json` 复制进包内 `res/`。
  3. test_package/conanfile.py `test()`：运行 test.sh 后读取
     `<package>/res/upstream_test_result.json`，裸 `print()` 复发
     `HMBS_UPSTREAM_TEST_RESULT=<同一 JSON>`；文件缺失则 ConanException 显式失败。
- 预期：下一轮 conanfile.py 内容已变化 → 配方 revision 变化 → conan create 强制重跑
  build()（真机 go test 重新执行、重新生成并打包 json），test_package 复发标记；
  之后任意轮缓存复用 build() 被跳过时，标记仍由 test_package 稳定输出。

## 注意事项

- hmbs 预检沙盒不注入 go 工具链，配方必须先探测设备 go，失败再下载固定 SDK；下载的 SDK 放在 per-build 工作区，不污染系统
- `--version` 输出 `Version Commit` 两个变量，必须用 ldflags `-X main.Version/-X main.Commit` 注入，否则输出 "unknown unknown"
- OHOS 下所有将被 fork/exec 的 ELF（含 go test 临时二进制）必须带 .codesign 段
