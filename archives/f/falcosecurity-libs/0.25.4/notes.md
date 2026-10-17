# falcosecurity-libs 0.25.4 HarmonyOS PC 适配记录

## 适配范围

- 上游标签：`0.25.4`，源码来自官方 GitHub codeload tarball（`https://codeload.github.com/falcosecurity/libs/tar.gz/refs/tags/0.25.4`），SHA256 为 `272a5a0c05e7c10a658ed9649023e6179061a4ab29e012602893586ac64b5938`；配方通过 `filename="falcosecurity-libs.tar.gz"` 固定归档类型。
- 构建系统：CMake；目标为 OpenHarmony/HarmonyOS PC aarch64，编译器为 `/data/service/hnp/bin/clang` 与 `clang++`，目标三元组为 `aarch64-linux-ohos`。
- 构建为 shared-library 包，启用 libscap/libsinsp 用户态库和官方测试目标，关闭 Linux driver、modern BPF、driver tests、libsinsp E2E、repo E2E、fuzzer、examples 和 benchmarks。
- 依赖使用上游 CMake ExternalProject 下载的 bundled zlib 1.3.1、oneTBB 2022.1.0、jsoncpp 1.9.5、RE2 2022-06-01、valijson 1.0.2；OHOS 测试构建通过 `test_requires("gtest/1.17.0")` 使用 ohpcd 已发布的 GoogleTest/GoogleMock，并以 `USE_BUNDLED_GTEST=OFF` 与 `GTest_DIR` 接入。

## 配方与补丁

1. `CompilerFlags.cmake`：shared build 不再误加 OHOS 不可用的静态链接选项。
2. `ExternalProjectToolchain.cmake`：向 bundled CMake 子项目传播 OHOS SONAME flag。
3. `zlib.cmake`：OHOS shared zlib 的 Autotools `LDSHARED` 显式生成 `libz.so.1` SONAME。
4. `test/libscap/CMakeLists.txt`：OHOS 排除依赖 Linux driver/BPF 的测试源，保留用户态和 savefile 测试。
5. `userspace/libscap/scap.c`：仅在真实 Linux 平台启用 Linux 实现，OHOS 使用已有通用实现。
6. `userspace/libscap/scap_platform.c`：通用平台补充 hostname 初始化。
7. `userspace/libsinsp/sinsp.cpp`：HOSTINFO 和 test-input live 模式在 OHOS 回退到通用平台实现。
8. `userspace/libsinsp/test/CMakeLists.txt`：修正上游 scap-file fixture 条件，使 62 个可运行的测试声明进入 OHOS 测试目标。
9. `userspace/libsinsp/test/plugins.ut.cpp`：机器信息断言限定真实 Linux 平台。
10. `userspace/libsinsp/test/public_sinsp_API/sinsp_logger.cpp`：日志测试使用 `TMPDIR`，避免设备 `/tmp` 不可写。
11. `userspace/libsinsp/test/scap_files/converter_tests.cpp`：Linux `fcntl` capture fixture 在 OHOS 的参数布局不同，显式记录 1 个有证据的 GTest skip。
12. `userspace/libsinsp/test/test_utils.h`：OHOS 规避 Linux `sockaddr_storage` 重定义。
13. `userspace/libsinsp/test/user.ut.cpp`：按 OHOS passwd 语义校验 root home。
14. `conanfile.py` 的 `SCAP_FILES` 常量记录 7 个官方 scap fixture 的 URL/SHA256（避开 W3 通用预下载器对 conandata URL 的部分文件误缓存）；配方 `source()` 先校验下载，`build()` 在 CMake configure 前将其复制到二进制目录的 `scap_files/`，使上游原有 fixture 下载循环在 CI/设备均可离线命中。
15. `conanfile.py` 的 `BUNDLED_SOURCES` 常量固定并校验 6 个实际启用的 CMake ExternalProject 归档（uthash、oneTBB、jsoncpp、valijson、RE2、zlib）；`build()` 在 configure 前将其复制到对应 `<name>-prefix/src/`，保持上游 `URL_HASH` 逻辑且不修改框架。

## 测试统计

| 测试簇 | 静态声明 | 注册源声明 | runner 用例 | 实际执行 | 通过 | 失败 | 跳过/未注册 |
|---|---:|---:|---:|---:|---:|---:|---:|
| libsinsp 用户态测试 | 778 | 715 | 805 | 805 | 804 | 0 | 1 |
| libscap 用户态/savefile 测试 | 393 | 363 | 363 | 363 | 363 | 0 | 0 |
| libsinsp E2E | 183 | 0 | 0 | 0 | 0 | 0 | 183 |
| driver 测试 | 467 | 0 | 0 | 0 | 0 | 0 | 467 |
| repo E2E | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 合计 | 1821 | 1078 | 1168 | 1168 | 1167 | 0 | 1；另有 743 个静态声明因平台目标未注册 |

