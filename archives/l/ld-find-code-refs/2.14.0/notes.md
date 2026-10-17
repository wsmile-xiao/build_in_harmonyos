# ld-find-code-refs 2.14.0 — 适配笔记（路径 A）

## 三重身份映射

| 身份 | 值 |
|------|-----|
| 平台 | ld-find-code-refs / 2.14.0 / Issue（任务页）/ feat/ld-find-code-refs-2.14.0 |
| 上游 | launchdarkly/ld-find-code-refs（github.com/launchdarkly/ld-find-code-refs），tag v2.14.0，Apache-2.0 |
| 归档 | Conan ld-find-code-refs/2.14.0，archives/l/ld-find-code-refs/2.14.0/ |

三者名称与版本完全一致，无需映射解释。任务页标签为 C++ 库适配，实际该软件为纯 Go CLI（无 C/C++ 目标库），属于应用类（package_type=application）路径 A 适配。

## 上游核验

- 源码：https://github.com/launchdarkly/ld-find-code-refs/archive/refs/tags/v2.14.0.tar.gz（与 codeload .../tar.gz/refs/tags/v2.14.0 形态字节一致；conan get() 按扩展名选解压器，必须用 .tar.gz 结尾的 URL）
- SHA256（双端实测，两种 URL 形态一致）：c7e305001837e5d7b8c4e1f5dbbaea66e2e4567ff161c0039a5375fd2cf3b791
- 许可证：Apache-2.0（LICENSE.txt）
- 语言：Go（go.mod: go 1.24 / toolchain go1.24.1，module github.com/launchdarkly/ld-find-code-refs/v2）
- 构建系统：Go + Makefile（`go build ./cmd/...`，产物 `ld-find-code-refs`）
- 依赖：自带完整 vendor/（可 -mod=vendor 离线构建+测试）；运行期依赖 git>=2.21（设备 2.45.2 满足）
- 版本常量：internal/version/version.go `const Version = "2.14.0"`（常量，不可 -X 注入，随源码烘焙）
- 测试入口：`go test ./...`，11 个 _test.go 文件 / 9 个包 / 35 个顶层测试函数（另有 8 个包内 func TestMain 为测试装配器，不计用例）：
  - aliases/alias_test.go（3，含 TestMain）
  - build/package/bitbucket-pipelines/bitbucket-pipelines_test.go（2，含 TestMain）
  - build/package/github-actions/github-actions_test.go（3，含 TestMain）
  - coderefs/coderefs_test.go（1，含 TestMain）
  - flags/flags_test.go（2，含 TestMain）
  - internal/git/git_integration_test.go（1，含 TestMain；go-git 纯 Go 建仓，不执行 git 二进制）
  - internal/ld/ld_test.go（9，含 TestMain，httptest 本地服务器）
  - internal/validation/validation_test.go（1）
  - search/（共 13：files_test.go 2、matcher_test.go 4、search_test.go 7，search_test.go 另含 TestMain）
  - 无网络、无 API key 依赖

## 实现要点

- conanfile.py：Go 应用配方（参考 archives/u/unpackerr 先例）：
  - `go test -mod=vendor ./...`（OHOS 上 `-exec` 自签 wrapper）→ `go build -mod=vendor -trimpath -ldflags "-s -w" -buildvcs=false -o ld-find-code-refs ./cmd/ld-find-code-refs`
  - GOPROXY=off：vendor 完整，强制离线确定性
  - Go 工具链 go1.26.3（linux-amd64/linux-arm64）自 mirrors.aliyun.com 下载，SHA256 已在设备实测复核（sha256sum == 配方值），置于模块树外
  - GOCACHE/GOMODCACHE/GOPATH/TMPDIR/链接输出置于非 hmfs 工作区（/data/storage/el2/base/cache，已探测可写、1.5T 可用），规避 E051/E134/E166
  - 产物与工具链 ELF 经 binary-sign-tool 自签（E077）；go test 环境 PATH 前置 git 目录（LookPath 探测需要）
- test_package：真实消费打包产物：
  1. `ld-find-code-refs --version` 断言输出含 ld-find-code-refs 与 2.14.0（internal/version 常量）
  2. `ld-find-code-refs --help` 退出码 0 且列出 prune 子命令
  3. 破坏性反向验证：`prune` 空参数必须被 cobra 参数校验拒绝（exit != 0）
- commands.json：CLI 工具（R38），软件级声明 binary=true
- 零上游 patch：源码无需任何修改即可在 OHOS 上构建与测试

## 验证结果

（由实际命令日志回填，日志存设备 tmp run 目录）

- conan-verify：G0-G4 + JC/L0/L1（含 L1e 反向）/L2/L4/L5 全部 pass，见 ci-run-3.log 与 ci-run-4.log
- 上游测试：35 顶层测试函数 + 90 子用例全部通过（0 失败/0 跳过），CI 内 go test 9 包全 ok；逐用例证据见 go-test-verbose.log
- 消费者测试：3 场景 4 断言（--version 两断言、--help 一断言、prune 空参数反向一断言）

## 未做事项

- 未 push（hook 强制拒绝）；未创建/修改 PR；未任务平台提审
- 未修改 ci/**、其他库目录、knowledge/ 正式条目
