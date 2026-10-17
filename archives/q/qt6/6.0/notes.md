# Qt 6.0 HarmonyOS PC 移植记录

## 当前状态

### 已验证基础版本（7 个补丁）

2026-10-08 的 HarmonyOS 6.0 AArch64 Conan `create`、安装包质量门禁及当时的消费端测试均通过。对应设备结果仍保留在下文，适用于当时的 7 补丁基础版本。

### 上一候选版本（12 个补丁）

补丁 0008–0012 为 HarmonyOS 相对名称加入抽象 AF_UNIX 映射、same-UID `SO_PEERCRED` 接受检查和 Qt 公共 API 消费端/上游回归。固定 QtBase 6.0.0 源码上的 12 个补丁全部通过 `git apply --check --whitespace=error`，应用后的 12 个文件与生成补丁的工作源码一致。2026-10-09 真机 AArch64 Conan CI 和该候选测试均已通过；7 补丁基础版本的历史结果仍单独列在后文。

先对缓存的 7 补丁旧包运行 RED：消费者成功编译，但在 `QLocalServer::listen(name)` 按预期失败，Qt 报 `Unknown error 1`。随后运行 `CONAN_PROFILE=ohos-aarch64 ci/conan/build_and_test.sh archives/q/qt6/6.0`，12 补丁候选完整 Conan CI 成功。该阶段的设备工作副本和日志在 `/storage/Users/currentUser/tmp/qt6-candidate-ci-20261009`；本机保留日志于 `.ci_logs/qt6-6.0-device-20261009/`。

12 补丁候选的 Conan 配方修订为 `5dd434c34e2a43741403e1fc67e2568a`。8 个上游目标均成功构建，8/8 完整 CTest 套件通过，总计 113.46 秒；`tst_qlocalsocket` QtTest 汇总为 52 passed、0 failed、1 skipped。唯一跳过是 `fullPath()` 的绝对路径文件套接字 bind：设备返回 EROFS（errno 30），原生 AF_UNIX bind 对照确认受系统限制，Qt 返回匹配的 Name/HostNotFound 错误且没有回退到抽象地址。Conan 消费者 54/54 检查通过，打印并验证了 40 字节双向套接字 payload/response、同 UID `SO_PEERCRED` 和关闭后重连拒绝。CI 的 L0、L1、L2、L4、L5 全部通过；L2 中部分 Qt 辅助工具不支持通用 `--version`/`--help` 参数，CI 将其作为非阻断警告。

### 当前候选版本（13 个补丁，OpenSSL 3）

用户选择继续适配 OpenSSL 3 后，新增补丁 0013：Qt 6.0 的动态符号解析可使用 OpenSSL 3 的两个重命名符号，初始化时加载 OpenSSL 配置；HarmonyOS DNS 上游测试只把 SDK 明确报告 `Resolver functions not found` 的四个数据行记为预期失败，完整套件仍运行。上游旧 DES/RC2/RC4 key fixtures 需要 legacy provider，因此配方只在 CTest 进程内将 OpenSSL 3.6.4 库、配置和 provider 模块匹配使用，不改 Conan consumer 的环境，也不启用包运行时的 legacy provider。

2026-10-10 修复 Qt 管理套接字客户端对外 UID 地址的误拒绝后，重新运行完整 AArch64 Conan CI 成功。最终配方修订为 `9bb90a56173fa0e493bcf4ac78f08fba`，package ID 为 `01d92cf349a0dd98ff915f4bd99a04430171517f`，package revision 为 `f9f9cf34d3f712800ee376b1c855e3df`。29/29 上游 CTest 套件全部通过，总运行时间 128.04 秒；按测试项统计，29 个完整套件共运行 9,861 个 QtTest 函数/数据行（9,563 passed、0 failed、226 skipped、72 个 blacklisted 项；4 条 DNS QEXPECT_FAIL 行的结果计入 passed；排除 58 个 init/cleanup harness 项），其中 2 项为鸿蒙新增（managedAbstractNameAllowsDifferentClientUid 函数及 abstract-permission-option-rejected 数据行），上游等价范围为 9,859 项；`tst_qlocalsocket` 为 53 passed、0 failed、1 个经原生 bind 对照确认的 EROFS 跳过。Conan 消费者 84/84 项检查通过，验证 OpenSSL 3、完成 TLS 握手并协商 `TLS_AES_256_GCM_SHA384`，通过 TLS 双向交换 31 字节 payload/response；HarmonyOS 命名本地套接字与独立 QProcess 测试也通过。设备 CI 门禁 L0、L1、L2、L4、L5 全部通过，L1e 破坏性反向测试确认消费者确实依赖 Qt 包；L2 的工具参数警告按仓库规则非阻断。CI 退出码为 0，日志 `.ci_logs/qt6-6.0-device-20261010/qt6-6.0-final-aarch64-conan-ci.log` 的 SHA-256 为 `e311660696f8358e4fd62ad7d4b29a7ca07773b925114dd8f272135e2efb1572`。

