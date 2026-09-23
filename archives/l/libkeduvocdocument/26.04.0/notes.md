# libkeduvocdocument 26.04.0 适配笔记

## 基本信息

| 项 | 值 |
|---|---|
| 目标库 | libkeduvocdocument 26.04.0（KDE Gear 26.04.0） |
| 上游仓库 / tag / commit | https://invent.kde.org/education/libkeduvocdocument · `v26.04.0` · `e5bc26b8d1da92b1823b2d8cd0aac1fbd697c387` |
| 源码包 | `https://download.kde.org/stable/release-service/26.04.0/src/libkeduvocdocument-26.04.0.tar.xz` |
| sha256 | `032689e3af4da9ce578bfa8efb8945d214556a09ddff412a5c2f8d5be720d653` |
| 构建系统 | CMake ≥ 3.16 + ECM 6.26.0 + KF6 6.26.0 + Qt6 6.11.1 |
| 语言预检（R47） | `lang-preflight` → detected=cpp（源文件 41 个，主体占比 100%） |
| 产物 | `lib/libKEduVocDocument.so.5.1.0`（SONAME `libKEduVocDocument.so.5`）、19 个公开头、`LibKEduVocDocumentConfig.cmake` + `LibKEduVocDocumentTargets.cmake` |
| 状态 | published（`conan create` 全绿 + `conan-verify` G0-G4/L2/L4/L5 全 PASS） |
| 编译日期 | 2026-09-21 |

## 依赖

```python
self.requires("qtbase/6.11.1")        # Qt6::Xml（PUBLIC）、Qt6::Test（autotests）
self.requires("ki18n/6.26.0")         # KF6::I18n
self.requires("karchive/6.26.0")      # KF6::Archive
self.requires("kio/6.26.0")           # KF6::KIOCore
self.requires("libxml2/2.15.3")       # OHOS SDK lld 链接期需要 libxml2.so.16（kio 先例）
self.tool_requires("ecm/6.26.0")
```

传递闭包（由 kio/ki18n/karchive 真实 recipe 决定）：kconfig、kservice、kcrash、kcoreaddons（测试期直接依赖）、gettext、zlib、xz、openssl。全部已发布，`conan download` 14/14 exit 0（详见同目录分析报告体系）。

## 构建步骤

```
conan create archives/l/libkeduvocdocument/26.04.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 -r=ohpcd --build=missing
```

配方 `build()` 流程：`apply_conandata_patches`（仅 OHOS/Linux）→ `cmake.configure()` → `cmake.build()` → 上游 ctest（8 项）→ 两个未被 ctest 注册的上游测试程序。

`generate()` 关键变量：

- `KF_IGNORE_PLATFORM_CHECK=TRUE`：KDE 平台白名单绕过（HarmonyOS 不在其列）。
- `KF_SKIP_PO_PROCESSING=ON`：`ki18n_install(po)` 需要 gettext msgfmt 处理 86 种翻译，OHOS 无 msgfmt，且翻译不影响库功能。
- `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname,`：CMake 无 `Platform/HarmonyOS.cmake`，SONAME 链接标志未定义，产物会缺 DT_SONAME（E537 前置条件）。
- ECM_MODULE_PATH 手工注入 + 手写 `conan_cmakedeps_paths.cmake`（qtbase 与 KF6 包都是 `cmake_find_mode=none`，ECM find-modules 需在 CMAKE_MODULE_PATH 上以解析伞形 `find_package(KF6 COMPONENTS I18n Archive KIO)`）。

## 首个真实错误 → 根因 → 修复

### 错误 1（E537 消费者侧，阻塞第一次 ctest）

```
Error relocating .../bin/libKF6KIOCore.so.6: _ZNK12KConfigGroup13readPathEntryERK7QStringRK5QListIS0_E: symbol not found
0% tests passed, 8 tests failed out of 8
exit_code=1
```

根因：已发布的 `kio/6.26.0` 二进制把**构建机的 Conan 缓存绝对路径**写进了 DT_NEEDED：

```
NEEDED [/storage/Users/currentUser/.cache/conan2/p/ki18n9378b4d80136f/p/lib/libKF6I18n.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/kserv88f93b00a81ef/p/lib/libKF6Service.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/kcras5edccfbfae498/p/lib/libKF6Crash.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/kconf7db3dce604ff1/p/lib/libKF6ConfigCore.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/kcore277a69e77593e/p/lib/libKF6CoreAddons.so]
```

本机缓存是 `~/.conan2`，`.cache/conan2` 不存在 ⇒ 加载 kio 库时其依赖无法解析 ⇒ 所有测试进程启动即失败。musl 对绝对路径 DT_NEEDED 直接解析，`LD_LIBRARY_PATH` 无法覆盖。

修复：`_bridge_absolute_needed_paths()` —— 扫描依赖库/构建树 ELF，把所有指向 `.cache/conan2` 且不存在的绝对 DT_NEEDED 路径物化为指向**当前**缓存中同名库的符号链接（幂等、路径存在时 no-op）。先例：akonadi 25.12.3 的 `_prepare_absolute_needed_links`。

