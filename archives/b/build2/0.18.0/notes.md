# build2 0.18.0 适配笔记

## 编译环境
- 构建系统: custom (`bootstrap.gmake`)
- 编译日期: 2026-09-03
- 目标编译器: OHOS arm64 clang 15 (`aarch64-unknown-linux-ohos-clang++`)
- 目标设备: `10.62.195.15:8022` (`ohos`)
- 状态: built（WSL 配方构建与上游测试通过；目标 W3 r6 在 Phase 2 失败）

## 编译步骤

下载官方 `build2-0.18.0.tar.gz` 与 `libbutl-0.18.0.tar.gz`，在任务私有
OHOS arm64 工具链中执行 Conan `create`。配方从
`tools.build:compiler_executables` 解析 C++ 编译器，绑定任务私有 `TMPDIR`，
并把 `libbutl-0.18.0` 保持在 Conan source tree 内。Phase 1 bootstrap 生成
`b/b-boot`，再复制为 `bin/build2` 与 `bin/b`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess` 不存在 | 官方快照保留空 symlink | 在任务源码副本中补入标准 GNU config.guess/config.sub |
| 2 | Conan G2 `[WinError 2]` | Windows Conan 无法执行 profile 指向的 OHOS clang 路径 | 在目标设备补齐哈希冻结的 OHOS 工具链闭包，并改用 Conan conf 解析编译器 |
| 3 | Phase 2 静态重建 `ios_base::failure: Operation not permitted` | HarmonyOS 用户存储对该阶段的文件操作不提供所需权限 | 不把失败伪装为成功；分发已验证的 Phase 1 bootstrap，并在报告中保留限制 |
| 4 | 把 `tests/**/*.testscript` 文件路径直接传给 `b test` 导致 `file{headers.testscript}` 未知目标 | build2 的测试目标由各目录 buildfile 声明为 `testscript{stem}`，原始文件路径会触发 file 目标搜索；另有 4 个 `common.testscript` 仅作为 harness 依赖 | 在任务私有副本移除 libbutl 可选测试树后，使用官方根级 `b/b config.bin.lib=static -s test`，并以 51 个文件（47 runnable + 4 harness）作为固定分母；任一 runner 非零都 fail closed |
| 5 | CI Phase 2 找不到 `libpkg-config/pkg-config.h` | libbutl 发布快照把 `libbutl-pkg-config/libpkg-config/*` 作为指向未随快照发布的 `upstream/libpkg-config` 的悬空链接；仅设置 `config.import.libbutl` 不能凭空生成缺失源码 | 在 `source()` 中以 SHA-256 下载官方 `build2/libpkg-config` v0.1.3 归档到 `libbutl-0.18.0/upstream/libpkg-config`，再由 libbutl 导出配置提供头文件和 C 源码；必须重新执行完整 Phase 2 与 51 项上游测试 |
| 6 | CI #38637 在任何配方测试前被 G0e 拦截 | 当前主线新增根目录 `test_push.txt`，不在 CI 根目录白名单；构建脚本因此 fail closed，未进入 Phase 1/2 或上游测试 | 合并最新 `origin/main` 后仅删除该已确认的主线临时文件，并保留 G0e 失败日志；新的 CI 必须重新通过 G0e 后再执行完整 Phase 2、51 项上游测试和 1 项消费者测试 |
| 7 | CI #38714 无法应用 PR diff | 在 #38637 后主线已自行删除 `test_push.txt`，旧候选仍携带该删除补丁；CI 应用 diff 时返回 `test_push.txt: does not exist in index` 并在 G0e 前退出 | 再次同步最新 `origin/main`，确认主线删除已包含在基线，使 PR diff 不再重复删除；保留冲突日志并以新 HEAD 重新触发全部门禁 |
| 8 | CI #38733 上游 51 项全部因 runner 缺少编译器配置失败 | 目标 `b/b` 没有默认 C++ 编译器，recipe 的 test operation 只传 `config.bin.lib=static`，返回 `not built with default C++ compiler; use config.cxx to specify`；Phase 2 编译本身已完成 | 在同一官方根级 runner 命令中传入从 Conan conf 解析的 `config.cxx=<absolute cxx>`，保持 51 文件分母不变并重新执行完整上游套件 |
| 9 | CI #38791 在 G0e 根白名单阶段被当前主线文件阻断 | 主线在上一轮之后新增 `BUILD.gn`、`oh-package.json`；旧候选未同步该主线，CI 在执行配方前 fail closed | 同步最新 `origin/main`，确认这些文件已属于基线且 PR diff 不重复删除；保留 G0e 日志并以同步后的新 HEAD 重新执行全部门禁 |
| 10 | CI #38855 同步主线后仍被 G0e 根白名单阻断 | `BUILD.gn`、`oh-package.json` 虽已进入主线，但 CI 白名单不允许根目录出现它们；仅把它们带入基线仍会 fail closed | 在确认主线仍含文件后，从候选中精确删除两者，保留失败日志；新 CI 必须重新通过 G0e 后执行 Phase 2、51 项上游测试和 1 项消费者测试 |
| 11 | CI #38924 在候选已删除根文件后仍被 G0e 阻断 | 远端分支与 PR 文件列表均显示 `BUILD.gn`、`oh-package.json` 已删除，但 CI checkout 后仍把主线文件带入根白名单检查，说明平台 diff 应用边界仍未收敛 | 保留 #38924 的真实日志与分支 404 回读；刷新候选提交后重新执行 G0e，若仍恢复主线文件则记录为平台门禁阻断，不把配方或上游测试写成通过 |
| 12 | CI #39023 在上游测试入口失败 | `basic_layout` 的 `source_folder` 包含 Conan 生成的 `build-release`；直接复制整个 source_folder 将 `build-release/conan` 混入上游树，根级 `-s test` 因非上游目录缺少显式目标而返回 `no explicit target for build-release/:dir{conan/}`，导致 51 项均失败 | 计算 `self.build_folder` 相对 `self.source_folder` 的根目录，仅在复制源树时排除该目录；保留 build2 源码、libbutl/libpkg-config 和完整 51 项 typed-target runner，必须以新 CI 重新验证 51/51 与消费者 1/1 |
| 13 | CI #39085 在源码获取阶段超时 | Worker 无法在限定时间内连接官方 `git.build2.org`，Conan `source()` 在重试后返回 `ConnectTimeoutError`，因此未进入编译或 51 项测试；本地验证表明官方 GitHub `build2/build2` 与 `build2/libbutl` v0.18.0 tag 归档可达，且字节级 SHA-256 分别与 cgit 归档完全一致 | 将 `conandata.yml` 的两个源码 URL 切换到官方 GitHub tag 归档，保持原 SHA-256 不变；在新 CI 中重新执行完整 Conan create、51 项上游 testscript 和 1 项消费者探针，任何下载或测试失败仍 fail closed |
| 14 | CI #39194 上游 bash 测试因 `getcwd` 权限报错 | GitHub 归档已成功下载并完成 Phase 1/2，但 build2 的 `tests/bash/testscript` 在执行 `b/b test` 时收到 shell 的 `shell-init: error retrieving current directory: getcwd: ... Permission denied`；Phase 2 需要 `/data` 的替换/锁语义，而 Bash 测试需要可遍历的 worker cwd，单一工作根不能同时满足 | 保持 Phase 1/2 在已探测的 `/data` 根执行；生成 `b/b` 后把完整已构建源码树复制到平台已用 zsh 启动构建的 `CI_REPO_ROOT`（回退候选才是 Conan build 目录），逐个执行 `bash/sh -c pwd` 探针，再从通过者运行同一个官方根级 runner。上游 51 项不修改、不排除，测试 HOME/TMP 也绑定到该副本根 |
| 15 | CI #39276 在 libbutl 源码下载阶段超时 | Worker 的 GitHub 主站对 `build2/libbutl` 归档连接超时；build2 主归档因已有 gh-proxy 缓存而下载成功，但 `libbutl` 未命中缓存，Conan `source()` 在 `github.com` 重试后退出，未进入编译或测试 | 将两个源码 URL 统一改为官方 `codeload.github.com` tag 端点；本地验证 build2（1,700,016 bytes）和 libbutl（551,222 bytes）的 SHA-256 与原 cgit 归档完全一致。新 CI 必须重新通过源码闭包、完整 51 项上游测试和消费者探针，下载失败仍 fail closed |
| 16 | CI #39308 codeload 归档解包失败 | codeload URL 的 basename 是 `v0.18.0`，Conan `get()` 未能从无扩展名 URL 推断 gzip tar 类型，下载后按 ZIP 解包并报 `BadZipFile: File is not a zip file`；源码字节和 SHA-256 校验尚未进入测试 | 在两个 `get()` 调用中显式指定 `filename=build2-0.18.0.tar.gz` 和 `filename=libbutl-0.18.0.tar.gz`，让 Conan 使用正确的归档格式；新 CI 必须继续完成 Phase 1/2、51 项上游 testscript 和消费者探针 |
| 17 | CI #39317 工作根门禁过早失败 | 三个官方源码归档已成功下载并解包，但把 shell cwd 探针加入 Phase 2 工作根选择后，所有 `/data` 候选都被拒绝，配方在编译前报 `build2 requires an OHOS work root whose shell can resolve cwd`；该门禁错误地要求单一路径同时满足两个不同阶段的能力 | 将 Phase 2 文件替换/锁能力与测试 shell cwd 能力拆成两个阶段：前者继续选择 `/data` 根，Phase 2 完成后把测试树迁移到经 shell cwd 探针的 Conan build 目录。新 CI 必须从头完成全部阶段，不能复用 #39194 的编译与其他 run 的测试 |
| 18 | CI #39337 Conan cache 测试副本仍不能 `getcwd` | Phase 1/2 已在 `/data/storage/el2/base/cache` 成功，完整树也已复制到 Conan `build-release` 下，但该 cache 路径的 Bash cwd 探针仍报 `Not supported` / `No error information`，因此正确 fail closed 且未执行 51 项 | 测试副本优先创建在 `CI_REPO_ROOT`，该目录已由平台以 zsh 作为当前目录启动同一构建；创建后仍必须独立执行 shell cwd 探针，失败才尝试 Conan build 目录，全部失败则阻断。不得因路径限制删除 `tests/bash/testscript` |
| 19 | CI #39372 的 `CI_REPO_ROOT` 副本仍不能启动 Bash | 三个官方归档、Phase 1/2 和 `b/b --version` 均通过，但 Bash 在 `CI_REPO_ROOT` 与 Conan build-root 子目录启动时都因子进程继承的 `PWD` 与真实 cwd 不一致而进入启动期 `getcwd()`，分别报 `Not supported` / `No error information`；改变 `/storage` 子目录不能修复这一环境漂移 | 保持 51 个上游 `.testscript` 字节、buildfile、目标和断言不变；仅在 OHOS 测试进程的 `PATH` 首位放置任务私有 `bash` 包装器。包装器用系统 `readlink /proc/self/cwd` 取得每个嵌套进程的真实测试 cwd，导出匹配的 `PWD`，再以原 cwd 和原参数执行真实 Bash。包装器探针必须返回精确 cwd、空 stderr 和 RC=0，测试前后还要复算全部 51 文件哈希；任一漂移或 runner 非零继续 fail closed |
| 20 | CI #39451 在 libpkg-config 下载阶段超时 | 同一 Worker 已从 `codeload.github.com` 成功下载 build2 和 libbutl，但第三个 redirect-form `github.com/build2/libpkg-config/archive/...` 连接超时；自动预下载又因 Worker 没有 `curl` 而未缓存，Conan 在编译和 51 项测试前退出 | 把 libpkg-config 切到同一官方 `codeload.github.com` tag 端点，并为无扩展名 URL 显式指定 `filename=libpkg-config-0.1.3.tar.gz`。本地下载为 46,798 bytes，SHA-256 仍为 `147C196B...8357`；新 CI 必须重新完成全部阶段和 51/51、1/1 |
| 21 | CI #39485 的官方 runner 在 `generate_uuid()` 处找不到 `libuuid.so.1` | Bash cwd 修复已经让目标平台上的 51 项官方 runner 真正启动，但 libbutl 的 Linux UUID backend 会按固定 SONAME 动态加载 `libuuid.so.1`；OHOS Worker 不提供该系统库，故 `tests/function/builtin/testscript:165:5` 返回 RC=1。此时仅能确认 `discovered=51`、`runnable=47`、`support=4`，不能把已出现 marker 的部分目标折算为通过 | 为 OHOS 增加已发布的 `uuid/2.40.1` 静态 PIC 依赖，用目标 C 编译器将其 `libuuid.a` 物化为任务私有 `libuuid.so.1`，写入精确 SONAME，并把目录前置到 `LD_LIBRARY_PATH`。正式 bootstrap 前生成并启动新的目标 C 探针进程，通过该 SONAME 的 `DT_NEEDED` 实际调用 `uuid_generate` 并核验 DCE variant；成功后才执行原样 51 项 runner。库随 build2 包进入 `lib/`，同时通过 Conan runenv/buildenv 传播，不修改、排除或替换任何上游测试 |
| 22 | CI #39557 的 UUID 预检在导入 Python `ctypes` 时失败 | 目标 Worker 的 Python `_ctypes` 扩展依赖未安装的 `libffi.so.8`；该失败发生在私有 `libuuid.so.1` 生成之后、bootstrap 之前，耗时 23.878 秒，未执行任何上游或消费者测试。用解释器扩展做运行时预检扩大了闭包，不能证明 libuuid 本身有问题 | 删除 `ctypes` 依赖。配方写入最小 C 探针并用同一目标 `cc` 链接刚生成的 `libuuid.so.1`；其 `DT_NEEDED` 保留精确 SONAME，新进程继承 `LD_LIBRARY_PATH` 后调用 `uuid_generate`，并按 libbutl 强 UUID 分支在非 v4 时调用 `uuid_generate_time_safe`。探针 RC、stdout 或 UUID 语义任一不符都在完整构建前 fail closed |
| 23 | CI #39608 的官方 runner 在外部 GNU `cat` 选项处失败 | 原生 UUID 探针、Phase 1/2、稳定 cwd 包装器均已通过，51 项官方 runner 真实启动；`tests/function/process/testscript:43:5` 执行 `^cat --squeeze-blank f` 时，OHOS 系统 `cat` 返回 `Unknown option 'squeeze-blank'`。runner RC=1，后续 31 个 runnable 目标没有终端，消费者未运行 | 不修改或排除 testscript。只在 OHOS 上由目标 `cc` 构建任务私有 `cat` 前端，将其与现有 Bash 包装器一起置于测试专用 `PATH` 首位；仅 `-s/--squeeze-blank` 走字节流空行压缩，普通调用通过 `execv` 原样交给预先解析的真实平台 `cat`。完整 suite 前要求压缩与透传两个目标探针均精确通过，随后仍运行同一个根级 51 项 runner |

## 源码修改

补入 `config/config.guess`、`config/config.sub` 仅用于任务自有源码副本的工具链验证；未形成候选 patch。

## 依赖版本

`libbutl-0.18.0`（官方快照，SHA-256 `527A24C4C787139C8C3B801973B190808FD1C3C6A538960E90DA19A3AB50218A`）。
`libpkg-config` v0.1.3（官方 build2 归档，SHA-256
`147C196B5128EE2639D9710C7572F6D312F1E2A65FB360C4E85F8369C2198357`）。
`uuid/2.40.1`（OHOS armv8 已发布静态 PIC 包；RREV
`e05bc8e141027fc5222bdc9401aac2db`，Package ID
`21b17f8b2bc0e9511e276e3d57a23893067cefe5`，PREV
`b73be30a008ebc36b81b7863932cb7a5`）。

## 验证结果

```text
WSL 官方源码重建与上游测试：通过（Phase 1/2 自举，51/51 文件清单通过）
上游 testscript：51/51 通过（47 个 runnable 目标 + 4 个 common harness）
消费者版本探针：1/1 通过（目标 Conan create 的历史独立回执；当前 W3 r6 未到达该阶段）
目标 W3 r6：失败（Phase 2 在任务私有存储仍报 `ios_base::failure: Operation not permitted`，RC=134；保留为不可变历史，未进入上游测试）
WSL 日志：F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\wsl-upstream-tests-r7.log
WSL 日志 SHA-256：149069D87DA6819A3B9B6C05BD565FD00E2A0DE4AB774B9BDF38BBD005E952A6（322589 bytes）
目标 r6 日志：F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\w3-r6-runner.log
目标 r6 日志 SHA-256：3BA1CD359748C8666FD6255E76DCD9DECB4B315925FF9C096C284FB36B822464（11056423 bytes）
CI #38445：失败（Phase 2 导出配置中的 `libpkg-config/pkg-config.h` 缺失；完整日志
见 `F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\ci-38445-conan-build-test.log`，未进入上游 51 项）
CI #39023：失败（已通过 checkout 和 G0e；上游 runner 递归到 `build-release/conan` 非源码目录，
`discovered=51, executed=51, passed=0, failed=51, rc=1`；修复复制边界后必须重新执行）
CI #39372：失败（三个源码归档与 Phase 1/2 通过；`CI_REPO_ROOT` 和 Conan build-root
副本的 Bash cwd 探针均失败，未启动 51 项；Buildbot buildid `44843`，revision
`20f113f170e731c8c7693fbf8f4de62bfe2ea57e`；日志 SHA-256
`67E7F669F0933FB7D04724D37F0708B76620A7DEF2F2538DDC3CA66317FC63DF`）
CI #39451：失败（build2 与 libbutl 的官方 codeload 归档成功，libpkg-config 的
`github.com/.../archive` 端点连接超时，未进入编译或测试；Buildbot buildid `44924`，
revision `49f50abe58e88c7edaa0fb559e87d61781387be4`；日志 SHA-256
`8061527F0DC8B2494AB232A7458E5EA22A3D22D241971C8AE93F64046BCFF8FA`）
CI #39485：失败（三个官方归档与 Phase 1/2 均完成，51 项官方 runner 已启动；
`generate_uuid()` 因 Worker 缺少 `libuuid.so.1` 返回 RC=1，统计为
`discovered=51, runnable=47, support=4, execution_accounting=unavailable_after_nonzero_runner`，
消费者未运行；Buildbot buildid `44958`，revision
`90950bf39828e407722d141d74201171053fe1f4`；日志 SHA-256
`7D69ECA447C61490C69C096FA2C619B0C6FEB1CD05A6B296A284CF845D783150`）
uuid W0：`conan install --build=never` 已精确取得上述 OHOS armv8 binary；日志
`F:\HarmonyPC\pr7775-build2-repair-20260903\evidence\w0-uuid-2.40.1-ohos-binary-install.log`
静态 PIC 物化夹具：AArch64 ELF DYN，SONAME `libuuid.so.1`，导出
`uuid_generate` / `uuid_generate_time_safe` / `uuid_unparse_lower`，29,040 bytes，
SHA-256 `4C43BCEA5FAB3B0211F47C155AEC1FC349DE48845D69720B3833A9BED045A178`
CI #39557：失败（`uuid/2.40.1` 精确 RREV/PID/PREV 下载成功，私有库已生成；目标
Python 导入 `_ctypes` 时因缺少 `libffi.so.8` 返回 RC=1，bootstrap 与测试均未开始；
Buildbot buildid `45030`，revision `77415b216dac1b4bc2125584dbb454890cede943`；
日志 SHA-256 `D4875BE02742D79C0A50D0E6FA08697AA10AF37972F4BCDB34CD39C06D7077EE`）
CI #39608：失败（原生 UUID 探针与 Phase 1/2 通过，官方 51 项 runner 已启动；
`tests/function/process/testscript:43:5` 的外部 `cat --squeeze-blank` 被 OHOS 系统
`cat` 以未知选项拒绝，runner RC=1，消费者未运行；Buildbot buildid `45081`，
revision `1c0aea5b3ebdc27973431e34be0bdc1b10129e9c`；日志 SHA-256
`930C9C1E721B93343E44411941DFA4490D2A787AE5593901AD17BA72D8AF0DBD`）
任务私有 cat 前端宿主定向夹具：通过（配方 AST 直接提取的 2299-byte C 源码；
`--squeeze-blank`、`-s`、stdin、多文件边界及普通透传均逐字节通过；源码 SHA-256
`02B6D5268F1B805249A9151CA8E23B9CAEEE981D67178D64B9B809919A6556F7`）
稳定 cwd 包装器 WSL 定向夹具：通过（错误 `PWD` 下仍恢复真实 cwd，保留 `$0` 与参数，
且无 stderr；夹具 SHA-256
`12C717C0AE24C77F71E84B7B1965B8417CAEE7B73CAD5D036F56CF8B3294A33A`）
RREV=43cc11a5a690b0403c56f194b16375fe
Package ID=4b977264131a1c74e82bd6bb51b63cc9aadc4cfa
PREV=241f06ad352dce9b0991752c92bc1ecf
完整日志：F:\HarmonyPC\contrib-claim-af-20260902-build2\evidence\target-conan-create-r2.log
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `bin/build2` | 22,964,800 bytes | OHOS arm64 Phase 1 bootstrap |
| `bin/b` | 22,964,800 bytes | OHOS arm64 Phase 1 bootstrap alias |

## 注意事项

## 编译结束

上游 51 个 testscript 已在全新官方源码副本中由 build2 自带 runner 完整执行并
通过。配方在 OHOS 上把 Phase 2 工作根优先放到任务私有 `/data/local/tmp`，并
保留旧目标用户存储失败和各次 CI 失败作为历史证据。CI #39372 证明改变
`/storage` 子目录不能满足 Bash 启动期 `getcwd()`；CI #39451 又在 libpkg-config
redirect-form GitHub URL 下载阶段失败。CI #39485 已证明这两项修复让目标官方 runner
进入真实用例执行，随后暴露缺少固定 SONAME `libuuid.so.1`；下一候选从已发布的静态
PIC provider 生成任务私有运行时库。CI #39557 进一步证明 Python `ctypes` 会引入
Worker 缺失的 `libffi.so.8`，因此下一候选改用目标 C 原生探针，不修改、排除或缩减
任何上游测试。CI #39608 已证明该原生探针和完整 bootstrap 可通过，并让官方 runner
进入 `tests/function/process`；新的阻断是 OHOS 系统 `cat` 缺少 GNU
`--squeeze-blank`。下一候选仅在测试专用任务目录提供目标 C 兼容前端，普通 `cat`
仍透传到平台实现。必须取得新的独立 CI 终态 `51/51` 与消费者 `1/1`，才可把目标
平台结果写为通过。