完整 CI 后又将当前消费者源码（定义 84 项检查）固定到缓存的 7 补丁基线配方修订 `8b44517b736d877dcaf426043b082e64` 执行 RED。消费者成功编译，并按预期在跨进程命名 `QLocalServer::listen()` 处以 `Unknown error 1` 失败，未启动客户端；这是预期回归失败，未执行完全部 84 项检查。日志为 `.ci_logs/qt6-6.0-device-20261009/old-package-red-final.log`。

代码评审后，配方收紧了 OpenSSL 3 库与 legacy provider 的配对选择：从同一安装位置派生 `OPENSSL_MODULES`，避免继承到其他 OpenSSL 安装的 provider 路径。上述最新真机重跑覆盖了此项改动，日志明确记录库与 provider 均选自 `/storage/Users/currentUser/.harmonybrew/lib`，`tst_qsslkey` 及 TLS 消费端往返均通过。

另增加 `test_package/harmonyos_cross_uid/` 作为独立 UID 真机验证客户端，并在 Conan 消费端新增 `qt6_cross_uid_server` target。2026-10-10 已用 DevEco 签名工具验证最新 AArch64 HAP 签名，安装并启动成功；`ohos.permission.INTERNET` 授权状态为 `0`（`PERMISSION_GRANTED`）。HAP UID `20020151` 连接 SSH/Qt 服务 UID `20020084` 的探测在 AF_UNIX `connect()` 处返回 `EACCES (13)`，没有读取 `SO_PEERCRED`、发送 payload 或进入 Qt accept；这对 HAP/SSH 身份仍是独立的 HarmonyOS 安全域边界，不能代表同包克隆 UID 的 Qt 过滤测试。后续已完成同包 app-clone UID 真机验证，见 2026-10-10 地址修复记录。旧 HAP SHA-256 为 `EC19B2023788AFD0B2B7F108EC882E729359052294BDA5DCA4FF7B5D790F60DD`，日志 `.ci_logs/qt6-6.0-device-20261010/cross-uid-device-probe-internet-granted.log` SHA-256 为 `2e0bf789813c4cef9220c690601db2d2f09d38467779c3de13cb851c3ff80c37`。DevEco 本地签名配置未加入仓库，临时构建后已恢复项目原 `build-profile.json5`。

基础版本设备配置为 `OHOS/armv8`、HarmonyOS 6.0、Clang 15.0.4、Conan 2.29.1。仓库 CI 当时使用 `ci/conan/build_and_test.sh archives/q/qt6/6.0`，L0、L1、L2、L4、L5 均通过。L2 中若干 Qt 辅助工具不支持通用 `--version`/`--help` 参数，CI 将其标为非阻断警告。

此前在设备上取得的中间结果：

- 无补丁基线在 Qt 6.0.0 的 `cmake/QtAutoDetect.cmake` Android 工具链自动识别处失败。
- 前 5 个平台补丁使配置通过并将编译推进到约 27%；随后 `src/corelib/thread/qthread_unix.cpp` 调用了 HarmonyOS SDK 未提供的 `pthread_setcancelstate`、`pthread_testcancel` 和 `pthread_cancel`。
- 设备日志当时位于 `/storage/Users/currentUser/tmp/qt6-task2-baseline.log` 和 `/storage/Users/currentUser/tmp/qt6-task2-five-patches.log`。这两份是设备临时目录中的中间失败记录，不是最终构建或测试通过证据。
- 当时的 7 个补丁曾对本地未修改的 Qt 6.0.0 源码执行 `git apply --check`。当前 13 个补丁也已对固定源码副本执行该检查并通过；它只证明补丁上下文可应用，不代表目标编译通过。

本机离线检查中，Conan 2.29.1 的 `inspect` 能读取配方和 `conandata.yml`，Python 配方语法检查通过，补丁引用均有对应文件，当前消费端 84 个运行检查与清单计数一致。Windows 主机的 `conan graph info` 在加载用户 Conan 配置目录下的插件时收到 `WinError 5`；目标平台结论以设备 CI 为准。

## 包范围