`TEST_P` 参数实例会使 runner 用例数高于注册源声明数；两者按不同层级保留。未注册的 743 个静态声明由 Linux-only libsinsp 测试 63、driver/BPF 相关测试 467、libsinsp E2E 183、libscap kmod/modern-BPF/Linux-fd 测试 30 组成。

设备上的独立结果：`unit-test-libsinsp` 为 805 执行、804 通过、1 跳过；`libscap_test` 为 363 执行、363 通过。fixture 常量方案真实 Conan 日志为设备任务临时目录 `conan-create-fixture-v7.log`；finish v2 的 W3 收口日志为 `archives/f/falcosecurity-libs/0.25.4/reports/w3-local-ci.log`，记录了实际源码 URL、7 个 fixture staging、两套上游测试和 `test_package`。

## 消费者测试

`test_package/test_falcosecurity_libs.cpp` 通过 Conan CMake target 编译并调用真实 API：校验 `scap_get_ppm_sc_name(PPM_SC_OPEN)` 返回 `open`，并校验 `sinsp_gethostname()` 返回非空字符串。设备输出为 `falcosecurity-libs API test passed: open, hostname=localhost`，1 个消费者程序、2 个 API 断言均通过。

## 验证命令

- W0：`bash ci/scripts/preflight_check.sh falcosecurity-libs/0.25.4`，运行时依赖为源码内 bundled 组件；测试专用 `gtest/1.17.0` 已用精确 `conan install --build=never` 验证 ohpcd 二进制可得，PASS。
- 源码预检：官方 tag 存在；源码 SHA256 与 `conandata.yml` 一致；源码主构建系统为 CMake，主要源文件为 C/C++。
- `conan-verify`：`python3 scripts/ohc-run.py conan-verify falcosecurity-libs 0.25.4 --profile ci/conan/profiles/ohos-aarch64`，G1/G2/G3/G4/L2/L4/L5 PASS；fixture 常量方案的真实 `conan create` 日志为 `conan-create-fixture-v7.log`，finish v2 的 W3 报告为 `reports/w3-local-ci.log`。
- finish 的通用 G0 仍会对 CMake 项目尝试 `./configure` 并返回 127；该框架入口不适用于本项目，原始日志已保留，不修改 CMake 源码迎合它。W3 已改用任务私有输入完成并通过。

## CI 失败修正记录

- CI #43109（2026-09-09）首行结论为 `## CI 校验失败`，失败步骤是 `conan-build-test`，源码 URL 被 CI 预下载改写为 `https://gh-proxy.com/https://github.com/falcosecurity/libs/archive/refs/tags/0.25.4.tar.gz` 后超时；这是 Worker 网络/源码入口问题，不是本次 CMake 编译错误。
- 设备对三种候选地址做了真实下载核对：官方 GitHub archive 与官方 codeload 均得到 4,538,271 字节、同一 SHA256；GitCode 同路径只返回 5,785 字节 UTF-8 文本，SHA 不符，排除。因 CI 预下载脚本只对 `github.com/` 自动添加 `gh-proxy`，采用官方 codeload URL 可绕开该重写；`conan source` 和后续 `conan create` 均记录 `Sources correctly downloaded from https://codeload.github.com/...`。
- CI #45749（build 52216）在 2026-09-14 的真实失败发生于 CMake configure：根源码 codeload 最终下载成功，但上游 7 个 `file(DOWNLOAD)` fixture 在 Worker 上持续等待，18,181 秒后触发 3,600 秒 `conan create` 超时；没有进入上游测试。该证据与源码/配方无关的根源码下载问题分开记录。
- 针对上述 configure-time 下载瓶颈，设备直连官方 S3 取得并以 SHA256 校验 7 个 fixture；第 6 次真实 `conan create`（设备日志 `~/tmp/uc2/falcosecurity-libs-0.25.4/conan-create-fixture-v6.log`）显示 7/7 `Staged pre-fetched scap-file`、7/7 `Skipping download`，随后完整编译、两个上游套件和真实 `test_package` 均退出 0。
- 历史 W3 clean 重试在 fixture staging 已解决后，于 CMake ExternalProject 下载 `uthash` 与 oneTBB 时出现 `OpenSSL SSL_read ... unexpected eof`；对应日志 SHA256 为 `27d832fbbdcbc0457226934161d15038b88262a37ab606c6b65915599ea40c70`，该次未进入上游测试，属于提交前探索证据。
- finish v2（2026-09-15）在 fixture URL 从 `conandata.yml` 移入 recipe `SCAP_FILES` 常量后完成 G2 与 W3；W3 日志 SHA256 为 `3b5653ab27705cbdbf8b191bedf4f16c8c35c22057f933c8bb3601d9881b2a25`，7/7 fixture staging、7/7 configure 下载跳过，两个上游套件与真实 `test_package` 均通过。
- finish v3（2026-09-12 20:55）在官方 codeload 输入下完成 G2 与 W3；`unit-test-libsinsp` 805（804 passed、1 skipped），`libscap_test` 363（363 passed），真实消费者 `test_falcosecurity_libs` 1/1 运行通过。当前 `.ci-result.json` 的 `exit_code=0`，W3 日志 SHA256 为 `13f3c13e1a2a23f50d43fe9dc7bdeb4bbe38c589ce8886259c6a2668a539f0de`；推送新 HEAD 后必须重新触发并核对 CI，旧 #43109 不可复用。


