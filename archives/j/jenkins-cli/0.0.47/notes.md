# jenkins-cli (jenkins-zh/jenkins-cli) 0.0.47 适配笔记

## 概述
- **软件**：Jenkins CLI（二进制 `jcli`），管理 Jenkins 的命令行工具（Go）。
- **上游**：https://github.com/jenkins-zh/jenkins-cli（tag v0.0.47）
- **语言/构建**：Go（go.mod `go 1.23`），CGO_ENABLED=0 纯静态。
- **目录**：`archives/j/jenkins-cli/0.0.47/`（与已有 `archives/j/jenkins` 服务端包独立）。
- **源码包 sha256**：`4e78600e214c357c08a0a83fe9cc59214b0d050de07dbb469d9f226c8c37eabc`
  （archive/refs/tags/v0.0.47.tar.gz 与 codeload 均一致，已核对）。

## 本轮（首个 pre-PR 适配轮）背景
- 上一轮 hmbs preflight 报 `incomplete / evidence：无法读取当前 archive 代码树`。
  根因：工作树为空（无 archive 配方目录、master 无提交），preflight 无代码可验证。
- 处理：拉取 upstream main，建 `feat/jenkins-cli-0.0.47` 分支，创建完整配方目录，
  使真机 preflight 有代码可编译/测试。

## 依赖分析
- Go 工具链 >= 1.23（go.mod 要求）。hmbs 预检沙箱只注入 cmake/make/ninja/python3；
  配方先探测设备 go，缺/过旧则从 Aliyun Go 镜像自举 go1.26.5（sha256 校验，复用本
  仓库 vibecheck/1.7.7 + algernon/1.17.10 已验证哈希）。
- 纯 Go 依赖（cobra/viper/survey/go-keyring/ginkgo/testify…），无 C 依赖。
- 无需其他已发布包。

## 关键适配点
1. **OHOS ELF 签名**：未签名 ELF 无法 exec。go 工具链 ELF + 最终 jcli 均需
   binary-sign-tool 签名（`llvm-objcopy --remove-section .codesign` → `sign
   -selfSign 1 -signAlg SHA256withECDSA`）。次轮真机若发现签名路径/工具名差异再微调。
2. **HMDFS link 限制**：go link mmap 输出失败；链接输出 + GOCACHE/GOMODCACHE/
   GOTMPDIR/TMPDIR 指向 ext2 工作区（`/data/storage/el2/base/cache` 优先）。
3. **go test 测试二进制签名**：`go test -exec` 签名包装器（sign → exec）。
4. **版本注入**：上游 goreleaser 用
   `-X github.com/linuxsuren/cobra-extension/version.version=<ver>`；配方注入
   `v0.0.47`，`jcli version` 输出 `Version: v0.0.47`。
5. **构建次序**：先构建并签名 jcli、置入 PATH，再 `go test -v ./...`（这样
   e2e/without_jenkins 的 completion 用例能 exec 到 jcli）。
6. **模块预取**：`go mod download -mod=mod`（多代理 GOPROXY + 重试）预取
   test-only 依赖，避免 go test 阶段集中下载失败。

## 上游测试统计
- 口径：go test 函数计数（`go test -v ./...` 顶层 `--- (PASS|FAIL|SKIP): Test*`
  行，ginkgo 包按唯一 Test* 入口计 1）。全模块 **40** 个（详见
  reports/upstream-tests.md 与 test_package/MANIFEST.yml 的 per-file 盘点）。
- 可运行：**23**（单元 19 + e2e/without_jenkins 4）。
- environment gap：**17**（根 e2e/ 14 + e2e/withdependencies 3）——这些是“活
  Jenkins 集成测试”，TestMain 在无 JENKINS_VERSION 时直接 return（不 m.Run），真机
  无 Jenkins 环境，go test 对其输出 `ok <pkg>` 且 0 判定。非缺依赖。

## test_package（L1 消费级）
- test.sh 两项断言（R34 反空壳，真实执行打包 jcli）：
  1. `jcli version` → 含 `Version: v0.0.47`（ldflags 注入验证）
  2. `jcli --help` → usage 文本（枚举 Jenkins CLI 子命令）
- test.sh 用显式计数器（非 stdout 字符串计数）发出 `HMBS_TEST_PACKAGE_RESULT`
  （discovered=2 / passedCount 实数）。