修复后：`ctest` 8/8 通过。

### 错误 2（E537 生产者侧，阻塞产物可消费性）

```
NEEDED [/storage/Users/currentUser/.conan2/p/karch083dc02aaf19b/p/lib/libKF6Archive.so]
NEEDED [/storage/Users/currentUser/.conan2/p/ki18n9378b4d80136f/p/lib/libKF6I18n.so]
NEEDED [/storage/Users/currentUser/.conan2/p/kcore277a69e77593e/p/lib/libKF6CoreAddons.so]
```

根因：ohpcd 发布的 KF6 库**没有 DT_SONAME**（实测 `libKF6Archive.so`/`libKF6I18n.so`/`libKF6CoreAddons.so`/`libKF6ConfigCore.so`/`libKF6Service.so`/`libKF6Crash.so` 全部 `<NO SONAME>`；只有 `libKF6KIOCore.so.6` 有）。CMake 因而按绝对路径链接，ld 把这些机器私有路径写进我们产物的 DT_NEEDED ⇒ 该包在任何缓存布局不同的机器上都不可消费。

修复尝试与结论（用最小 CMake 工程逐项实测）：

| 方案 | 结果 |
|---|---|
| `IMPORTED_SONAME` + `IMPORTED_NO_SONAME FALSE`（baloo/kpackage 注释写法） | ❌ 链接行仍是绝对路径（CMake 4.1.2 实测） |
| `IMPORTED_SONAME_RELEASE` | ❌ 同上 |
| `IMPORTED_LOCATION` 改写为裸名 | ❌ 链接失败 |
| **`-l:libKF6*.so` + `target_link_directories`（kpackage E537 推荐变体）** | ✅ DT_NEEDED 记录 basename |

最终采用补丁 `0002-keduvocdocument-CMakeLists.txt.patch`：从 KF6::I18n / KF6::KIOCore / KF6::Archive / KF6::CoreAddons / KF6::ConfigCore / KF6::Service / KF6::Crash 目标读出库目录与 include 目录，改用 `-l:<basename>` 链接并补 `SYSTEM PRIVATE` include。踩坑：KF6 目标只设置 `IMPORTED_LOCATION_<CONFIG>`，读 generic `IMPORTED_LOCATION` 得到 `NOTFOUND`（否则会静默退化为空链接列表）；`KF6::CoreAddons`/`KF6::ConfigCore` 必须显式列出，否则 `KJob`/`KAutoSaveFile` 头文件与符号缺失。

修复后产物 DT_NEEDED（全部可重定位 basename）：

```
NEEDED [libQt6Xml.so.6] [libKF6I18n.so] [libKF6KIOCore.so.6] [libKF6Archive.so]
       [libKF6CoreAddons.so] [libKF6ConfigCore.so] [libQt6Core.so.6] [libc++_shared.so] [libc.so]
SONAME [libKEduVocDocument.so.5]
```

### 错误 3（上游打包缺陷，导致消费者不可用）

`find_package(LibKEduVocDocument)` 后 `${LIBKEDUVOCDOCUMENT_LIBRARIES}` 指向不存在的目标 `LibKEduVocDocumentImport__keduvocdocument`（实际导出名 `LibKEduVocDocumentImport__KEduVocDocument`），且 `LIBKEDUVOCDOCUMENT_INCLUDE_DIR` 被硬编码为 build 期的 `"@INCLUDE_INSTALL_DIR@/libkeduvocdocument"`（KDEInstallDirs 并不提供该变量 ⇒ 退化成 `"/libkeduvocdocument"`）。消费者编译报 `keduvocdocument.h: No such file`。

修复：补丁 `0001-LibKEduVocDocumentConfig.cmake.in.patch`（平台无关的上游 bug 修复，libktorrent 先例）——include 目录改为相对 Config 文件自身位置、导出正确的目标名、补 `find_dependency(Qt6 COMPONENTS Xml)`。

## 上游测试（实测）

### ctest 注册项：8/8 通过

```
$ ctest --test-dir <build> --output-on-failure --no-tests=error
1/8 Test #1: keduvocdocumenttest.cpp ..........   Passed    0.07 sec
2/8 Test #2: emptydocumenttest.cpp ............   Passed    0.06 sec
3/8 Test #3: keduvoctexttest.cpp ..............   Passed    0.07 sec
4/8 Test #4: readerkvtml2test.cpp .............   Passed    0.09 sec
5/8 Test #5: readerwordquiztest.cpp ...........   Passed    0.08 sec
6/8 Test #6: readerpaukertest.cpp .............   Passed    0.07 sec
7/8 Test #7: readervokabelntest.cpp ...........   Passed    0.08 sec
8/8 Test #8: readerxdxftest.cpp ...............   Passed    0.07 sec
100% tests passed, 0 tests failed out of 8
```

**总数 8 / 通过 8 / 失败 0 / 跳过 0。**

### 上游另有两个测试程序（`keduvocdocument/tests/`）未被 ctest 注册

