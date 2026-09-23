# baloo 6.28.0 适配笔记

## 编译环境
- 构建系统: cmake (ECM/KDE Frameworks 6)
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15 (ohos-aarch64 profile, os=OHOS)
- 状态: built

## 编译步骤

1. **依赖图谱设计（W0 实测）**：baloo 需要 Qt6DBus -> qtbase/6.11.1.1（FEATURE_dbus=ON）。
   仓内 KF6 组件（kconfig/kcoreaddons/ki18n/kfilemetadata/kcrash/solid/kidletime）全部引用
   qtbase/6.11.1（FEATURE_dbus=OFF），同图两版本冲突 -> `self.requires("qtbase/6.11.1.1", override=True)`
   统一（abiword-plugin/knewstuff 的 override 先例）。KF6 组件统一用 6.14 系（对齐 kfilemetadata/6.14.0
   的传递依赖），kdbusaddons 用 6.29.0（需 Qt6DBus）。实测 conan install 全依赖二进制命中缓存，零重编。
2. **补丁集**（6 个，全部 OHOS 平台守卫或版本对齐）：
   - 0001: KF_DEP_VERSION 6.28.0->6.14.0（驱动 find_package 下限与导出 KF6BalooConfig.cmake 的
     find_dependency 版本）+ ECM 下限 6.26.0（kdnssd 6.29 先例）+ KIO 组件移除（仅 kioworkers 使用）
     + ki18n_install(po) 跳过（qtbase 无 LinguistTools，kconfig/kfilemetadata 同款）+ E537
     IMPORTED_SONAME 块（KF6 6.14 组件无 DT_SONAME，防绝对路径 DT_NEEDED 泄漏，kpackage 先例）
   - 0002: 不构建 kioworkers 子目录（KF6::KIOCore 唯一消费者）
   - 0003/0004/0005: std::ranges::any_of/find_if -> 经典 std::any_of/std::find_if（OHOS clang15
     libc++ 无 C++20 ranges 算法，实测 repro）
   - 0006: priority.cpp 的 <linux/ioprio.h> 用 __has_include 特性检测守卫（OHOS musl 有
     SYS_ioprio_set 宏但无 glibc 特有的 linux/ioprio.h 头，lowerIOPriority 降级 no-op）
3. **conanfile 关键点**：
   - `tc.blocks.remove("cppstd")`：conan toolchain 的 cppstd=17 普通变量会压制 ECM
     KDECompilerSettings 的 C++20 默认值并在 CMAKE_CXX_FLAGS 后追加 -std=c++17，导致 std::ranges
     编译失败（实测 flags.make 顺序确认）
   - `QT_ADDITIONAL_PACKAGES_PREFIX_PATH` 指向 qtdeclarative（Qt6Config 解析 Qml/Quick 组件，
     akonadi 25.12.3 先例）
   - conan_cmakedeps_paths.cmake 手写（qtbase cmake_find_mode=none）+ 注入 OHOS SDK sysroot usr
     前缀（CMake 无 CMAKE_SYSROOT，FindInotify 找不到 sys/inotify.h 会静默关掉 BUILD_KINOTIFY，
     导致全部 autotests 不注册）
   - build()/test() LD_LIBRARY_PATH 前置 /system/lib64 + qtbase lib（沙箱不兼容 libc++_shared.so，
     bluez-qt/kconfig 先例）
4. **conan create 全绿**（r13，exit 0）：libKF6Baloo.so.6.28.0 + libKF6BalooEngine.so.6.28.0 +
   2 个 QML plugin + balooctl6/baloosearch6/balooshow6/baloo_file/baloo_file_extractor CLI +
   KF6Baloo.pc + KF6BalooConfig.cmake 全部安装。
5. **上游 autotests（BUILD_TESTING=ON）**：OHOS 注册 33 项 ctest（37 项 Linux 注册中 kinotifytest
   为 Linux-only 不编译；filewatchtest/filefetchjobtest/filemonitortest 3 项排除——需 D-Bus
   session bus + 运行中的 baloo_file daemon，OHOS 构建机无 dbus-daemon）。32/33 通过；querytest
   执行但其 testSearchstringParser 的 content-term 数据行在 OHOS 沙箱返回空集（HMDFS QTemporaryDir
   行为差异，上游期望 tmpfs 语义），该测试其余 20 项子断言与全部其他测试通过，如实记录不排除。
