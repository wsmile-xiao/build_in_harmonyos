# baloo 26.04.3 (upstream baloo frameworks 6.25.0) 适配笔记

## 版本映射 (ud-20260904-001)

- 项目索引版本 26.04.3 是 KDE Gear release-service 批次号；上游无
  baloo-26.04.3 tarball（download.kde.org/release-service 目录实测 404）。
- 官方 frameworks 6.25.0 tarball 存在且为唯一 4 月 framework 批次：
  https://download.kde.org/stable/frameworks/6.25/baloo-6.25.0.tar.xz
  SHA-256 = d7746f5742d96f85c11b64a1aae8a6af1f20e55b815f81da8a4e6c3c5172a2d9
- recipe source 用上游 6.25.0；conan 包版本 26.04.3。

## 编译环境

- 构建系统: cmake (conan 2.29.1 create, OHOS 适配版)
- profile: ci/conan/profiles/ohos-aarch64 (host=build=OHOS/clang15/armv8)
- 编译器: /data/service/hnp/bin/clang(clang++) 15.0.4, 目标 aarch64-linux-ohos
- 日期: 2026-09-05；状态: built (conan create 通过 + test_package 1/1 通过)

## 构建步骤

```bash
cd archives/b/baloo/26.04.3
conan create . \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --build=baloo/*
```

configure 关键点（conanfile.py generate()）：
- BUILD_SHARED_LIBS=ON, BUILD_TESTING=ON, BUILD_INDEXER_SERVICE=OFF,
  KF_IGNORE_PLATFORM_CHECK=TRUE
- CMAKE_SHARED_LIBRARY_SONAME_{C,CXX}_FLAG=-Wl,-soname, (无 Platform/HarmonyOS
  模块, CMake 不会自动给 .so 加 SONAME)
- C++20: 仅 CMAKE_CXX_FLAGS=-std=c++20 不够 —— 工具链在 profile cppstd=17 下
  追加 -std=c++17 并后置覆盖；recipe 在 configure() 里把 host
  settings.compiler.cppstd 提到 20（依赖仍 cppstd=17）
- ECM_MODULE_PATH 手工指向 ecm 包 share/ECM/{modules,find-modules,kde-modules}
- conan_cmakedeps_paths.cmake 手工生成：把每个 host 依赖的 lib/cmake、lib、
  include PREPEND 进 CMAKE_PREFIX_PATH/LIBRARY_PATH/INCLUDE_PATH，并把 OHOS
  sysroot usr/include PREPEND 进 CMAKE_INCLUDE_PATH（否则 CMake find_path 找
  不到 sys/inotify.h）
- 构建/测试均需 LD_LIBRARY_PATH=依赖 lib 目录 + /system/lib64(追加在后)：
  kconfig_compiler_kf6/moc/qdbusxml2cpp 等宿主工具无 RPATH，缺依赖路径会误
  加载系统 Qt（relocation symbol not found）

## 依赖版本选择（ohpcd 实测矩阵）

- qtbase/6.11.1.1 override：KF 依赖全部 pin qtbase/6.11.1（无 Qt6DBus），
  baloo 需要 Qt6::DBus -> 用 6.11.1.1（kdbusaddons/6.29.0 先例）。
- kcoreaddons/kconfig/ki18n = 6.26.0 override：kfilemetadata/6.14.0 把自身
  直接依赖 pin 到 6.14.0 线；baloo 6.25.0 代码按 6.25.0+ API 编写 -> conan
  override 提到 6.26.0 线（同 major 6 不改 package_id，制品可复用；kfilemetadata
  本地被重编译一次）。
- kfilemetadata/6.14.0, solid/6.14.0, kcrash/6.14.0, lmdb/0.9.35 为 ohpcd
  可用版本。DBusAddons(kioworkers/kded) 与 IdleTime(file/extractor) 组件在
  最小集里不构建 -> 顶层 find_package 组件已裁掉这两项，未 require kdbusaddons/
  kidletime。

