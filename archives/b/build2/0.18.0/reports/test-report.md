# build2 0.18.0 验证报告

## 上游测试清单

`INVENTORY_COUNT=51`

官方 `build2-0.18.0.tar.gz` 的 `tests/**/*.testscript` 共 51 个：

- 47 个由各目录 `buildfile` 声明的可运行 `testscript{stem}` 目标；
- 4 个 `common.testscript` 官方 harness 输入。

完整清单见
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\upstream-test-inventory-r7.txt`。
Phase 1 的 `b/b-boot --version` 只作为 bootstrap smoke test，不计入这 51 项。

## 上游完整执行

- 执行环境：WSL 全新官方源码副本
- 上游命令：`b/b config.bin.lib=static -s test`
- discovered：51
- executed：51
- passed：51
- failed：0
- skipped：0
- 返回码：0
- 通过率：`51/51 (100%)`
- 日志：
  `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\wsl-upstream-tests-r7.log`
- 日志 SHA-256：
  `149069D87DA6819A3B9B6C05BD565FD00E2A0DE4AB774B9BDF38BBD005E952A6`

执行使用 build2 官方根级 runner，由 buildfile 解析类型化目标。未把原始
`*.testscript` 路径作为 `file{...}` 目标运行。任务私有副本仅删除 libbutl
发布快照中带悬空 ODB 链接的可选测试子树；该子树不属于 build2 的 51 项测试，
build2 自身测试文件未修改、未排除。

## 配方执行入口

`conanfile.py` 在 Phase 2 生成 `b/b` 后盘点并强校验 51 个
`tests/**/*.testscript`，再运行同一官方根级命令。返回码非零、清单不是 51、
4 个 harness 数量漂移或任一可运行目标缺少 runner 标记都会使构建失败。
因此 CI 的 `conan create` 必须重新执行完整 51 项上游测试，然后再执行
`test_package` 的 `build2 --version` 消费者探针。

libbutl 0.18.0 发布快照中的 `libbutl-pkg-config/libpkg-config/*` 是指向
`upstream/libpkg-config` 的悬空链接；配方 `source()` 额外下载官方
`build2/libpkg-config` v0.1.3 归档到该路径，保证 `libpkg-config/pkg-config.h`
及其 C 源码在 Phase 2 的导出配置中可见。该源码闭包也必须在 CI 中用 SHA-256
重新校验，不能依赖 worker 的预装文件。

libbutl 的 Linux UUID backend 还会在运行时按 SONAME
`libuuid.so.1` 调用 `dlopen()`。OHOS Worker 没有该系统库，配方因此从已发布的
`uuid/2.40.1` 静态 PIC 包生成任务私有 `libuuid.so.1`。正式 bootstrap 前必须由同一
目标 C 编译器生成新的原生探针，使其 `DT_NEEDED` 绑定该 SONAME；探针在已设置的
`LD_LIBRARY_PATH` 下启动新进程，实际调用 `uuid_generate`、检查 DCE variant，并按
libbutl 的强 UUID 分支在非 v4 时调用 `uuid_generate_time_safe`。该预检失败即停止，
不得运行或统计上游 suite；通过后仍必须由原官方 runner 完整执行 51 项。

## 目标执行边界

目标 OHOS W3 r6 在 Phase 2 静态重建时报告
`ios_base::failure: Operation not permitted`（RC=134），未进入该 run 的上游
51 项测试或消费者探针。该失败保留为真实目标证据，不与 WSL `51/51` 拼接为
目标 PASS：

- 目标日志：
  `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\w3-r6-runner.log`
- 目标日志 SHA-256：
  `3BA1CD359748C8666FD6255E76DCD9DECB4B315925FF9C096C284FB36B822464`

此前 r4 目标 Conan create 与同一 `test_package/test.c` 消费者探针曾独立通过：

- 消费者测试：`1/1 (100%)`
- RREV：`43cc11a5a690b0403c56f194b16375fe`
- Package ID：`4b977264131a1c74e82bd6bb51b63cc9aadc4cfa`
- PREV：`241f06ad352dce9b0991752c92bc1ecf`

该历史消费者结果不代表当前 r6，也不替代当前候选在平台 CI 中必须完成的
Phase 1、Phase 2、上游 `51/51` 和消费者 `1/1`。

## CI #38637 G0e 阻断

Buildbot #38637（buildid `44080`，revision `a7dba8102b7c153c2cbc9c4d318ac826bb768416`）
在 `conan-build-test` 的 G0e 根目录白名单阶段发现当前主线临时文件
`test_push.txt`，返回码为 1，未进入 Phase 1、Phase 2、上游 51 项或消费者探针。
完整 59 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38637-conan-build-test.log`，
SHA-256 为 `A3DA3FCBAE45982A9A956BD99E2BCBD02F6FCE260C3DB2E308A98BD000D9EC95`。
该结果是主线根目录漂移的真实阻断证据，不计入上游测试分母；删除该已确认临时文件
后必须以新候选重新通过 G0e，并完整执行 `51/51` 与 `1/1`。

## CI #38714 差异应用阻断

Buildbot #38714（buildid `44158`，revision `74398fe45fb14b2398d0cad5a520b47182da508d`）
在应用 PR diff 阶段发现主线已由提交 `36cf4efc3` 删除 `test_push.txt`，旧候选的
重复删除因此报 `error: test_push.txt`、`test_push.txt: does not exist in index`，随后
以 RC=1 在 G0e 前退出。完整 54 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38714-conan-build-test.log`，
SHA-256 为 `EAE906B2D791CCD1A9D5052DE03CDD6D73BDC7921FA36E27572C3EC5558EFA63`。
该结果不包含任何上游测试；同步最新 `main` 后必须以新候选重新通过差异应用、G0e、
Phase 2、上游 `51/51` 和消费者 `1/1`。

## CI #38733 上游测试参数阻断

Buildbot #38733（buildid `44178`，revision `1eb96b517b4b83578a1dacb0c5c76e3e8eb1a8bd`）
已完成 Phase 2 并生成 `b/b`，但运行上游根级 test operation 时目标程序报告
`error: not built with default C++ compiler`、`info: use config.cxx to specify`。
原 recipe 没有把 Conan conf 中解析的 OHOS C++ 编译器传给测试命令，故 51 项均为
失败（`discovered=51, executed=51, passed=0, failed=51, rc=1`），未执行消费者探针。
完整日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38733-conan-build-test.log`，
SHA-256 为 `6B37039B6AAD33EF57EE13E540A7A08C38E00E5D09A5F954799C7A4F943FB44C`。
配方现将 `config.cxx=<absolute cxx>` 与 `config.bin.lib=static` 一并传给同一官方
根级 runner；测试分母仍固定为 51，不能用 WSL 结果替代新的 CI 终态。

## CI #38791 主线根文件阻断

Buildbot #38791（buildid `44238`，revision `921ab048595f2a8a959f92f43032b601813ccdc5`）
在 G0e 根目录白名单阶段发现当前主线新增的 `BUILD.gn`、`oh-package.json`，返回
RC=1，未进入 Phase 1/2 或任何上游测试。完整 59 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38791-conan-build-test.log`，
SHA-256 为 `3A00887B33D094DE354C6778CD3DEA20E65F6B8EBF24AD8E83DA9478A05E7FCA`。
同步最新 `main` 后这些文件已属于基线，当前 PR diff 不重复删除；必须以新的候选
重新通过 G0e，再完整执行 `51/51` 和 `1/1`。

## CI #38855 白名单阻断

Buildbot #38855（buildid `44310`，revision `8e33b924aa86de7c4e1f9f8301bd619017e1747f`）
在 G0e 根目录白名单阶段再次发现 `BUILD.gn`、`oh-package.json`，返回 RC=1，未
进入 Phase 1/2 或任何上游测试。完整 62 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38855-conan-build-test.log`，
SHA-256 为 `7E21A9BBEAA4B4850E1AAA40E930AD045C6455CA5416336F068249A910C9CF6E`。
固定白名单是当前 CI 的权威门禁；候选已精确删除这两个主线文件，必须用新 HEAD
重新通过 G0e，并完整执行 `51/51` 与 `1/1`。

## CI #38924 checkout 边界阻断

Buildbot #38924（buildid `44383`，revision `85b67ec7af9a6e992b21a7c3b10bae8694d7788b`）
在 G0e 阶段仍报告 `BUILD.gn`、`oh-package.json`，返回 RC=1，未进入任何配方或
上游测试。完整 59 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38924-conan-build-test.log`，
SHA-256 为 `75FB445105A65585DC3C16F5F475A26D1CB9D74284032E7F09AC07AC9A272FEE`。
远端分支对这两个路径均返回 404，PR 文件列表也标记为 deleted；因此该结果记录
为 CI checkout/diff 应用边界，不计入上游测试分母。新 HEAD 必须重新通过 G0e。

## CI #39023 上游测试失败

Buildbot #39023（buildid `44483`，revision `6929492f1c5b496e6d6e40fbc6a747a2e00b13b9`）
已通过 checkout、G0e、Phase 1/2 编译并进入官方根级 test operation，但在测试更新阶段
递归处理 Conan 生成目录 `build-release/conan`，返回
`no explicit target for build-release/:dir{conan/}`。因此终态为
`discovered=51, executed=51, passed=0, failed=51, skipped=0, rc=1`，51 项均未获得
可执行目标标记，消费者 `test_package` 未运行。完整机器人日志见
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\pr-7775-comments-ci39023.json`，
页面快照见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39023.html`。

根因是 Conan `basic_layout` 的 `source_folder` 与 `build-release` 同级，recipe 在
复制工作树时未排除 `self.build_folder`，把生成的 `conan/` 元数据带入上游源码。修复
按 `self.build_folder` 相对路径计算根目录并仅在 `copytree` 的源根排除它；上游源文件、
libbutl/libpkg-config 和 51 项清单均不变。下一候选必须重新执行完整 CI，不能将本次
失败与 WSL `51/51` 结果拼接。

## CI #39085 源码下载超时

Buildbot #39085（buildid `44545`，revision `777c5a6ef3c816a0695d8e21e7a6cd4678ac0523`）
已通过 checkout、G0e 和质量门禁，但在 Conan `source()` 获取
`https://git.build2.org/cgit/build2/snapshot/build2-0.18.0.tar.gz` 时发生
`ConnectTimeoutError`，重试后终止；未执行编译、上游 51 项测试或消费者探针。完整
机器人日志见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\pr-7775-comments-ci39085.json`，
页面快照见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39085.html`。

为保持官方来源和可复现性，已验证官方 GitHub tag 归档：

- `https://github.com/build2/build2/archive/refs/tags/v0.18.0.tar.gz`：1,700,016 bytes，
  SHA-256 `5F5237390A66FCA11E5901D446402DC8CE333E78A6F0262DE95BEE4613F37F29`；
- `https://github.com/build2/libbutl/archive/refs/tags/v0.18.0.tar.gz`：551,222 bytes，
  SHA-256 `527A24C4C787139C8C3B801973B190808FD1C3C6A538960E90DA19A3AB50218A`。

两者哈希与原 cgit 归档完全一致，未改变源码内容或测试分母。新的 CI 必须在该 URL
闭包上完成 Conan create、官方根级 runner 的 `discovered=51, executed=51, passed=51,
failed=0, skipped=0, rc=0`，以及消费者 `1/1`；下载失败或测试未执行时不得宣称通过。

## CI #39194 上游 bash 测试失败

Buildbot #39194（buildid `44654`，revision `7b76b4bac8f54eec0d5b2eaf6b670ba27850bd11`）
已成功从官方 GitHub 归档下载源码并完成 checkout、G0e、Phase 1/2 编译，随后进入
上游 test operation。`tests/bash/testscript:96` 的真实执行失败，stderr 为
`shell-init: error retrieving current directory: getcwd: cannot access parent directories:
Permission denied`；因此终态为 `discovered=51, executed=51, passed=0, failed=51,
skipped=0, rc=1`，消费者 `test_package` 未运行。该失败不是下载问题，也不能通过减少
上游分母或排除 bash 测试解决。完整 live 日志已保存为
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39194-live.log`。

根因是 Phase 2 需要 `/data` 的替换/锁语义，而 Bash 测试需要可遍历的 `/storage`
cwd，单一工作根不能同时满足。修复保持 Phase 1/2 在已探测的 `/data` 根执行；生成
`b/b` 后，把完整已构建源码树复制到平台已用于启动 zsh 构建的 `CI_REPO_ROOT`，
要求 `bash`/`sh -c pwd` 返回 0 且 stderr 为空，再从该副本运行同一个官方根级 runner。
Conan build 目录仅作为第二候选。上游测试文件不修改、
不排除，测试 HOME/TMP 也绑定到该副本。下一次 CI 必须再次完成完整 51 项上游
testscript 和消费者探针，并以新的终态日志确认 `passed=51, failed=0`。

## CI #39308 codeload 解包失败

Buildbot #39308（buildid `44778`，revision `d44b5870d77da0bfccfd6c7f9fab688608e2ecbf`）
能够读取 codeload URL，但 Conan `get()` 将无扩展名的 `v0.18.0` 保存名当作 ZIP，
在 `source()` 第一个归档处报 `BadZipFile: File is not a zip file`，约 17 秒终止。
没有进入编译或上游测试；日志见
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39308-conan-build-test.log`。

修复在 `get()` 中显式绑定 `filename` 为 `.tar.gz`，不改变 URL、归档内容或 SHA-256。
下一次 CI 必须通过源码解包并完成完整 51 项上游测试和消费者 `1/1`，不能把下载成功
或本地哈希验证当作测试通过。

## CI #39317 过早工作根门禁失败

Buildbot #39317（buildid `44787`，revision `71831bc36a3d7d2efc9371d22f97e7b60ef01f4f`）
已成功下载并解包 build2、libbutl 和 libpkg-config 三个官方归档，但在 `build()`
选择工作根时，先前加入的 shell cwd 检查拒绝了所有 `/data` 候选，报
`build2 requires an OHOS work root whose shell can resolve cwd`，未进入编译或测试。
日志见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39317-conan-build-test.log`。

该失败证明 shell cwd 不是 Phase 2 工作根的合法前置条件。修复按阶段分离根能力：
Phase 1/2 仍在 `/data` 完成，之后将完整已构建测试树复制到经 shell cwd 探针的
`CI_REPO_ROOT`，并从该副本运行全部 51 项。不得拼接 #39194 的 Phase 2 与新 run 的测试；
下一次 CI 必须在同一 revision 内从源码获取到消费者探针全程通过。

## CI #39337 Conan cache 测试根仍不支持 getcwd

Buildbot #39337（buildid `44808`，revision `181a903ce1815ace2781ccd3268d06dfa0f641c6`）
完成了三个源码归档校验、Phase 1/2 和 `b/b --version`，随后将完整树复制到 Conan
`build-release` 下。该副本的 shell cwd 探针仍返回
`shell-init: error retrieving current directory: ... Not supported` 和
`pwd: ... No error information`，配方按预期阻断，未执行上游 51 项或消费者探针。
日志见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39337-conan-build-test.log`。

平台同一构建已在 `CI_REPO_ROOT` 中成功启动 zsh，因此下一候选优先在该权威工作根
创建完整测试副本并再次执行 shell cwd 探针；仅通过后才运行官方根级 51 项 runner。
该修复保持测试文件、目标和分母不变，不能把 #39337 的 Phase 2 与后续测试拼接。

## CI #39276 libbutl 下载超时

Buildbot #39276（buildid `44742`，revision `9bfc684321a56396bfb37ee096a336ba8ed20f81`）
在源码阶段下载 build2 主归档后，访问 `github.com/build2/libbutl` 的 tag 归档时
连续超时并终止；没有进入编译或任何上游测试。步骤终态为 `conan-build-test=2`，
日志见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39276-conan-build-test.log`。

build2 主归档显示通过 `gh-proxy.com` fallback 命中缓存，不能据此推断 libbutl
也可达。为消除主站域名差异，配方现在统一使用 GitHub 官方 codeload tag 端点：
`https://codeload.github.com/build2/build2/tar.gz/refs/tags/v0.18.0` 和
`https://codeload.github.com/build2/libbutl/tar.gz/refs/tags/v0.18.0`。本地下载的
两个归档分别为 1,700,016 和 551,222 bytes，SHA-256 与原 cgit 归档完全一致，
源码闭包和测试分母不变。下一次 CI 必须重新完成 Phase 1/2、上游
`discovered=51, executed=51, passed=51, failed=0, skipped=0, rc=0` 和消费者 `1/1`。

## CI #39372 CI_REPO_ROOT 测试根仍不支持 getcwd

Buildbot #39372（buildid `44843`，revision
`20f113f170e731c8c7693fbf8f4de62bfe2ea57e`）成功校验并解包三个官方源码归档，
完成 Phase 1/2 和 `b/b --version`。配方随后先后把完整树复制到 `CI_REPO_ROOT` 与
Conan build-root 子目录，但 Bash cwd 探针分别报告
`getcwd: ... Not supported` 和 `pwd: ... No error information`，因此在 51 项上游测试
启动前按合同失败，消费者也未运行。完整 187,910 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39372-conan-build-test.log`，
SHA-256 为
`67E7F669F0933FB7D04724D37F0708B76620A7DEF2F2538DDC3CA66317FC63DF`。

该结果证明问题不在某个具体 `/storage` 子目录，而在 libbutl 为嵌套子进程切换 cwd 后
仍保留父进程 `PWD`，Bash 因二者不一致而在读取脚本前进入失败的 `getcwd()`。新候选不再
迁移或修改测试树，只在 OHOS 测试进程 `PATH` 首位放置任务私有 `bash` 包装器：包装器
以 `/system/bin/sh` 启动，用系统 `readlink /proc/self/cwd` 取得每次启动的真实测试 cwd，
导出匹配的 `PWD`，再以原 cwd 和原参数执行真实 Bash。测试前必须通过 RC=0、空 stderr、
精确 cwd 的包装器探针，测试前后复算
全部 51 个 `.testscript` SHA-256 并要求字节不变。WSL 定向夹具还在故意错误的 `PWD`
环境下验证了真实 cwd、脚本 `$0`、含空格参数和内部环境清理；夹具 SHA-256 为
`12C717C0AE24C77F71E84B7B1965B8417CAEE7B73CAD5D036F56CF8B3294A33A`。该夹具只证明
启动包装器的控制流，目标平台仍必须重新给出
`discovered=51, executed=51, passed=51, failed=0, skipped=0, rc=0` 和消费者 `1/1`。

## CI #39451 libpkg-config redirect endpoint 下载超时

Buildbot #39451（buildid `44924`，revision
`49f50abe58e88c7edaa0fb559e87d61781387be4`）在同一 `source()` 中已从
`codeload.github.com` 成功下载并解包 build2 与 libbutl；随后访问
`https://github.com/build2/libpkg-config/archive/refs/tags/v0.1.3.tar.gz` 时连续
连接超时，在编译与全部 51 项测试前退出。自动 pre-download 还明确报告 Worker
不存在 `curl`，因此没有产生可供 Conan 复用的缓存。完整日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39451-conan-build-test.log`，
SHA-256 为
`8061527F0DC8B2494AB232A7458E5EA22A3D22D241971C8AE93F64046BCFF8FA`。

修复将第三个归档改为官方直接 codeload tag 端点
`https://codeload.github.com/build2/libpkg-config/tar.gz/refs/tags/v0.1.3`。本地重新下载
得到 46,798 bytes，SHA-256 仍为配方固定的
`147C196B5128EE2639D9710C7572F6D312F1E2A65FB360C4E85F8369C2198357`，证明 URL
切换不改变源字节。由于该 URL basename 没有归档扩展名，`get()` 同时显式指定
`filename=libpkg-config-0.1.3.tar.gz`，避免重现 #39308 的 ZIP 误判。新 CI 仍须在
同一 revision 内从三个源码下载一直执行到 51/51 与消费者 1/1；本次下载失败不计入
任何测试通过数。

## CI #39485 UUID 运行时阻断

Buildbot #39485（buildid `44958`，revision
`90950bf39828e407722d141d74201171053fe1f4`）成功取得三个官方归档、完成 Phase 1/2、
通过稳定 cwd 包装器探针，并真实启动 build2 官方根级 runner。在
`tests/function/builtin/testscript:165:5` 的 `generate_uuid()` 场景，子进程按固定
SONAME 加载 `libuuid.so.1` 失败，runner 以 RC=1 终止：

```text
error: unable to generate uuid: unable to load libuuid.so.1:
Error loading shared library libuuid.so.1: No such file or directory
```

终态只能记录为 `discovered=51, runnable=47, support=4,
execution_accounting=unavailable_after_nonzero_runner, rc=1`；消费者没有运行。完整日志：
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39485-conan-build-test.log`，
SHA-256
`7D69ECA447C61490C69C096FA2C619B0C6FEB1CD05A6B296A284CF845D783150`。

W0 使用 `--build=never` 取得 `uuid/2.40.1` 的 OHOS armv8 静态 PIC binary（RREV
`e05bc8e141027fc5222bdc9401aac2db`、Package ID
`21b17f8b2bc0e9511e276e3d57a23893067cefe5`、PREV
`b73be30a008ebc36b81b7863932cb7a5`）。本地链接夹具从该 `libuuid.a` 生成 29,040-byte
AArch64 ELF DYN，SONAME 为 `libuuid.so.1`，导出 `uuid_generate`、
`uuid_generate_time_safe` 与 `uuid_unparse_lower`，SHA-256
`4C43BCEA5FAB3B0211F47C155AEC1FC349DE48845D69720B3833A9BED045A178`。这些只证明
依赖与链接闭包可形成；最终通过仍只认新 HEAD 平台 CI 的完整 `51/51` 与 `1/1`。

## CI #39557 Python ctypes 预检闭包失败

Buildbot #39557（buildid `45030`，revision
`77415b216dac1b4bc2125584dbb454890cede943`）通过 L0/KC/JC，精确下载
`uuid/2.40.1#e05bc8e141027fc5222bdc9401aac2db` 的 Package ID
`21b17f8b2bc0e9511e276e3d57a23893067cefe5`、PREV
`b73be30a008ebc36b81b7863932cb7a5`，并进入 `build()`。私有 `libuuid.so.1` 生成后，
旧预检尝试导入 Python `ctypes`，目标 `_ctypes` 扩展先因缺少 `libffi.so.8` 失败：

```text
ImportError: Error loading shared library libffi.so.8:
(needed by .../_ctypes.cpython-312-aarch64-linux-ohos.so)
```

该 run 在 23.878 秒时终止，未启动 bootstrap、上游 51 项或消费者测试。完整日志：
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39557-conan-build-test.log`，
SHA-256
`D4875BE02742D79C0A50D0E6FA08697AA10AF37972F4BCDB34CD39C06D7077EE`。

修复移除 Python/ctypes 闭包，改由目标 `cc` 编译一个直接引用 `uuid_generate` 和
`uuid_generate_time_safe` 的原生 C 探针，并链接刚生成、带精确 SONAME 的私有共享库。
探针作为新目标进程运行，验证 loader 搜索与真实强 UUID 语义；通过后才进入完整
bootstrap 与官方 runner。该定向修复仍需新 HEAD CI 证明 `51/51` 与消费者 `1/1`。

## CI #39608 OHOS `cat --squeeze-blank` 能力缺口

Buildbot #39608（buildid `45081`，revision
`1c0aea5b3ebdc27973431e34be0bdc1b10129e9c`）通过原生 UUID 目标探针、Phase 1/2、
`b/b --version` 和稳定 cwd 包装器探针，并真实启动同一个官方根级 51 项 runner。
运行到 `tests/function/process/testscript:43:5` 时，上游调用外部
`^cat --squeeze-blank f`，OHOS 系统 `cat` 返回：

```text
cat: Unknown option 'squeeze-blank' (see "cat --help")
error: process cat exited with code 1
```

runner 因此以 RC=1 fail closed；终端只确认 `discovered=51, runnable=47,
support=4, execution_accounting=unavailable_after_nonzero_runner`，后续 31 个 runnable
目标没有终端，消费者测试未运行。完整 191,138 行日志保存在
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-39608-conan-build-test.log`，
SHA-256 为
`930C9C1E721B93343E44411941DFA4490D2A787AE5593901AD17BA72D8AF0DBD`。

修复不修改、排除或重写任何 testscript。配方只在 OHOS 测试专用任务目录中，用同一
目标 `cc` 构建一个 `cat` 前端并置于 `PATH` 首位：`-s/--squeeze-blank` 按字节流
压缩连续空行，普通调用通过 `execv` 原样交给在改写 PATH 前解析的真实平台 `cat`。
正式 suite 前必须分别通过精确输出的 squeeze 探针和普通透传探针。配方 AST 直接
提取的 2,299-byte C 源码已在宿主用 `-Wall -Wextra -Werror` 编译，并对长/短选项、
stdin、多文件边界和透传逐字节通过；源码 SHA-256 为
`02B6D5268F1B805249A9151CA8E23B9CAEEE981D67178D64B9B809919A6556F7`。该宿主结果
不冒充目标执行；新 HEAD 仍必须在 OHOS CI 中完成完整 `51/51` 与消费者 `1/1`。
