# kmbox 26.04.3

本配方对应 KDE PIM 26.04.3 正式发布版本。上游独立的 `testReadOnlyMbox()` 在文件系统不强制 `chmod` 只读时才触发 `QSKIP`；`testSaveAndLoad()`、`testAppend()` 等持久化用例仍执行。
本配方仅面向 HarmonyOS；`manifest.yaml` 使用仓库现有 `built` 状态值记录配方产出，具体上游与消费者测试结果另列于 `test_results`。

## HarmonyOS PC 实测（2026-10-10，官方 URL + get()）

- 设备：HarmonyOS AArch64，独立 `CONAN_HOME=/storage/Users/currentUser/work/psj/ch-kmbox13448`。配方文件上传后逐个 md5 对拍。
- 命令：`conan create archives/k/kmbox/26.04.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`。
- 退出码：0。日志：`~/work/psj/kmbox13448fix-create.log`。
- `source()` 日志：`Sources correctly downloaded from https://download.kde.org/stable/release-service/26.04.3/src/kmbox-26.04.3.tar.xz`。
- 上游 CTest：`mbox-mboxtest` 1/1 通过（`100% tests passed out of 1`，耗时 1.69 秒）。
- 消费者：`test_package` 编译并运行 `test_kmbox`，打印 `PASS: KMbox wrote and reread one MIME message`。程序内 11 个运行期断言随该进程通过；本轮只跑了默认 `shared=True`。

## HarmonyOS PC 实测（2026-10-04，提交了源码包的旧配方）

- 设备：HarmonyOS AArch64，Conan 2.29.1；使用独立任务缓存。
- CI worker 查询 `kmime/26.04.3` 时遇到 registry 策略/网络错误，无法据此判定该版本制品是否已发布。为隔离验证本包，在独立缓存中从匹配版本配方本地创建 kmime 依赖包；依赖未上传，其他 PR 未修改。
- `conan create archives/k/kmbox/26.04.3 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`：退出码 0。
- CMake/CTest 由 HarmonyOS 构建环境提供；因使用 `ctest --test-dir`，验证要求 CMake 3.20 或更高版本。配方不下载或固定主机构建工具版本。
- 上游 CTest：注册 1 个目标 `mbox-mboxtest`，共享与静态构建各实跑 1/1 通过。
- 配方在 `build()` 中执行上游 CTest；测试失败会使当前 Conan 包构建失败。这样可阻止未经上游用例验证的包进入消费者测试，代价是每次配方构建都承担测试时间。
- Conan 消费者：共享与静态构建的 `test_kmbox` 各实跑 1/1 通过；程序内 11 个运行期断言覆盖临时目录、mbox 创建、加载、写入、保存、重载与邮件头读取。包发现与链接在 CMake 配置、构建阶段验证，不计入这 11 项。
- AtomCode 指出 RPATH/linker flags 冗余、CTest 超时偏短、消费者未覆盖传递发现路径及清单命令不可执行；现已移除无用 RPATH/linker flags，将超时统一到 300 秒，将消费者改为仅声明 kmbox/qtbase，并把 test_package_tests.command 改为实际 conan create 命令。上述最终源码在设备独立缓存中共享、静态各重新执行一次；每次 conan create 退出码 0，上游 CTest 1/1、消费者 1/1 且 11 项检查通过。
- `-o kmbox/*:shared=False` 实际生成 `libKPim6Mbox.a`；默认 `shared=True` 构建共享库，证明 Conan 选项已接入 CMake。
- CTest 与消费者在未复制依赖 `.so` 到测试目录时均通过；运行期搜索路径由 Conan `conanrun` 提供。消费者测试中 `appendMessage()` 返回 `MBoxEntry`，当前用法已在两种构建中编译并运行。
- 保留 `cmake_find_mode=none` 以使用上游安装的 `KPim6MboxConfig.cmake`（导出 `KPim6::Mbox`）；kmbox 配方声明 kmime 传递依赖，消费者只需声明 kmbox 即可通过 Conan 依赖图发现传递配置。消费者测试仅声明 kmbox 与 qtbase，同时直接包含 `KMime/Message`，用于覆盖这条传递发现路径。
- 测试配方不再直接声明未使用的 kcodecs 依赖；因 kmime 依赖图需要，Conan 仍会解析并安装传递依赖 kcodecs。
- 运行时依赖由 Conan `conanrun` 环境提供：配方声明 `runenv_info` 将 kmbox 的库目录加入 `LD_LIBRARY_PATH`，依赖包的运行环境由 Conan 一并合并。消费者配方只补充 Qt 插件搜索路径、offscreen 平台及隔离的 HOME/XDG 目录；共享与静态消费者实测通过，不依赖把不同 Conan 包目录假定为同一 `$ORIGIN`。
- 可核验的远端 CI 历史：构建 #70556（worker CI-033）在 L0i 查询 `kmime/26.04.3` 时三次重试均遇 `system acceleration policy not enabled`，日志判定 `registry_unreachable`，L1/L2/L4/L5 未执行；#70551（worker CI-002）在 worker-prep/git-clone 阶段遇 SSH bridge `Connection refused`。#70595（worker CI-023）机器人仅报告校验失败，评论未提供阶段日志，本记录不据此认定为基础设施故障。上述记录属于当时的头 `886887ae`，不是现在的头。`kmime/26.04.3` 仍是本配方的真实依赖，本 PR 不删除该依赖，也不改用镜像绕过 L0i。上游 CTest 继续在 `build()` 中执行，不提供跳过开关；测试失败会使 `conan create` 失败。

## 源码地址（2026-10-10）

- 官方单一地址：`https://download.kde.org/stable/release-service/26.04.3/src/kmbox-26.04.3.tar.xz`。`source()` 调用 `get(self, **self.conan_data["sources"], strip_root=True)`。`export_sources()` 只导出补丁。
- 本机下载与真机 `curl` 均为 33,952 字节，SHA-256 `ff39d6616f9d56a318cbb4e029bd42960f8a115579bdce7785e0af6f1fe5ee59`。该值与 `https://kde.org/info/releases-26.04.3/` 的 SHA-256 表，以及官方 mirrorlist 的 Known hashes 一致。
- 此前把同字节包放进 `s/kmbox-26.04.3.tar.xz` 并随配方提交，使 GitCode `pull/13448.diff` 失去二进制补丁数据。CI 在 checkout-pr 报 `missing binary patch data`，约 4–6 秒退出。机器人把它标成网络问题，与阶段不符。该二进制已从配方删除。
- 真机可以访问 `download.kde.org`，因此不改用 mirrorservice.org 或其它镜像。#70762 的 SSH bridge `Connection refused` 发生在 checkout 之前，换源也不能修复它。
- `kmime/26.04.3` 已合入 main，制品仓已有该版本（pusher `ohpcd-bot`）。配方仍 `requires("kmime/26.04.3")`，不在本包内自建该依赖。

## 2026-10-04 旧归档配方的设备记录

以下结果属于当时提交了源码包的配方，不是本头 `get()` 路径的证据：

- 共享与静态 `conan create` 退出码均为 0；上游 `mbox-mboxtest` 各 1/1；消费者各 1/1，每种 11 项运行期断言。日志：`~/work/psj/kmbox-26.04.3-new-shared.log`、`~/work/psj/kmbox-26.04.3-new-static.log`。