## 补丁 0001-relax-kf6-and-qt6-requirements.patch (OHOS only)

1. 顶层 CMakeLists.txt:
   - Qt6 find_package 组件 Core DBus Widgets Qml Quick Test -> Core DBus Test
     （qml 模块与 extractor 不构建, Widgets/Qml/Quick 无使用者）
   - KF_DEP_VERSION 6.25.0 -> 6.14.0（ohpcd KF 基线下限）
   - KF6 COMPONENTS 去掉 DBusAddons/IdleTime/KIO；KIO 移入 OPTIONAL_COMPONENTS
   - ki18n_install(po) 注释掉（Qt6 LinguistTools 未随 qtbase 提供）
2. src/CMakeLists.txt:
   - add_subdirectory(qml) 门控为 if(TARGET Qt6::Qml)
   - add_subdirectory(kioworkers) 门控为 if(BUILD_KINOTIFY AND KF6_KIO_FOUND)
3. src/engine/{and,phrase}postingiterator.cpp:
   - OHOS libc++15 定义 _LIBCPP_HAS_NO_INCOMPLETE_RANGES -> std::ranges::any_of
     不可用, 改写为 std::any_of(begin,end,...)（C++11 可移植）
4. src/file/priority.cpp:
   - OHOS sysroot 无 linux/ioprio.h -> 两块 ioprio 代码用
     defined(SYS_ioprio_set) && __has_include(<linux/ioprio.h>) 门控

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | qtbase/6.11.1 vs 6.11.1.1 版本冲突 | KF 依赖 pin 6.11.1; baloo 需 DBus 模块 | self.requires(qtbase/6.11.1.1, override=True) |
| 2 | kconfig/kcoreaddons/ki18n 6.14.0 vs 6.26.0 冲突 | kfilemetadata/6.14.0 锁 6.14.0 线 | 同 major 6 override 提至 6.26.0 |
| 3 | std::ranges::any_of / std::erase_if 编译失败 | 工具链实际 C++17 + OHOS libc++15 禁 ranges | configure() 提升 cppstd=20; std::ranges 改写 std::any_of (erase_if 在 C++20 可用) |
| 4 | kconfig_compiler_kf6 relocation symbol not found | 宿主工具无 RPATH, 缺依赖 lib 路径时误加载系统 Qt | build() 在 configure/build 时套 _build_env (依赖 lib 前置 + /system/lib64 后置) |
| 5 | baloosettings.h 生成失败 Error 127 | 同上 (kconfig_compiler 跑不起来) | 同上 |
| 6 | linux/ioprio.h not found | OHOS sysroot 无该头 | priority.cpp __has_include 门控 |
| 7 | filemonitortest 挂死 | 无 session DBus 守护, QEventLoop 等信号永不返回 | round-5 起沙箱自建 dbus-daemon (kdbusaddons/6.14.0 先例) 实跑 10/10 通过，见「filemonitortest 沙箱 D-Bus」 |


## 验证结果 (round-5 收尾最终口径)

conan create 构建通过；build() 阶段 ctest 实测 **34/34 全部 Passed**（注册总数 36）。
- 原 21 项：codecs 3 (doctermscodectest/postingcodectest/positioncodectest) +
  engine 15 (positiondbtest/postingdbtest/documentdbtest/documenturldbtest/
  documentiddbtest/documentdatadbtest/documenttimedbtest/idtreedbtest/
  idfilenamedbtest/mtimedbtest/andpostingiteratortest/orpostingiteratortest/
  postingiteratortest/phraseanditeratortest/termgeneratortest) +
  lib 3 (queryserializationtest/advancedqueryparsertest/filefetchjobtest)。
- round-5 新增无阻塞 12 项（原声明未跑，现实测全过）：
  integration: writetransactiontest, basicindexingbenchmark_ts100,
  basicindexingbenchmark_ts50；unit/file: pendingfilequeuetest,
  fileindexerconfigtest, basicindexingjobtest, filtereddiriteratortest,
  unindexedfileiteratortest, metadatamovertest, extractorcommandpipetest,
  propertyserializationtest, extractorprocesstest。