`qt6/6.0` 对应官方 QtBase `v6.0.0`，仅支持 HarmonyOS PC AArch64（Conan `OHOS/armv8`）。包提供 Core、Concurrent、Network、软件光栅 Gui、offscreen Widgets、PrintSupport、Test 和 Xml；Gui 插件包含 minimal/offscreen 平台插件与 ICO/JPEG/GIF 图像插件。FbSupport 与 DeviceDiscoverySupport 是 QtBase 内部构建产物。此包不提供 Qt Quick/QML、数据库、原生窗口集成、OpenGL/Vulkan 或其他 Qt 模块。Qt 自带源码依赖随 QtBase 构建，本配方没有直接 Conan 依赖。

同仓库 QtBase 6.11.1 的路线用于核对组件组织和测试分层；其中常规上游测试、扩展测试和消费者场景分别记录为 7、19、7。Qt 6.0 的目标名称和条件重新从本归档固定的 6.0.0 源码读取，未照抄较新版本的 API 或测试目标。

## 上游来源

- 项目：QtBase（官方仓库 `qt/qtbase`）
- 标签：`v6.0.0`
- Commit：`fc9cda5f08ac848e88f63dd4a07c08b2fbc6bf17`
- Tree：`8d3adebbc24ee255c14662d040047242276dbfc9`
- 归档：`https://codeload.github.com/qt/qtbase/tar.gz/fc9cda5f08ac848e88f63dd4a07c08b2fbc6bf17`
- SHA-256：`19a2d8eb78921624faca6a4e5a3ff31e7ca91b0bb13ab4869f8c218e39300766`

Qt 官方归档入口当时返回 404，因此源码固定到官方 Git 仓库中已核验的 `v6.0.0` commit，并使用该 commit 的 codeload 地址。

## R51 上游测试清点

基于固定版本源码静态清点：`tests/` 下有 2,133 个递归目录、1,086 个 `CMakeLists.txt`；`qt_internal_add_test(` 有 568 处，其中 `tests/auto` 下 565 处。当前启用的五个模块目录中有 490 处注册调用：Core 212、Network 47、Gui 111、Widgets 119、Xml 1。这些是 feature/backend 条件生效前的源码注册调用数，不等于配置后的 CTest 项或单独测试函数数。

7/12 补丁阶段先构建 8 个聚焦目标，覆盖事件循环、线程、TCP 服务端、本地套接字、图像、光栅绘制、offscreen 控件和 XML；`tst_qlocalsocket` 另构建上游 helper `socketprocess`。13 补丁 OpenSSL 3 扩展将验证范围扩大到 29 个目标：QtNetwork 23 个配置目标以及上述 Core/Gui/Widgets/Xml 六个套件。29 个完整 CTest 套件均通过，`tst_qlocalsocket` 限时 600 秒；该完整套件此前曾独立运行并核对系统 EROFS skip 原因。

两个已检查但不加入可发布测试构建的目标是 `tst_qcoreapplication` 和 `tst_qtcpsocket`：Qt 6.0 的对应 CMake 文件在 `private_tests` 关闭时提前返回；该开关随 developer-build，不适用于本发布配置。线程测试中的 terminate/terminated 两个测试函数在 `QT_NO_PTHREAD_CANCEL` 能力宏下跳过；普通线程启动、退出和 join 测试仍保留。

7 补丁基础版本的配置后结果：所选 8 个目标 **8/8 成功构建**；7 个完整 CTest 套件 **7/7 通过**。`tst_qlocalsocket setSocketDescriptor` 单独运行，QtTest 汇报 3 passed、0 failed（初始化、测试函数和清理）。当时消费者程序的 50 项运行时检查 **50/50 通过**。这些历史结果不代表当前候选。静态注册调用数不作为已执行测试分母。

## 适配记录