### W3 设备 inode 阻塞记录（2026-09-15）

- 设备挂载点 `df -h` 仍有约 366GB 可用，但 `df -i` 显示 inode 总数 48,455,677、空闲约 5,000、使用率 100%。
- v8（2026-09-15 22:39）在 99% 编译阶段写 `kexec_arm64.cpp.obj.d` 首次报 `No space left on device`，完整日志 SHA256：`24a776825b421dff720cbd9d0b57964b85864213a51c0bdb10c6b0ea0ba5e9d3`，退出码 1。
- 清理本任务 38 个旧 `p/b/falco*` 构建目录后，v8-rerun1（23:03）在 jsoncpp/oneTBB CMake scratch 写入阶段再次报同一错误，日志 SHA256：`ba4ce0b10a87f07f95b731b3c98ddafa4be92382c011490f89a2f5c0e20339ab`，退出码 1；两次均未进入上游测试。
- 该阻塞属于共享设备 inode 资源，不修改配方、不缩小测试分母；相关临时构建缓存已清理，保留两份失败日志用于后续复核。


### W3 v8-rerun2 完整验证（2026-09-16）

- 命令：`bash ~/tmp/uc2/falcosecurity-libs-0.25.4/run-conan-create-fixture-v1.sh`，提交前工作树（含未提交的 BUNDLED_SOURCES follow-up），`CONAN_HOME=~/tmp/ch/home-falcosecurity-libs-0.25.4-w0`，host/build profile 均为 `ci/conan/profiles/ohos-aarch64`，`tools.build:jobs=2`。
- 日志：`~/tmp/uc2/falcosecurity-libs-0.25.4/conan-create-fixture-v8-rerun2.log`，331651 字节，SHA256=`07170b6649b19a7fa5af04aef52870acd64439d3da3d1d3cea97db38f175ad64`；脚本内部 `conan_create_rc=0`。外层 tee wrapper 的错误状态不代表 Conan 失败，真实 Conan 返回码以日志中的显式记录为准。
- 预取输入：7/7 `Staged pre-fetched scap-file`；6/6 `Staged bundled source archive`；7/7 CMake fixture `Skipping download`；6/6 ExternalProject 归档 `File already exists and hash match (skip download)`；6 个 ExternalProject download step 均未发生网络回源。
- 上游测试：`unit-test-libsinsp` 执行 805、通过 804、跳过 1；`libscap_test` 执行 363、通过 363；合计 runner 1168、通过 1167、失败 0、跳过 1。静态总数 1821、注册源声明 1078、未注册静态声明 743 的分母保持不变。
- 消费者测试：`test_falcosecurity_libs` 编译并运行 1/1，调用 `scap_get_ppm_sc_name(PPM_SC_OPEN)` 与 `sinsp_gethostname()`，2/2 API 断言通过，输出 `falcosecurity-libs API test passed: open, hostname=localhost`。


### 当前提交的 W3 复验（2026-09-17）

- 在当时的最新提交上调用 finish 内部 `step35_local_ci()` 完成 W3；完整日志为 `reports/w3-local-ci.log`，`.ci-result.json` 的 `exit_code=0`。最终提交 SHA 与该日志哈希在 PR 正文、Issue 和 STATE 中同步记录。
- 本轮 `build_and_test.sh` 对 7 个 fixture 全部 `Skipping download`，6 个 ExternalProject 归档全部 SHA256 match；`unit-test-libsinsp` 805（804 通过、1 跳过）、`libscap_test` 363/363，消费者 1/1、2/2 API 断言通过，L1e 反向测试确认真实依赖本包。
- v8-rerun2 的 331651 字节日志仍作为提交前探索证据保留；最终提交对应的 W3 日志是同 SHA 绑定证据，不能仅凭 v8 日志判断当前提交。

## 状态与边界

- 当前归档状态应为 `built`，不能写成 `published`；尚未发生合并后的 release/upload。
- Linux kernel driver、modern BPF 和依赖 live driver 的 E2E 测试未执行，原因是目标为 OHOS userspace build，相关上游目标只在 Linux 条件下注册；不将消费者测试冒充这些测试。
- `lang-preflight` 曾因仓库内嵌的 `test/e2e/tests/commons/setup.py` 误判为 Python/setuptools，已保留其原始结果；实际根 CMake、`project(falcosecurity-libs)`、源文件占比和构建日志证明任务是 C/C++ CMake，不能据此归类为 `env_unsupported`。

