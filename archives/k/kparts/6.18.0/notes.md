# kparts 6.18.0 — HarmonyOS PC 适配说明

## 1. 交付物

| 项目 | 内容 |
|------|------|
| 上游 | KDE Frameworks 6 — kparts 6.18.0（`https://download.kde.org/stable/frameworks/6.18/kparts-6.18.0.tar.xz`，sha256 `846e522e…41821604`） |
| 产物 | `libKF6Parts.so.6.18.0`（含 DT_SONAME 与 `libKF6Parts.so` / `.so.6` 版本化软链）、KF6Parts 头文件、`KF6PartsConfig.cmake` |
| 配方 | `conanfile.py`、`conandata.yml`、`manifest.yaml`、`patches/0001`、`patches/0002`、`test_package/`（含 `MANIFEST.yml`） |
| 适配路径 | 路径 A（基础适配） |

## 2. 依赖选型（关键决策，含被否决路线的实测依据）

ohpcd 制品仓现状（实测 `conan download` / `conan list`）：

- **无 kio/6.18.0**；`kio/6.26.0` 是 `KIOCORE_ONLY=ON` 构建（无 KIOWidgets 目标、无 `KUriFilter` 头、`include/KF6/KIO/` 只剩 `kio_version.h`）；**`kio/6.14.0` 才是含 KIOCore/KIOWidgets/KIOGui/KIOFileWidgets/urifilters 的全栈包**。
- KF6 6.18.0 系列其余组件（karchive/kconfig/kcoreaddons/ki18n/kservice/solid/kcrash/kbookmarks/kcolorscheme/kcompletion/kguiaddons/kiconthemes/kitemviews/kjobwidgets/kwidgetsaddons/kwindowsystem/kauth/kxmlgui）均已发布。

kparts 6.18 的 `src/navigationextension.cpp` **真实调用 KIOWidgets** 的 `KUriFilter::self()` / `KUriFilterData`（不是仅头文件引用）。三条路线实测：

| 路线 | 做法 | 结果 |
|------|------|------|
| A | KF6 6.18 栈 + kio/6.26.0（KIOCORE_ONLY） | ❌ 编译失败：`'KIO/FileCopyJob' file not found`、`'KUriFilter' file not found`（6.26 KIOCORE_ONLY 无这些头） |
| B | KF6 6.18 栈 + kio/6.14.0（`override=True` 把 kio 自钉的 17 个 KF6 库抬到 6.18） | ❌ kio 被迫源码重建，其 `kioworkers/trash/trashimpl.cpp` 依赖 `<solid/block.h>`，已发布 solid 包只安装 `include/KF6/Solid/Solid/block.h` → `fatal error: 'solid/block.h' file not found`（大小写不匹配） |
| C（采用） | **整图使用已发布的 KF6 6.14.0 系列**（qtbase/6.11.1 + kconfig/kcoreaddons/ki18n/kservice/kwidgetsaddons/kxmlgui/kjobwidgets/kio 6.14.0，`tool_requires ecm/6.26.0`）+ 仅放宽本库 `KF_DEP_VERSION` | ✅ `conan graph info` 实测 **0 Missing / 0 Build**（20 Download + 6 Cache），kparts 从源码构建、依赖全部直接下载二进制 |

补充实测（排除其它候选）：KF6 6.26 系列源码硬性 `find_package(KF6CoreAddons 6.26.0)`，无法用 6.18 头文件降级重建；`kjobwidgets/6.26.0`、`kconfigwidgets/6.26.0` 未发布，故"全 6.26 栈"同样不可行。

KF6 在同一大版本内保持 API/ABI 兼容，kparts 6.18 使用的全部 KF6/KIO API 在 6.14.0 中均存在。

## 3. 补丁说明

| 补丁 | 内容 | 原因 |
|------|------|------|
| `patches/0001-lower-kf-dep-version.patch` | 顶层 `CMakeLists.txt`：`set(KF_DEP_VERSION "6.18.0")` → `"6.14.0"`（仅版本门禁，含注释） | 本库依赖版本门禁须与 ohpcd 实际发布的 6.14.0 系列一致；不改则 `find_package(KF6 6.18.0)` 失败 |
| `patches/0002-lowercase-kio-includes.patch` | 3 处 KIO 头包含改小写：`readonlypart.cpp` 的 `<KIO/FileCopyJob>`→`<kio/filecopyjob.h>`、`<KIO/StatJob>`→`<kio/statjob.h>`，`readwritepart.cpp` 的 `<KIO/FileCopyJob>`→`<kio/filecopyjob.h>` | kio/6.14.0 把 KIO 头安装在 `include/KF6/KIOCore/kio/`（全小写）。OHPC CI 构建机文件系统大小写不敏感（已发布 kio 内含 `lib/plugins/kf6/kio/kio_trash.so`，其源码写 `<solid/block.h>` 仍能构建），但本地/其它环境（ext4）大小写敏感 → 不改写则构建不可移植。声明完全相同，无行为变化 |

两处补丁均为 `patch_type: portability`，不改变库的任何对外行为。