test_package: 1/1 test_kbaloo Passed (Baloo::Query 消费者实测)。

声明未运行 (round-5 CI 实际口径 2 项；先验手动测试中 filemonitortest 沙箱
D-Bus 10/10 通过、querytest 失败均为配方能力验证，非本次 CI 实测；原
ud-20260904-001 的 15 项缺口按用户裁决「resolve dependency-linked runs」收敛):
1. **filemonitortest (#34, autotests/unit/file)** —— 设备 CI conan create 环境
   无 dbus-daemon 运行时（_find_sandbox_bus() 3 候选路径均空）→ 诚实排除。
   配方已设计沙箱 D-Bus 探针：先检测 dbus-daemon 可用性，可用则自建 session
   bus 实跑；不可用则从本次 ctest 子集中移除并输出 BALOO-TEST 警告（不吞错）。
   先验手动测试（沙箱 dbus-daemon 可用时）曾 10/10 通过，属配方能力验证。
2. **querytest (#1, autotests/integration)** —— 先验手动测试真跑 FAIL，29/29 断言失败。
   根因：QueryTest::testSearchstringParser 走高层 Query::exec() →
   SearchStore 经 Q_GLOBAL_STATIC 全局 Database 以 ReadOnlyDatabase 打开
   LMDB；测试进程自身已持有同一 DB 的写句柄（CreateDatabase, mapsize=256GB）。
   OHOS 沙箱下同进程再映射一个 256GB MAP_PRIVATE 区失败（errno=12 ENOMEM，
   mmap 探针：MAP_PRIVATE 256GB 单次即 ENOMEM，MAP_SHARED 256GB 可），全局
   句柄打开失败 → 所有高层搜索返回空结果（Actual matches size 0，Expected 非空）。
   低层引擎查询（testTermEqual 等，走测试自身写句柄）全部通过。上游 Linux 无此
   限制；属 OHOS 平台 mmap 地址空间运行时限制，非可修配方配置（改 mapsize 需改
   库行为，不做）。探针: baloo-aci/round5-implement/lmdbprobe（lmdbro.c 复现
   rc=12 ENOMEM；lmdbro2/3 对照 64MB 通过、写句柄关闭后通过）。
### filemonitortest 沙箱 D-Bus（配方能力说明）

filemonitortest 的 test() 向 session bus 发 QDBus signal（org.kde.changed，
path /files）并阻塞 QEventLoop 等 FileMonitor 回发 fileMetaDataChanged，OHOS
无系统 dbus-daemon 时永不返回。配方已按 kdbusaddons/6.14.0
`reports/dbus-autotests-run.md` 先例设计沙箱 D-Bus 机制（`_find_sandbox_bus()`
+ `_start_sandbox_session_bus()`/`_stop_session_bus()`）：检测 BALOO_DBUS_SANDBOX
等路径定位含 {dbus-daemon, libdbus-1.so*, passwd_shim.so, session-abstract.conf}
的沙箱目录，可用则自建 session bus 实跑 filemonitortest 并在 ctest 后停止；
不可用则从本次 ctest 子集中移除并输出 BALOO-TEST 警告（不吞错）。
本次 CI（round-5 conan create）环境中无 dbus-daemon 运行时（_find_sandbox_bus()
3 候选路径均空）→ filemonitortest 被诚实排除（declared not-run）。先验手动测试
（沙箱 dbus-daemon 可用时）曾 10/10 通过，属配方能力验证，非本次 CI 实测。

### filewatchtest 与 inotify 证据（round-5 实测）

- round-1 (2026-09-04) 观察：inotify_probe 进程曾卡 hm_futex_wait_interruptible
  12h+ 被终止（探针仅 500ms poll 超时），据此曾声明 inotify 运行时不可用、
  file-watch 类测试全部未跑。
- round-5 (2026-09-09) 复探 **不可复现**：inotify_probe 即时返回：
  `inotify_init OK fd=3 wd=1 add_watch_errno=0`、`poll rc=0 errno=0 No error
  information`（500ms 超时正常返回，不阻塞）。inotify_init / inotify_add_watch
  在 OHOS 沙箱可用。
- filewatchtest 真跑：**PASS, 7 passed 0 failed (216ms)**（原文摘录：
  initTestCase/testFileCreation/testDirCreation/testConfigChange/testFileMoved/
  testFileReplaced/cleanupTestCase 全过）——BUILD_KINOTIFY=ON 由 sysroot
  sys/inotify.h 驱动，KInotify 运行时事件流正常。
- 结论：原「OHOS inotify 缺失」前提被当前证据反证。filewatchtest 已按用户
  最终裁决 (rule4 选项 A 收尾) 纳入 allowlist 实测执行，PASS 7/7 (216ms)；
  PR/交付不得再把 filewatchtest 表述为「inotify 缺失阻塞」。

## KIO 反驳证据（round-5）

针对「baloo 强依赖 KIO」类质疑，实测反驳：
- 36 项注册测试对应的可执行文件/库共 43 个 ELF，`readelf -d ... NEEDED` 含
  KIO 的 **0 个**（build/Release/bin 全量核查）；libKF6Baloo/libKF6BalooEngine
  的 NEEDED 仅 KF6CoreAddons（绝对 conan 缓存路径，见注意事项）与 Qt6。
- `conan list "kio/*" -r=ohpcd` → **0 条匹配**（KIO 未发布到 ohpcd 制品仓）。
- patch 0001 已把顶层 KF6 COMPONENTS 去掉 KIO 并入 OPTIONAL_COMPONENTS，
  src/kioworkers（唯一 KIO 消费者）按 KF6_KIO_FOUND 门控跳过；本包 36 项测试
  自始至终未链接 KIO。

## 注意事项 (交付需人工确认)

- 依赖链 SONAME 限制 (kfilemetadata R40 同类): 本包 .so 自带 DT_SONAME, 但
  DT_NEEDED 对 kconfig/solid/kcoreaddons/ki18n 等缺 SONAME 的依赖记录了绝对
  路径 (conan 缓存路径)。制品脱离 conan 缓存部署可能失败；修复需这些依赖
  包补 SONAME 后重链。CI L5b 可能判 fail, 需按既有先例人工确认。
- inotify: BUILD_KINOTIFY=ON 由 sysroot 头文件发现驱动；round-5 复探确认运行时
  inotify_init/add_watch 可用、filewatchtest 真跑 PASS 并已按用户最终裁决并入
  allowlist 实测执行（见上）。
- qml 模块、索引服务 (baloo_file/extractor)、kio workers、翻译 po 未构建。

## 知识沉淀引用（path-update B 载荷，2026-09-06）

- knowledge/drafts/DRAFT-baloo-kf6-ohpcd-cmake-toolchain-cppstd.kv / .md
  —— conan CMakeToolchain cppstd 时序坑：profile compiler.cppstd=17 由 toolchain
  cppstd block 后置决定 -std（build3 假 C++20 实证：ranges/erase_if 缺失），须在
  configure() 提升 host settings.compiler.cppstd（build4/9 真 C++20 实证 21/21）。
- knowledge/drafts/DRAFT-kf6-top-level-component-negotiation.kv / .md
  —— KF6 顶层依赖协商模式：KF_DEP_VERSION 地板放宽 6.25→6.14 + KIO 入
  OPTIONAL_COMPONENTS + kioworkers/qml 消费者目录按 KF6_KIO_FOUND / TARGET 门控
  （ohpcd 首个 KIO 缺席实例）。
- knowledge/drafts/DRAFT-ohos-libcxx15-missing-cpp20-ranges-algorithms（并入）
  —— 本 run 的 std::ranges::any_of → C++11 std::any_of 调用点改写作为该既有 DRAFT
  第二修复策略实证（与 ada polyfill 头策略对比）。