## 真机预检（HMBS 自动执行，本机不直接跑 conan）
- conanfile.py build() 运行上游 `go test -v ./...`，解析判定行发出
  `HMBS_UPSTREAM_TEST_RESULT`；test_package 运行冒烟发出
  `HMBS_TEST_PACKAGE_RESULT`。
- 预检日志返回后将据 real 计数回填 notes.md / reports，并在 PR 正文如实写通过率
  （含 17 个未运行用例说明，不写 100%）。

## 验证结果（真机预检，2026-09-29）
- 编译：conanfile.py 构建/签名 jcli、置入 PATH、go test 真实执行（真机实测）。
- 上游 go test -v ./...（go-test 函数口径）：**发现 40，执行 21，通过 17，
  失败 4，跳过 0**。
  - 17 环境 gap：根 e2e/（14）+ e2e/withdependencies（3）活 Jenkins 集成
    测试（TestMain 无 JENKINS_VERSION 直接 return，0 判定）。
  - 4 test_failure：completion 输出断言失败（TestZshCompletion 等，cobra
    GenZshCompletion/GenBashCompletion/GenPowerShellCompletion/GenFishCompletion
    输出不满足上游断言，如 `#compdef _jcli jcli` 缺失或内容差异）。
- 上游通过率（PR 正文口径）：17/40 通过；23 个未通过 = 4 失败 + 19 未运行
  （17 环境 + 实际无判定）。**不写 100%**。
- test_package（L1）：2/2 通过（jcli version + jcli --help 冒烟）。

## rule4 缺口核算（本轮修复）
- rule4 强制 `gaps 总数 == discovered - passed`。旧实现 gaps 只计
  skipped + not_executed（19），漏计 4 个 FAILED → 报“说明覆盖 19 项但实际
  缺口 23 项”被拒。
- 修复：conanfile.py 把 failed>0 计入 `test_failure` gap（4），连同
  environment（19）/ ohos_feature（skipped）gap，使 gaps 总数 = 23 = 40-17。
- 恒等式：passed+failed==executed（17+4=21）；executed+skipped<=discovered
  （21+0<=40）；五字段非负整数；gaps 总数恒等于 discovered-passed。
- status：failed>0 → failed（本次 4 失败，如实标 failed，不伪装通过）。

---

**编译验证**：2026-09-29（语法级）→ 真机预检待 hmbs
**最终状态**：built（待真机证据确认）

---

## 本轮（真机 compile 失败修复，2026-09-29）

真机 preflight 在 compile 阶段失败，两个配方缺陷（非源码下载失败，源码包已正常解包到 go build）：

1. **`go mod download -mod=mod` 报 "flag provided but not defined: -mod"（3 次重试全 rc=2）**
   - 根因：配方自举 go1.26.5 中，Go 1.26 移除了 `go mod download` 子命令的 `-mod` 标志。
   - 修复：`_prepare_upstream_modules` 去掉 `-mod=mod`（模块解析已由环境 GOFLAGS=-mod=mod 钉死）。
2. **`shutil.copy2(final_bin, path_bin/jcli)` 报 PermissionError EPERM**
   - 根因：`copy2 -> copystat -> os.chmod/chown` 在 hmdfs 的
     `/data/storage/el2/base/cache/conan-go-build/.../bin` 树被拒（HMBS 平台能力 chmod:0）。
   - 修复：新增 `_copy_binary()`（`shutil.copyfile` 只拷内容 + 尽力 chmod 755，失败仅 debug），
     用于 build() 置入 PATH 的拷贝，并把 `_build_jcli` 的 final_bin 拷贝也统一改用之。
- 验证：`python3 -m py_compile` 通过。待 hmbs 真机复跑。

## CI R38（L0k commands.json）
- CI 构建 #64842 在 L0k 门禁失败：`CLI tool detected but commands.json missing (R38)`。
  根因：jenkins-cli 是 application 型 CLI（package_type=application + bindirs bin），
  软件级目录 `archives/j/jenkins-cli/` 缺少 `commands.json`。
- 处理：新增 `archives/j/jenkins-cli/commands.json`（`type=tool`，`name=jenkins-cli`，
  versions 含 `0.0.47`，`binary:true`），参照 templates/commands.json.template 与
  archives/s/strace/commands.json 示例。L0k 校验脚本实测 PASS。