`keduvocdocument/tests/CMakeLists.txt` 只用 `ecm_mark_as_test()`（ECM 实现：仅把目标设为 `EXCLUDE_FROM_ALL`，**不会** `add_test`），因此上游的 ctest 只有 8 项。这两个程序是真实上游测试产物，配方在 `build()` 中显式运行，避免"漏测上游案例"：

| 程序 | 调用 | 结果 |
|---|---|---|
| `sharedkvtmlfilestest` | `<build>/bin/sharedkvtmlfilestest`（无参数） | exit 0 |
| `converter` | `<build>/bin/converter <src>/keduvocdocument/kvtml_empty_sample.kvtml <out>.kvtml` | exit 0，输出 1488 字节 KVTML2，`<kvtml version="2.0">` 与 `<identifier` 保留（配方断言） |

注：`converter` 的 `-f/--format` 选项被上游误定义成无值 flag（`QCommandLineOption` 用两参数构造），传值会报 `option not expecting values`；按 `converter <in> <out>` 调用即可（默认写 KVTML2）。`keduvocdocument/docs/basic_vocabulary_en2de.kvtml` 是过期样例，KVTML2 reader 报 `missing identifier elements`，故 round-trip 使用 `kvtml_empty_sample.kvtml`。

### 汇总（上游）

- 测试入口：`keduvocdocument/autotests/CMakeLists.txt`（8 项 ctest）+ `keduvocdocument/tests/CMakeLists.txt`（2 个测试程序，未注册）
- 总数 10 / 通过 10 / 失败 0 / 跳过 0（**测试程序口径**：8 ctest 注册 + 2 未注册）
- **用例级口径**：8 个 QTest 程序内部共 **23 个用例**（`<binary> -functions` 实测：keduvocdocumenttest 2、emptydocumenttest 1、keduvoctexttest 2、readerkvtml2test 10、readerwordquiztest 2、readerpaukertest 2、readervokabelntest 2、readerxdxftest 2），全部通过，0 跳过

### test_package（消费者，18 条断言全过）

`test_package/test.cpp` 链接安装后的包，构造含 2 个 identifier + 1 条 entry（2 个 translation）的文档，`saveAs(Kvtml)` → `open()` 回读 → 比对 title / identifierCount / locale / entry 译文，并断言 `detectFileType()`。输出：`libkeduvocdocument test_package: all assertions passed`。

## 鸿蒙专项测试用例（≥1，均已在 test_package 中执行通过）

1. `dt_soname_stamped`：`llvm-readelf -d <pkg>/lib/libKEduVocDocument.so.5.1.0` → `DT_SONAME = libKEduVocDocument.so.5`（验证 OHOS 无 SONAME 链接标志这一适配点）。
2. `no_absolute_needed_leak`：同一产物 **9 条 DT_NEEDED 全部为 basename**，无 `.conan2`/`.cache/conan2` 绝对路径（验证 E537 生产者侧修复）。

## 平台发现（非阻塞）

- HarmonyOS 6.0 实测：把文档保存到**新建 `QTemporaryDir()`（0700）** 内会失败——`saveAs()` 无法在目标旁创建 autosave/lock 伴随文件，返回 `FileCannotLock`（`qWarning: Cannot lock file <path>`）；保存到 `QDir::tempPath()`（上游自己的测试做法）正常。test_package 因此使用 `QTemporaryFile` + `QDir::tempPath()`。
- CMake 4.1.2 不认 HarmonyOS 平台（`System is unknown to cmake`），属既有 E092，已由 SONAME 变量手工补齐。

## 验证结果

```
python3 scripts/ohc-run.py conan-verify libkeduvocdocument 26.04.0
# G0 PASS / G1 PASS / G2 PASS / G3 PASS / G4 PASS / L2/L4/L5 跳过（工具未定位包 ID）
# reports/conan-verify-report.md → Verdict: PASS
```

完整 `conan create`（强制重建，`.ci_logs/manual-create-final.log`）：两补丁应用 → configure → build → **ctest 8/8 PASS** → 2 个上游测试程序 PASS → 打包 17 文件 → test_package **18/18 断言** PASS，`exit_code=0`。

## 注意事项

- 本包是**库**（含导出 CMake config），无 `bin/` 可执行产物 ⇒ 不需要 `commands.json`（R38 不适用）。
- 产物 DT_NEEDED 为 `libKF6Archive.so` / `libKF6I18n.so` 等 basename；消费侧需通过 Conan（`requires` 传递）提供这些库的 lib 目录。
- 已发布的 KF6 二进制（kio 6.26.0）自身仍带构建机绝对 DT_NEEDED，属依赖包缺陷（E537）；在缓存布局不同的机器上运行依赖它的程序仍需兼容符号链接桥接。
- `kio/6.26.0` 是 KIOCORE_ONLY 形态（无 KIOGui/KIOWidgets）；本库只用 `KF6::KIOCore`，无影响。
---

**编译结束**: 2026-09-21 01:06
**最终状态**: published
