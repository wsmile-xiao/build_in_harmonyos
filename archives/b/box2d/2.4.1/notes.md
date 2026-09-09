# box2d 2.4.1 适配笔记

## 前置状态

- 分支：`feat/box2d-2.4.1`
- Issue：待补；2026-09-05 扫描 GitCode 可见 issue 1830 条、2026-09-07 复查最新 open issue，均未发现 box2d 2.4.1 专项 issue。最新 open issue #2764 是其他贡献者（junshi_liu）的 box2d **3.1.1** 知识库扩展 issue（对应 atomgit PR !8658），与 2.4.1 无关。
- 上游 tag：`v2.4.1`
- 上游 commit：`9ebbbcd960ad424e03e5de6e66a40764c16f51bc`
- 源码：`https://github.com/erincatto/box2d/archive/refs/tags/v2.4.1.tar.gz`
- SHA256：`d6b4650ff897ee1ead27cf77a5933ea197cbeef6705638dd181adc2e816b23c2`

## W0 依赖检查

核心 `box2d` 目标没有 `find_package` 或外部 Conan 依赖，只使用 C/C++ 标准运行库。上游 testbed 内嵌 `glad`、`glfw`、`imgui`、`sajson`，但 Conan 配方显式关闭 `BOX2D_BUILD_TESTBED`，因此不引入图形栈依赖，也无需拆分依赖库。

## 构建系统分析

- 构建系统：CMake，上游最低版本 3.8。
- 库目标：`box2d`，默认静态库；支持 `BUILD_SHARED_LIBS`。
- 安装规则：安装 `include/box2d`、库文件和 `box2dConfig` 导出。
- 上游单测：`unit-test` 汇总 5 个 doctest case；上游没有注册 `add_test()`，Travis CI 直接执行 `./bin/unit_test`。

## 配置策略

```text
BOX2D_BUILD_UNIT_TESTS=ON
BOX2D_BUILD_TESTBED=OFF
BOX2D_BUILD_DOCS=OFF
BOX2D_USER_SETTINGS=OFF
```

默认构建静态库，并保留 `shared` Conan option。配方在可执行环境中直接运行上游 `unit_test`，避免把 CTest 的 “No tests were found!” 误当成上游测试通过。

## 本机验证

- 官方源码包下载和 SHA256 校验通过。
- Windows/MSVC 2022、CMake 3.31.6、Ninja 1.12.1 本机上游构建通过。
- 上游 `unit_test` 通过：5/5 test cases，36/36 assertions。
- Conan 2.31.2 + Windows/MSVC 2022 + CMake 3.31.6 执行 `conan create archives/b/box2d/2.4.1 --build=missing` 通过；打包得到 `box2d.lib`、40 个头文件和 CMake 配置文件。
- Conan `test_package` 通过：真实链接 `box2d::box2d`，创建 static/dynamic body 并运行 60 步仿真，6 项断言全部通过。
- 后续一次 GitHub 下载超时；本机 Conan 复验使用同 SHA256 官方源码包经临时本机 HTTP 地址完成，验证后 `conandata.yml` 已恢复为官方 GitHub URL。
- HarmonyOS PC aarch64 真机单包验证通过，详见下节。

## HarmonyOS PC aarch64 验证