1. `cmake/QtAutoDetect.cmake`：HarmonyOS Clang mkspec 不进入 Qt 6.0 的 Android NDK 自动发现分支，避免 Conan 工具链被误判为 Android。
2. `cmake/QtPlatformSupport.cmake` 和 `cmake/platforms/Platform/HarmonyOS.cmake`：将 HarmonyOS 纳入 Qt 的 Linux/POSIX 平台初始化路径，使 CMake 配置 `UNIX`、系统头文件和 POSIX 平台属性。
3. `mkspecs/harmonyos-clang/`：新增 Clang mkspec 和 POSIX `qplatformdefs.h`，解决 Qt 构建与 qmake 平台定义缺失。
4. Qt 6.0 的 QtBase pthread 实现仅在 `QT_NO_PTHREAD_CANCEL` 未定义时调用取消 API。Conan 配置向目标 C++ 编译添加该能力宏；无取消能力时 `QThread::terminate()` 沿用 Android 一样的 no-op 路径。相应地，两个仅测试强制取消的上游测试函数跳过，其他线程功能仍执行。没有伪造 SDK pthread 符号。
5. `FEATURE_tuiotouch=OFF`：Qt 6.0 CMake 同时创建 `QTuioTouchPlugin` 与 `qtuiotouchplugin` 目标，它们生成仅大小写不同的 `CMakeFiles/*.dir` 路径。设备存储将两种路径映射到相同 inode，导致 GNU Make 的一个 `build.make` 覆盖另一个并在全量构建时找不到 `QTuioTouchPlugin.dir/depend`。TuioTouch 是面向外部 TUIO 触控协议的可选硬件输入插件，不属于本包 offscreen UI 范围，因此关闭该 feature；关闭依据是设备文件系统和最终编译结果，不是猜测性的跳过。
6. HarmonyOS 只在私有宏 `QT_BUILD_HARMONYOS_LOCAL_SOCKETS` 下改变相对 `QLocalServer`/`QLocalSocket` 名称语义：规范化临时路径后按有效 UID 与 SHA-256 建立抽象地址；保持绝对路径文件套接字；超长路径仍拒绝；抽象地址拒绝非 `NoOptions` 权限标志；接受 Qt 管理的连接前核对 `SO_PEERCRED` UID。Conan 仅对该 OHOS QtBase 构建开启 `_GNU_SOURCE`；消费者不依赖此编译宏。外部传入的监听 descriptor 不启用该过滤。
7. OpenSSL 3 兼容补丁增加 Qt 6.0 对重命名动态符号的 fallback，并在初始化时加载 OpenSSL 配置。仅 CTest 用与库匹配的 HarmonyBrew 3.6.4 legacy provider 执行包含旧算法 fixture 的上游测试；Conan consumer 使用默认运行时配置完成真实 TLS 加密往返。HarmonyOS DNS resolver 不可用时，只有错误精确匹配的上游数据行预期失败，整套 QDnsLookup 仍执行。

## 消费端测试

`test_package/test_qt6.cpp` 链接并使用已安装包中的五个公开组件。7 补丁基础版本覆盖 Qt 事件循环与元对象、真实 TCP 双向数据交换、QImage/QPainter 像素读回、offscreen QWidget 绘制、合法/非法 XML，以及线程协作退出；当时的 50 项检查在设备上全部通过。

基础版本中的 HarmonyOS 特有流程通过 POSIX 抽象 AF_UNIX 地址创建真实内核 socket，再交给 Qt `QLocalServer`/`QLocalSocket` 接管；测试分块发送 40 字节 payload、验证完整回读与响应、关闭端点，并确认重新连接返回 `ECONNREFUSED`。设备输出确认该历史流程通过并打印实际 payload 和字节数。这是真实内核 I/O 往返测试，不是固定断言消息。

12 补丁阶段已将本地套接字测试换为 Qt 公共命名 API：`QLocalServer::listen(name)`、以 `./name` 别名和服务端 `fullServerName()` 连接、检查两端地址、同 UID `SO_PEERCRED`、双向 payload/response、关闭后有界重连失败。13 补丁 consumer 又加入了一个独立 `QProcess` 客户端，以及 TLS loopback 用例。最终 84 项检查全部通过；命名 socket 实际交换 40 字节，独立进程交换 36 字节，TLS 协商 `TLS_AES_256_GCM_SHA384` 并交换 31 字节加密 payload/response。2026-10-10 同包 app-clone UID 真机测试还验证了 Qt 的跨 UID `SO_PEERCRED` 过滤回调；HAP→SSH 系统 UID 连接单独受到 EACCES 安全域边界限制。

## ELF 签名与 SONAME 验证

配方在 `cmake.install()` 后对安装树中的 ELF 调用 HarmonyOS `binary-sign-tool`。同仓库 QtBase 6.11.1 的记录指出 CMake 安装时改写 RPATH 会使原有 HarmonyOS 签名失效，因此该配方沿用 QtBase 安装后签名的处理顺序。另一方面，canfigger 0.3.2 的真机对照记录显示：hnp Clang 链接产生的 `.codesign` 产物可加载，经过 `binary-sign-tool selfSign` 重签的同一库发生 SIGSEGV；cwebx 3.52 也记录其链接器签名可直接使用。