## 4. 构建与测试要点

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：OHOS 不在 KDE 平台白名单内。
- `BUILD_TESTING=ON`：上游 `autotests/` 原样构建，`build()` 内经 `ctest --output-on-failure --no-tests=error` 真实执行；GUI 用例以 `QT_QPA_PLATFORM=offscreen` 运行。
- `CMAKE_CXX_STANDARD=20`：KF6 6.18 头文件使用 C++20 特性，而 `ohos-aarch64` profile 固定 cppstd=17。
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`：CMake 无 `Platform/HarmonyOS` 模块，需显式注入，产物才有 DT_SONAME 与版本化软链（kio/kfilemetadata/baloo 先例）。
- `ECM_MODULE_PATH` 与 `conan_cmakedeps_paths.cmake`：CMakeDeps 生成的 `ECMConfig.cmake` 不传 `ECM_MODULE_PATH`；qtbase 使用 `cmake_find_mode=none`，需手动补 `CMAKE_PREFIX_PATH`。
- **运行库闭环（本次最关键的环境问题）**：已发布 KF6 包的 `DT_NEEDED` 有两种 musl 无法自行解析的形态：
  1. **绝对烙印路径**，如 `/storage/Users/currentUser/.cache/conan2/p/<hash>/p/lib/libKF6XmlGui.so`（发布机 conan 缓存）；
  2. **相对路径**，如 `../../bin/libKF6ConfigCore.so`（kconfig/kiconthemes 等同工程库），musl 对含 `/` 的 `DT_NEEDED` **按进程 CWD 解析**，`LD_LIBRARY_PATH` 对此类名字无效（glibc 差异）。

  OHOS 内核对 ELF 做代码签名校验，改写/patchelf 副本会被拒绝，因此配方（以及真机 payload）采用**软链接**方案：软链接不改变目标文件内容 → 签名保持有效，loader 按期望路径打开即成功（平台知识库 PR #9573 先例）。实现见 `conanfile.py::_prepare_runtime_closure()`：运行 ctest 前扫描依赖闭包（含传递依赖）所有 `.so` 的 `DT_NEEDED`，对每个缺失路径按 basename 在闭包内找到真实库并 `ln -s`；同时把整个依赖闭包加入 `LD_LIBRARY_PATH`。真机侧同一逻辑由 payload 的 `setup.sh` 完成（实测 23 条绝对烙印路径 + 2 条相对路径）。
- 真机 `LD_LIBRARY_PATH` 需含扁平 payload 目录与 `/system/lib64`；`libc++_shared.so` 由 payload 提供。

## 5. 实测结果（真实数据）

环境：WSL2 Ubuntu 22.04 + OHOS 6.0 SDK + qemu-aarch64-static（`ohos-runroot`），profile `ohos-aarch64-run` / `ohos-aarch64`；真机 DAYU200-RK3568（OpenHarmony 6.0.0.47 API20 aarch64，序列号 `450100445634303332018f3e7d2dba00`）。

| 项目 | 命令 | 结果 |
|------|------|------|
| 端到端构建 | `conan create archives/k/kparts/6.18.0 -pr:h ohos-aarch64-run -pr:b default --build=missing` | ✅ `Package '5522206cb3817ff7a8e3ab80ba84eef59742b858' created` |
| 上游测试 | `ctest --test-dir <build> --output-on-failure --no-tests=error`（qemu） | ✅ **100% tests passed, 0 tests failed out of 2** |
| 上游 QTest 明细 | `ctest -V` | ✅ `parttest`：**Totals: 12 passed, 0 failed**（initTestCase+10+cleanupTestCase）；`partloadertest`：**Totals: 8 passed, 0 failed**；合计 **20/20** |
| 消费者端到端 | test_package `test_kparts`（qemu） | ✅ `RESULT: kparts 6.18.0 consumer end-to-end: 15/15 checks passed`（15 项断言） |
| 真机端到端 | `device_runner.sh run kparts_e2e … "sh run.sh"` | ✅ **15/15**，`exit_code: 0`（两次独立运行均通过），证据 `_device_evidence.json` |

真机 payload 说明：`test_kparts` + 35 个共享库（依赖闭包，含 `libKF6KIOWidgets.so`/`libKF6XmlGui.so`/qtbase 等）全部自签名（真实 `binary-sign-tool`），`setup.sh` 建 `bin/`（供 `../../bin/…` 相对解析）与 `/storage/Users/currentUser/.cache/conan2/p/<hash>/p/lib/`（供绝对烙印路径解析）软链树，测试进程 CWD = `lib/test`。

## 6. 已知边界

- 远程 URL 路径（`openRemoteFile` / KIO job）需要 `kioworker` 子进程与 DBus 会话，无 worker 的 qemu 沙箱与纯库真机 payload 均不测试该路径；本次消费者端到端用例基于**本地文件路径**（库内同步分派，`openUrl`→`openFile`→信号→`closeUrl` 全链路真实文件 I/O）。
- kparts 为纯库（无 `bin/` 产物），按 R38 不需要 `commands.json`。
- 运行库软链接只补齐"缺失路径"，幂等；不修改 conan 缓存、不修改依赖包，仅在本库构建树 / 测试 payload 内创建。

## 7. 证据文件

| 文件 | 说明 |
|------|------|
| `outputs/kparts-evidence/local_validate_conan_create.log` | 本地端到端 `conan create` 全量日志（含上游 ctest 与消费者测试输出） |
| `outputs/kparts-evidence/upstream_ctest_verbose.log` | 上游 ctest `-V` 日志（QTest `Totals:` 明细，rule4 依据） |
| `outputs/kparts-evidence/device_e2e_run.log` | DAYU200 真机运行日志（15/15） |
| `outputs/kparts-evidence/_device_evidence.json` | 真机执行证据（job/序列号/系统版本/退出码/时间戳） |
| `outputs/kparts-evidence/device_setup.sh`、`device_run.sh`、`device_payload_prep.log` | 真机 payload 布局与运行脚本、依赖闭包生成日志 |