### 对话 #1 — 2026-09-08

完成任务核验、W0/W0b、源码预检、OHOS CMake 配方、13 个正式补丁、上游测试和真实 `test_package`。首次 finish 的 G0 因工具错误走 `./configure`，W3 因过期 `origin/main` 误报其他归档；使用当前任务 staged diff 后 W3 通过。当前仍需完成提交前 W4、PR 和线上同 SHA 的 CI/AI 闭环。

### 对话 #2 — 2026-09-09

为满足消费者统计机器字段，`test_package/MANIFEST.yml` 增加 `consumer_tests: 1` 与 `consumer_passed: 1`。设备低并发 Conan 复验使用临时 profile 的 `tools.build:jobs=2`，G1/G2/G3/G4/L2/L4/L5 全部通过；G2 中 `unit-test-libsinsp` 执行 805、通过 804、跳过 1，`libscap_test` 执行并通过 363，真实 `test_package` 1/1 程序、2/2 API 断言通过。

旧 HEAD 的 finish/W3 与 CI #42756 证据均因本次源码入口修正而过期；finish v3 已在当前工作区完成 G2/W3，独立 W4 已通过。当前仍待精确提交、推送后按新 HEAD 重新获取线上 CI/AI Review；路径 C Issue #2837 已关联当前 PR，仍等待平台复审；未执行最终平台提审或合并。
### 对话 #3 — 2026-09-15

修正 CI #45749 暴露的 CMake configure-time fixture 下载超时：取消未能稳定应用的临时第 14 个补丁，改为 Conan `source()` 下载并校验 7 个官方 fixture，`build()` 在 configure 前 staging 到 `CMAKE_BINARY_DIR/scap_files`；随后 clean W3 暴露 6 个 bundled ExternalProject 归档的第二类网络边界，配方继续扩展为 checksum-bound source/staging；设备 v7 `conan create` 退出 0，最终 W3 需在 v8 重跑。测试账本保持 1821 个上游静态声明、1078 个注册源声明、1168 个 runner 用例、1168 个实际执行、1167 通过、1 跳过，以及 1 个消费者程序/2 个 API 断言通过。W3 已完成，仍需完成 W4；提交推送后获取同 SHA 的 CI/AI 结论；路径 B 知识扩展 Issue #3024 已创建并待与最终 SHA 互链；路径 C Issue #2837 继续等待复审。
### CI build #49520 失败与官方 S3 端点修正（2026-09-17）

- 提交前 HEAD `9bd10bb...` 的 CI build #49520 通过 G0/KC/JC，但 `conan create` 在 `kexec_arm64.scap` 下载到约 47.7/60.8 MB 后满 3600 秒超时；完整 CI 评论保留了命令、profile、Worker 和日志链接。
- 设备对虚拟主机 URL `https://falco-distribution.s3.eu-west-1.amazonaws.com/...` 的 Range 请求出现 `UNEXPECTED_EOF_WHILE_READING`；同一官方 S3 对象的 path-style URL `https://s3.eu-west-1.amazonaws.com/falco-distribution/...` 返回 HTTP 206。对象尺寸与 7 个 fixture 的 SHA256 输入未改变。
- 将 recipe `SCAP_FILES` 的 7 个 URL 切换到该官方 path-style 端点后，干净 w2 Conan home 的 G2 再次完成 7/7 staging、7/7 configure skip、6/6 bundled hash match、两套上游测试和真实 `test_package`；这解决的是传输端点稳定性，不是关闭测试或使用未核验镜像。

该端点选择可复用于同类 S3 虚拟主机 TLS EOF 场景，但提交前必须对同一对象重新核对官方归属、Content-Length 和 SHA256，不得把任意镜像当作等价源。

### 平台覆盖矩阵

- `libscap` userspace：`libscap_test` 363/363 通过，覆盖 savefile converter、事件表和 syscall 表。
- `libsinsp` userspace：`unit-test-libsinsp` 805 执行、804 通过、1 个有证据的 OHOS fixture-layout skip，覆盖 filter、parser、plugin 和 scap-file suites。
- 公开消费者 API：1/1 消费者程序、2/2 API 断言通过，调用 `scap_get_ppm_sc_name` 与 `sinsp_gethostname`。
- 能力边界：Linux kernel driver、kmod、modern BPF 和 live-driver E2E 目标未在 OHOS userspace 配置注册；743 个静态声明保留在未注册分母中，不宣传为 OHOS 等价能力。
---

**编译结束**: 2026-09-17 20:29
**最终状态**: built