6. **test_package**：test_baloo 1/1（ctest + 直接运行双验），覆盖 Query::toJSON/fromJSON round-trip +
   QueryRunnable 构造 + IndexerConfig 析构持久化 round-trip（setFileIndexingEnabled 在析构时 save，
   测试需作用域隔离）。运行时桥接 kfilemetadata/6.14.0 的绝对路径 DT_NEEDED（E537 残留：制品含
   ~/.cache/conan2 绝对路径，musl loader 不做 LD_LIBRARY_PATH fallback，桥接 symlink 解决）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(Qt6 COMPONENTS Qml) 失败 | qtbase cmake_find_mode=none，Qt6Config 只搜 qtbase 前缀 | QT_ADDITIONAL_PACKAGES_PREFIX_PATH=qtdeclarative 包目录（akonadi 先例） |
| 2 | std::ranges 编译报 no member named ranges | 双因：conan cppstd=17 普通变量压制 ECM C++20；libc++ 无 ranges 算法 | tc.blocks.remove("cppstd") + 补丁 0003~0005 换经典算法 |
| 3 | test_package find_dependency(KF6CoreAddons 6.28.0) 版本墙 | KF_DEP_VERSION 写入导出 config | 补丁 0001 将 KF_DEP_VERSION 降为 6.14.0 |
| 4 | test_baloo 运行时 libKF6FileMetaData.so.3 加载失败 | kfilemetadata 制品 DT_NEEDED 含 ~/.cache/conan2 绝对路径，musl 无 fallback | test() 桥接 symlink（stale 前缀 -> 活缓存）+ 本包补丁防新增泄漏 |
| 5 | No tests were found（上游 ctest 空） | CMake 无 CMAKE_SYSROOT，FindInotify 失败 -> BUILD_KINOTIFY=FALSE | conan_cmakedeps_paths.cmake 注入 SDK sysroot/usr 到 CMAKE_PREFIX_PATH |
| 6 | linux/ioprio.h not found | musl 有 SYS_ioprio_set 宏但无该头文件 | 补丁 0006 __has_include 守卫，降级 no-op |
| 7 | IndexerConfig round-trip 断言失败 | setFileIndexingEnabled 仅改内存，save 在析构 | 测试作用域隔离（对象析构后再读） |

## 源码修改

- 6 个补丁（见 conandata.yml），全部有平台守卫或版本对齐说明，非 OHOS 平台不受影响。

## 依赖版本（实测消费）

| 依赖 | 版本 | registry 状态 |
|------|------|---------------|
| qtbase（override 统一） | 6.11.1.1 | ohpcd 已发布（Qt6DBus 消费门禁通过，kdbusaddons 6.29 先例） |
| qtdeclarative | 6.11.1 | ohpcd 已发布（含 Qt6Qml/Qt6Quick） |
| kconfig/kcoreaddons/ki18n/kfilemetadata/kcrash/solid/kidletime | 6.14.0 | ohpcd 已发布（对齐 kfilemetadata 传递依赖，全缓存命中） |
| kdbusaddons | 6.29.0 | ohpcd 已发布 |
| lmdb | 0.9.35 | ohpcd 已发布 |
| ecm (tool) | 6.26.0 | ohpcd 已发布 |

## 验证结果

```bash
conan create . --user=ohpcd --channel=stable   -pr:h=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64   -pr:b=/storage/Users/currentUser/.conan2/profiles/ohos-aarch64 --build=missing
# -> baloo/6.28.0@ohpcd/stable: Package '892988f985074a10018250e7254328f4374c21de' created
# -> 上游 CTest: 32/33 通过（querytest 如实记录平台差异）
# -> test_package: 100% tests passed, 0 tests failed out of 1
# -> PASS: Baloo Query JSON round-trip + QueryRunnable + IndexerConfig round-trip OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（qtbase/6.11.1.1 override + KF6 6.14 系 + tc.blocks.remove cppstd） |
| conandata.yml | 官方源 URL + SHA-256（单 URL，KDE 域名自动镜像） |
| patches/0001~0006 | 版本对齐 + ranges 算法 + ioprio 守卫 + SONAME 可重定位链接 |
| test_package/ | test_baloo（Query/QueryRunnable/IndexerConfig 真实 API 断言）+ MANIFEST.yml |

---

**编译结束**: 2026-09-06
**最终状态**: built