- 验证时间：2026-09-05 21:19-21:23（Asia/Shanghai）。
- 运行目录：`/storage/Users/currentUser/ohos-test-runs/codex-box2d-2.4.1-r1-20260905-211013`。
- 验证 commit：`0ceb709439df5d29a1eae9925e9c8dc134c7ebdd`。
- 环境：Conan 2.29.1、Clang 15.0.4、`ohos-aarch64` profile、OHOS 6.0、armv8、Release、静态库。
- 内存控制：CI 使用 `tools.build:jobs=1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、`MAKEFLAGS=-j1`；构建期间 `MemAvailable` 保持约 14 GB。
- 官方源码包双向 SHA256 校验通过：`d6b4650ff897ee1ead27cf77a5933ea197cbeef6705638dd181adc2e816b23c2`。
- 单包 CI 结果：`Total: 1 / Success: 1 / Pass rate: 100.0%`；L0 pass，L1 pass，L2 skip（纯库无 `bin/`），L4 pass（无补丁），L5 pass。
- 上游 `unit_test` 通过：5/5 test cases，36/36 assertions。
- Conan `test_package` 通过：真实链接并运行 `test_box2d`，输出 `box2d consumer test passed`。
- 产物：`libbox2d.a`（345232 字节）、40 个头文件、3 个 CMake 配置文件；`readelf` 确认归档成员为 ELF64 AArch64 relocatable。
- 远端源码包由本地 `git archive HEAD` 生成；远端仅为执行 CI 对归档中的 CI shell/config 行尾做了 CRLF 转 LF处理，未改变配方和提交内容。

## 第二台真机复验（2026-09-07）

- 验证时间：2026-09-07 23:33 - 2026-09-08 00:12（Asia/Shanghai）。
- 设备：`10.62.134.118:2222`（第二台 HarmonyOS PC 真机，HongMeng Kernel 1.12.0 aarch64；首台经 frp-tip.com 访问）。
- 验证 commit：`691fb3638c`（rebase 后 HEAD；`archives/b/box2d/2.4.1` 与首次真机验证内容逐字节一致）。
- 源码包：本地 `git archive HEAD`，327178240 字节，MD5 `0ff92e14e68ea82b4bb3a70248fd3919` 双向校验一致；远端解包至 `$HOME/tmp/box2d-ci`。
- 环境：Conan 2.29.1、`ohos-aarch64` profile、clang++ 15（`/data/service/hnp/bin/clang++`）。
- 内存控制：设备 global.conf 追加 `tools.build:jobs=1`、`CMAKE_BUILD_PARALLEL_LEVEL=1`、`MAKEFLAGS=-j1`；全程 `MemAvailable` 16.7-17.6 GB，无关机风险。
- 结果：`Total: 1 / Success: 1 / Pass rate: 100.0%`；L0 pass、L1 pass（L1a/L1b/L1c + L1e 破坏性负向测试）、L2 skip（无 `bin/`）、L4 pass、L5 pass；`ci-metadata.json` 正常生成。
- 上游 `unit_test` 与 `test_package` 均真实执行（`box2d consumer test passed`）。
- 该设备环境差异及处理（仅设备副本，不改仓库）：
  1. `/tmp` 只读：`TMPDIR=$HOME/tmp` + zsh `TMPPREFIX=$HOME/tmp/zsh`（here-doc 临时文件走 `/tmp/zsh`，不吃 TMPDIR）。
  2. 设备无 `bash`：设备副本 `build_and_test.sh` 两处 `bash ci/scripts/*.sh` 改为 `/bin/sh`（knowledge_check/junk_check 为 POSIX 兼容，实测通过）。`$HOME` 用户存储区新建文件禁止 exec，垫片方案不可行。
  3. CRLF：`ci/`、`config/` 全部文本文件 `sed -i 's/\r$//'`（build_timeouts.txt 的 `\r` 会破坏整数校验）。
  4. 设备无 `git`：G0e 处告警非致命，`source_trace.commit` 记为 unknown，不影响门禁结论。
- 本地存档（会话临时）：`.tmp/box2d-device-run/{build.log,ci-metadata.json}`。

## 下一步命令

已完成真机单包验证命令：

```sh
CI_PACKAGES="archives/b/box2d/2.4.1" zsh ci/conan/build_and_test.sh
```

后续如需 shadow CI 复验，使用：

```sh
/path/to/run-ohos-shadow-ci.sh archives/b/box2d/2.4.1
```

## 2026-09-07 rebase 记录

- origin/main 前进 218 个提交后执行 rebase：`git rebase origin/main`（基点 `2444511e32`）。
- rebase 后提交哈希更新：`67e702f92a`（feat）、`aa25d575e6`（test 记录）；`archives/b/box2d/2.4.1` 内容与真机验证时的提交（`0ceb709439`）逐字节一致，真机验证结论继续有效。
- rebase 前对 worktree 中无关的 `archives/l/libXext/{README.md,manifest.yaml}` 后台噪音改动设置了 `git update-index --skip-worktree`（本地索引标记，不进提交；恢复用 `--no-skip-worktree`）。
- 推送命令（issue 补齐后执行）：

```sh
git push fork feat/box2d-2.4.1
```

## 阻塞点

- issue 编号待创建或补充。
- issue 补齐前暂不推送、不创建 PR。
- 项目内另有贡献者在适配 box2d 3.1.1（issue #2764 / atomgit PR !8658），2.4.1 与 3.1.1 并存是否符合仓库预期，建议在创建 issue/PR 时与维护者确认。

## 结束标记

**最终状态**: 本机前置适配与 HarmonyOS PC aarch64 真机单包验证完成，已 rebase 到最新 origin/main；待补 issue 后推送并创建 PR。