7 补丁基础版本的设备 CI 曾验证签名后消费程序可成功链接、加载和运行。13 补丁候选再次完成 Conan 创建、29 套件 CTest 和 84 项消费者运行；L5 工件门禁通过。插件安装时设置 SONAME 并规范化 CMake 导出路径（包含 `${_IMPORT_PREFIX}/./plugins/...` 的 `./`），将不准确的 `IMPORTED_NO_SONAME_RELEASE TRUE` 替换为对应 `IMPORTED_SONAME_RELEASE`。基础版本设备 `readelf` 对 `libqminimal.so` 的检查记录仍保留在下文。

## 基础版本设备验证结果与边界（7 个补丁）

- 设备 CI 快照：`/storage/Users/currentUser/tmp/codex-qt6-6.0-final-r6-20261008`
- CI 日志：`/storage/Users/currentUser/tmp/codex-qt6-6.0-final-r6-20261008/.ci_logs/conan_build_qt6_6.0.log`
- CTest：7/7 套件通过；总运行时间约 105 秒。
- 上游本地套接字：7 补丁基础版本只运行了 `setSocketDescriptor`。12 补丁候选的完整 `tst_qlocalsocket` QtTest 为 52 passed；最终 13 补丁 UID 修复候选为 53 passed，均为 0 failed、1 skip，跳过原因仅为设备禁止绝对路径 AF_UNIX bind。
- 7 补丁基础版本 Conan 消费端：50/50 检查通过，覆盖原生 abstract AF_UNIX descriptor adoption。
- 12 补丁候选 Conan 消费端：54/54 检查通过；日志输出 `HarmonyOS Qt 6.0 abstract socket payload`（40 bytes），Qt 接收端验证回显响应，同 UID peer credentials 检查通过，关闭端点后有界重连被拒绝。
- 仓库 CI：L0、L1、L2、L4、L5 通过；L2 对部分辅助工具的通用帮助/版本参数发出非阻断警告。
- 插件 SONAME：5 个 CMake 导出目标均有匹配的 `IMPORTED_SONAME_RELEASE`；抽查 `libqminimal.so` 的 `DT_SONAME` 正确。

以上结果限定在提供的 HarmonyOS 6.0 AArch64 真机与 Conan profile，不能外推到其他系统版本或架构。2026-10-10 的 HAP-to-SSH shell UID 探测以 EACCES 结束，作为跨系统安全域访问边界保留。

## 2026-10-10 Qt 客户端跨 UID 地址复测

真机 `QLocalSocket::connectToServer()` 曾在发起系统调用前返回 `Invalid name`。根因是 HarmonyOS 管理地址解析器错误地要求显示地址中的 UID 等于客户端 `geteuid()`；显示地址是客户端要访问的服务端标识，不能用客户端 UID 对它做所有权限制。已保留严格的规范 UID 与 SHA-256 摘要语法检查，去掉 UID 相等比较；Qt 管理监听器仍在入队前用 `SO_PEERCRED` 校验真实连接 UID。

新增的上游 QtTest 在 HarmonyOS AArch64 上按旧实现 RED（`Invalid name`），修复后通过；它使用真实原生抽象 AF_UNIX listener 与 Qt 客户端完成连接。重新签名并安装 HAP 后，同包 app clone UID 20020152 成功连接 UID 20020151 的 Qt 服务、读取对端凭据并发送 47 字节。服务端在清零旧计数后保持活动但 `server_accepted=false`、`payload_bytes=0`，说明 Qt 在 QLocalServer 接收层前拒绝该 UID。相同 UID 的 47 字节请求及 52 字节 echo 也通过。完整 `tst_qlocalsocket` 为 53 passed、0 failed、1 个由设备 EROFS 预期跳过；设备记录位于 `.ci_logs/qt6-6.0-device-20261010/qt6-local-socket-uid-fix-device-evidence.txt`。


## 2026-10-10 clean-worker Conan failure: OpenSSL dependency

Buildbot #81506 passed L0 and JC5. During Qt CMake configuration it reported Could NOT find OpenSSL with both the crypto library and include directory missing; the Qt 6.0 configuration therefore did not register tst_qsslkey, while the recipe still attempted to build that target unconditionally. The run stopped before CTest and the Conan consumer test. This is a missing build/runtime dependency in the clean Conan graph, not a test to blacklist or skip. The earlier 29/29 CTest and 84/84 consumer run had a manually installed HarmonyBrew OpenSSL and therefore did not exercise a clean worker.

The fix declares the published openssl/3.5.6.1.2 recipe, requests its shared OpenSSL 3 build, passes its package folder to Qt as OPENSSL_ROOT_DIR with INPUT_openssl=runtime, and adds its library directory to the CTest OpenSSL runtime candidates. tst_qsslkey remains a required selected test; no skip or blacklist is introduced. AArch64 Conan CI and the real TLS consumer loopback must pass before recording this revision as verified.
