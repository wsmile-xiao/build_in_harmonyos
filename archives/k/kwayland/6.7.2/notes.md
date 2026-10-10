# kwayland 6.7.2 适配笔记

## 为什么是 6.7.2（Plasma 版线，不是 KF6 6.26）

kwayland 自 Plasma 6 起脱离 KDE Frameworks 发布节奏，跟随 Plasma
版本线（6.7.2 与 kwin 6.7.2 / kdecoration 6.7.2 / libkscreen 6.7.2
同线）。kwin 6.7.2 硬性要求：

```cmake
find_package(KWayland ${PROJECT_VERSION})
```

kwin 里大量 `#if KWAYLAND_VERSION >= QT_VERSION_CHECK(6, 7, 0)` 分支，
6.7.2 是同线最新，选它。

## 上游硬依赖与本配方消费方式

| 上游要求 | 配方做法 |
|---|---|
| Qt6 ≥ 6.10（Gui + Private、Concurrent、WaylandClient + Private） | qtbase/6.11.1.2 + qtwayland/6.11.1（ohpcd 钉版） |
| Wayland 1.24（Client） | wayland/1.22.0 + 0001 降 min + 0002 剔除 wl_fixes（见下） |
| WaylandProtocols 1.15 | tool_requires wayland-protocols/1.36.1（=qtwayland 同 ref，见下） |
| PlasmaWaylandProtocols 1.21 | tool_requires plasma-wayland-protocols/1.21.0 |
| EGL | OHOS SDK sysroot（EGL_INCLUDE_DIR/EGL_LIBRARY 缓存变量；运行期走 /system/lib64/libEGL.so，见下） |
| WaylandScanner | 钉 WaylandScanner_EXECUTABLE（见下） |

KWaylandClient 链接：`PUBLIC Qt6::Gui` + `PRIVATE Wayland::Client
Qt6::Concurrent Qt6::GuiPrivate Qt6::WaylandClientPrivate`（实测
src/client/CMakeLists.txt:237）。私有链接不进导出接口，消费者只需
Qt6Gui（上游 KWaylandConfig.cmake.in 只有 `find_dependency(Qt6Gui)`）。
导出目标命名空间是 `Plasma::`（顶层 CMakeLists.txt:122
`install(EXPORT KWaylandTargets ... NAMESPACE Plasma::)`），消费者链接
`Plasma::KWaylandClient`。

## wayland 1.24 → 1.22（patches/0001）

qtbase/6.11.1.2 与 qtwayland/6.11.1 都钉 wayland/1.22.0，混入 1.24.0
是图冲突（libkscreen 6.7.2 同款先例）。kwayland 只用稳定 Wayland 客户端
API，1.22 已全部提供；0001 把 `find_package(Wayland 1.24)` 降到 1.22。

## wl_fixes 在 1.22 下的处理（patches/0002，第五轮 G2 实录）

降 min 之后暴露真依赖，第五轮 G2 编译挂：

```
registry.cpp:341:20: error: use of undeclared identifier 'wl_fixes'
registry.cpp:498:28: error: use of undeclared identifier 'wl_fixes_interface'
registry.cpp:499:38: error: unknown type name 'wl_fixes'
registry.cpp:499:84: error: use of undeclared identifier 'wl_fixes_interface'
qtbas.../QtWaylandClient/6.11.1/QtWaylandClient/private/qwayland-wayland.h:
    1317/1323/1325/1326/1327/1338: error: no struct named 'wl_fixes' in
    the global namespace
```

wl_fixes 是 Wayland **1.24 新增**接口（1.22.0/1.22.0.1 头文件 0 处出现，
1.24.0 有 26 处、带 `#ifndef WL_FIXES_INTERFACE / #define
WL_FIXES_INTERFACE` 守护宏）。图里升 1.24 走不通：qtbase/6.11.1.2 精确
钉 1.22.0，override 会把 qtbase/qtwayland 拖入源码重建（0001 已定
1.22）。上游 kwayland 6.7.2 也没有针对旧 wayland 的条件编译——它的
发布基线就是 1.24。故 0002 做编译期剔除，两处：

1. `src/client/registry.cpp`：**全部 5 处** wl_fixes 使用用
   `#ifdef WL_FIXES_INTERFACE` 守护——成员声明（WaylandPointer<
   wl_fixes, wl_fixes_destroy>）、release() 里的
   wl_fixes_destroy_registry、destroy() 里的 fixes.destroy()、
   setEventQueue() 里的 addProxy、handleAnnounce() 里的
   wl_fixes_interface 匹配 + bind。1.22 头文件不定义该宏 → 整段编掉。
   功能零损失：1.22 的合成器不会宣告 wl_fixes，守护掉的都是死代码；
   1.24+ 下宏已定义，编译结果与上游逐字相同（no-op）。
2. `src/client/surface_p.cpp`：全树唯一包含 QtWaylandClient 私有头的 TU
   （`private/qwaylandwindow_p.h` → `qwayland-wayland.h`）。Qt 6.11 生成的
   qwayland-wayland.h 里 `QtWayland::wl_fixes` 包装类无条件引用
   `struct ::wl_fixes *`（1317-1338 六处，均为**类型**引用、无任何
   `wl_fixes_*` 函数引用），而 1.22 头文件没有该类型声明 → 在包含前补
   `#ifndef WL_FIXES_INTERFACE / struct wl_fixes; / #endif`
   （只需不完全类型；kwayland 从不调用该接口，Qt 包装类只存指针成员，
   其析构在库内实现）。

   运行期安全实证（第四轮设备侧 nm）：libQt6WaylandClient.so.6 **定义了**
   QtWayland::wl_fixes 包装、且**无未定义 wl_fixes 符号**——wayland
   生成头里的 wl_fixes_* 是 static inline，已编进库内；1.22 的
   libwayland-client 下不会有未解析符号，kwayland 自身也从不 bind 该全局。

补丁经双引擎验证：GNU `patch -p1 --fuzz=0` 与 conan 同款 `patch_ng`
（strip=0 / fuzz=False，即 `apply_conandata_patches` 的实际参数）都干净
应用，且 0001→0002 顺序叠加无冲突、结果与手改树逐字节一致。

## 版本化 .so 符号链接链在 OHOS 建不出来（patches/0003，第六轮 G2 实录）

第五轮编译全过之后，第六轮 G2 挂在链接期（真机 conan-verify 原文）：

```
CMake Error: failed to create symbolic link
    '../../bin/libKWaylandClient.so.6': Permission denied
CMake Error: cmake_symlink_library: System Error: Permission denied
CMake Error: failed to create symbolic link
    '../../bin/libKWaylandClient.so': Permission denied
```

根因不在 kwayland 源码：KWaylandClient 上游带 `VERSION ${KWAYLAND_VERSION}`
/ `SOVERSION ${KWAYLAND_SOVERSION}`（src/client/CMakeLists.txt:245-246），
配方又按 kdecoration 先例定义了 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG`
——两者齐全时 CMake 生成版本化三段名（libKWaylandClient.so →
.so.6 → .so.6.7.2），产物规则里带两条 `cmake -E cmake_symlink_library`；
而 **OHOS 构建环境不允许创建符号链接**（各目录 ln -s 一律 EPERM，
`.conan2`/`bih` 全树 0 个 `-type l`），真身刚链接出来就被失败连带删除。

生态侧证据一致——已发布 OHOS 库全是**单一无版本实体文件**：

- KScreenLocker 包内就是 `lib/libKScreenLocker.so`（无 .so.6/.so.6.7.2）；
  kscreenlocker 配方 docstring 明说 "the missing platform soname flag
  keeps the build free of the versioned .so symlink chain"；
- kdecoration 配方注释是同一件事的另一半：没有 soname 标志 → 库没有
  DT_SONAME → musl 加载器解析不了 bin//lib/ 相对的 NEEDED 条目；
- qtbase/wayland 这类要版本名的包，走 install 期**同尺寸副本**
  （nlink=1）绕开符号链接。

0003 的做法：从目标上去掉 VERSION/SOVERSION（产出单一无版本实体文件，
与已发布制品同形），配方的 soname 标志保留 → 链接器仍写入
`DT_SONAME=libKWaylandClient.so`，消费者的 DT_NEEDED 保持裸文件名、
可重定位。`ecm_setup_version` 产生的 KWAYLAND_VERSION/SOVERSION 变量
本身不动（版本头 kwayland_version.h 与 KWaylandConfigVersion.cmake
照常生成，kwin 的 `find_package(KWayland 6.7)` 不受影响）。

真机探针（缓存构建树，全部编译产物已在位，只重链接）实证：`make` 全绿、
make 日志里 `cmake_symlink_library`/`symbolic link` **0** 次、bin/ 下只有
单个 `libKWaylandClient.so`（无 .so.6/.so.6.7.2、无任何符号链接）、
`readelf -d` 有 `SONAME libKWaylandClient.so`，消费者可执行文件
（copyClient/panelTest/xdgforeign-test）的 DT_NEEDED 记录为裸
`libKWaylandClient.so` 而非路径。中途曾误判"无版本信息后 soname 标志是
死配置"（依据是探针日志被 `head -30` 截断），第二次探针的 BEFORE 快照
（标志在、无版本信息）readelf 明确有 SONAME，遂保留标志、补丁只做
"去版本"一件事（也与 kdecoration/layer-shell-qt 两个已合并先例一致）。

补丁同样经三引擎验证：GNU `patch -p1 --fuzz=0`、conan 同款 `patch_ng`
（strip=0 / fuzz=False）各自干净应用，且 0001→0002→0003 全链顺序叠加
无冲突、结果与手改树逐字节一致。

## wp/pwp 为什么放 tool_requires

- wayland-protocols 若 host require，会与 qtbase 的 host requires
  wayland-protocols/1.36 撞版本（qtwayland 同款先例：把
  wayland-protocols 放 build context）。
- 两者都是纯 XML 数据，只在构建期被 wayland-scanner 消费，运行时零依赖；
  tool_requires 还避免 package_id 耦合（换 wp 版本不会触发 kwayland
  重建级联）。
- 注意：tool_requires 不进 `self.dependencies`（host 图），generate()
  里用 `self.dependencies.build.get(...)` 取路径。

## 为什么用 wp/1.36.1 而不是链上的 wp/1.48（第三轮 G2 实录）

第三轮 G2 挂在 build context 的 wayland 版本上：

```
ERROR: Version conflict: Conflict between wayland/1.22.0 and
wayland/1.24.0 in the graph. Conflict originates from kwayland/6.7.2
```

三路来源：`pwp/1.21.0 → wayland/1.22.0`、`wp/1.36.1`（qtwayland 6.11.1
的 tool_requires，传递进本配方的 build context）`→ wayland/1.22.0`、
`wp/1.48 → wayland/1.24.0`（其配方自钉，打包的静态 scanner 从 wayland
1.24 源码编译）。build context 与 host context 一样要求同一 context 内
同名包版本唯一：wp/1.36.1 与 wp/1.48 只要同居一个 build context，wayland
就必然裂成 1.22/1.24 两版。

**override 化解不了**（实测无效 + 源码级原因）：`Requirement.__hash__ =
hash((self.ref.name, self.build))`（requires.py:241），而 wp/1.48 的
wayland 是 build context 节点上的**普通 requires**（build=False），本配方
能声明的只有 `tool_requires(..., override=True)`（build=True）——键不同，
`transitive_deps` 里查不到，override 静默不生效（图报错原样）。override
只能跨同类需求：build 覆 build、host 覆 host。

可行的化解只有两条：

1. **不把 wp/1.48 放进本 graph**（采用）：本配方 tool_requires
   `wayland-protocols/1.36.1`——与 qtwayland 已带的**同 ref**，去重后
   build context 只剩一个 wp 节点，wayland 全局 1.22.0（pwp 同钉），零
   override、零源码重建，全部吃官方已发布二进制。上游只要
   WaylandProtocols 1.15，1.36.1 覆盖 kwayland 消费的全部 XML
   （stable/xdg-shell、unstable/xdg-shell-v6、relative-pointer、
   pointer-gestures、pointer-constraints、xdg-foreign、idle-inhibit、
   xdg-output、xdg-decoration）。
2. 把 build context 整体抬到 wayland/1.24.0（override wp/1.36.1→1.48 +
   pwp 改钉 1.24.0）：wp/1.36.1 与 pwp 都被拖入源码重建，且会作废刚验证
   完的 pwp 制品与 MR，收益只是"配方里写着 1.48"，不取。

链上 wp/1.48 的角色不受影响：kscreenlocker 6.7.2 等无 qtwayland 的消费者
正常吃 1.48；凡宿主图里带 qtwayland 的消费者（kwayland、kwin），build
context 的 wp 都以 qtwayland 的 1.36.1 为准。

## EGL 为什么不用制品仓 mesa（首轮 G2 图冲突实录）

首轮 conan-verify G2 挂：

```
ERROR: Version conflict: Conflict between expat/2.8.2.1.1 and
expat/2.8.2 in the graph. Conflict originates from mesa/24.3.4.1.1
```

mesa/24.3.4.1.1 钉 expat/2.8.2.1.1（其 .so 带 SONAME 的改版），而
qtbase→dbus→expat/2.8.2、qtbase→wayland/1.22.0→expat/2.8.2（本配方
直连 wayland 也同钉）——两个精确钉版构成图冲突，override 会把
qtbase/dbus/wayland 全部拖入源码重建，不可取。

且实测上游全树无 `EGL_LIBRARIES`/`EGL::EGL` 引用：EGL 只被
`find_package(EGL)` 探测一次，`set_package_properties(... TYPE REQUIRED)`
+ `ecm_feature_summary(FATAL_ON_MISSING_REQUIRED_PACKAGES)` 让探测失败
即 configure 失败——**只需要"找得到"，没有任何目标链接它**。libEGL 属
OHOS 系统图形栈（设备 /system/lib64/libEGL.so 在位，qtbase 的 Qt6Gui
DT_NEEDED 也按系统路径解析）。

故配方不引 mesa，改用 SDK sysroot 的 EGL：

- `EGL_INCLUDE_DIR = <sdk>/sysroot/usr/include`（EGL/egl.h 在位）
- `EGL_LIBRARY = <sdk>/sysroot/usr/lib/aarch64-linux-ohos/libEGL.so`（桩库）

（glob `ohos-sdk_*/` 取可用版本；SDK 资源先例=静态 wayland-scanner 用
SDK 的 libexpat.a。）test_package 同步去掉 mesa——其原注释假设
"libEGL 在 host 图"是错的，运行期由系统库解析。

## WaylandScanner_EXECUTABLE

ECM 的 FindWaylandScanner 在 OHOS 找不到独立 khronos scanner 工具。
优先 qtbase/libexec/wayland-scanner（已验证能在 OHOS 执行的构建），
兜底 wayland/bin/wayland-scanner（libkscreen 先例）。

## wayland-protocols 的 .pc 修复（layer-shell-qt 先例）

tool_requires 无 CMakeDeps config，ECM FindWaylandProtocols 走
pkg-config；wp 包自带的 wayland-protocols.pc 里 prefix 是缓存期旧路径，
故 generate() 里按真实包前缀重生成 .pc 放 `build_folder/pkgconfig-fixed`
并置顶 PKG_CONFIG_PATH（Environment scope=build 存脚本
conanbuild_wp_pkgconfig），再显式给 WaylandProtocols_DATADIR 缓存变量
（src/client/CMakeLists.txt 用 `${WaylandProtocols_DATADIR}` 引用
xdg-shell 等 XML）。

## 上游测试：只有构建、没有 ctest 注册

实测 tests/CMakeLists.txt：只 `add_executable` 11 个客户端测试
（copyClient/pasteClient/touchClientTest/panelTest/qtwayland-integration-
test/subsurface-test/shadowTest/dpmsTest/plasmasurface-test/xdgforeign-
test/xdg-test），**没有任何 add_test**；它们运行时依赖的
org-kde-kf5-kwayland-testserver 在 KF6 服务端拆分后移出了本仓库。
所以 build() 不做 ctest（`ctest --no-tests=error` 反而会挂），
BUILD_TESTING=ON 保证 12 个测试可执行文件（11 + kwaylandScanner）
全部真实编译通过；运行时验证改由 test_package 的 E2E 往返承担
（见 test_package/MANIFEST.yml）。

## 其余 OHOS 适配（全有合并先例）

- KF_IGNORE_PLATFORM_CHECK=TRUE：绕过 KDE 平台检测。
- CMAKE_SHARED_LIBRARY_SONAME_*_FLAG：OHOS 无 Platform/HarmonyOS cmake
  模块，共享库会没有 DT_SONAME（kdecoration/layer-shell-qt 先例）。
  0003 去版本后两者合起来的效果 = 单一无版本实体文件 + SONAME=裸名。
- ECM_MODULE_PATH 手设：CMakeDeps 生成的 ECMConfig 不传变量
  （libkscreen 先例）。
- conan_cmakedeps_paths.cmake 手写：qtbase cmake_find_mode=none 不进
  CMAKE_PREFIX_PATH，逐依赖 PREPEND lib/cmake + CMAKE_FIND_PACKAGE_PREFER
  _CONFIG ON + Qt6_DIR 钉 qtbase、跳过旧 qtbase/6.11.1（libkscreen 全套）。
- PlasmaWaylandProtocols 是 cmake_find_mode=none 包：上游
  PlasmaWaylandProtocolsConfig.cmake 放在 pwp/share/cmake，generate()
  把该目录 PREPEND 进 CMAKE_PREFIX_PATH 并显式给
  PLASMA_WAYLAND_PROTOCOLS_DIR（双保险）。
- Qt6LinguistTools：**kwayland 不需要**（全树 `find_package(Qt6 ...)` 只取
  Gui/Concurrent/WaylandClient ± Private；无 ki18n、无 po/）。libkscreen /
  kscreenlocker 钉它是为了 ECMPoQmTools 的 po→qm 步骤，本包无此步骤，故
  配方里不声明 qt6linguisttools tool_require，也不查它的
  Qt6LinguistTools_DIR。注意 `self.dependencies[.build].get(名字)` 不是
  dict.get：依赖不在集合里会直接抛 `KeyError: 'xxx' not found in the
  dependency set`（dependencies.py:58），只看不查的依赖不要写探测代码。

## test_package 的两处修正（第七、八轮 G2 实录）

补丁 0003 之后第七轮 G2 越过了主构建与打包（`kwayland/6.7.2@ohpcd/stable`
在缓存里 `Already installed`、12 个测试可执行文件全产出），只在
test_package 的 configure 挂：

```
CMake Error at CMakeLists.txt:20 (target_link_libraries):
  Target "mini_compositor" links to:
    wayland::wayland
  but the target was not found.
```

根因是解析路径，不是缺依赖：test_package 的 generate() 只用
CMakeToolchain（qtbase/kwayland 是 cmake_find_mode=none，本来也不用
CMakeDeps），generators 目录里没有 CMakeDeps 的 `wayland-config.cmake`，
所以 `find_package(wayland)` 必然落到模块模式——命中 Qt6 自带的 ECM
组件式模块 `.../Qt6/3rdparty/extra-cmake-modules/find-modules/
Findwayland.cmake`（Qt6Config 把该目录加进 CMAKE_MODULE_PATH；模块里
`find_package_handle_standard_args` 还给出包名大小写不一致的开发者
警告）。该模块提供的是 `Wayland::Client` / `Wayland::Server` /
`Wayland::Cursor` / `Wayland::Egl` 四个导入目标，**没有** CMakeDeps
风格的 `wayland::wayland` 全局目标——那个名字只在主配方构建（有
CMakeDeps + CMAKE_FIND_PACKAGE_PREFER_CONFIG）里成立。

修正：test_package 用模块的包名与组件写法
`find_package(Wayland REQUIRED COMPONENTS Client Server)`，链接
`Wayland::Client Wayland::Server`。模块经 pkg-config 定位到 conan
wayland/1.22.0 包（conanbuild 的 PKG_CONFIG_PATH），库路径/头文件都由
目标携带；运行时一侧仍由 test() 里 LD_LIBRARY_PATH 全量依赖 lib 目录
解析。

修正后第八轮 test_package configure/编译/链接全绿（mini_compositor +
client_roundtrip 都产出），挂在 test()，是 Conan API 用法错误：

```
ERROR: kwayland/6.7.2@ohpcd/stable (test package): Error in test() method, line 63
    self.run(os.path.join(self.build_folder, "client_roundtrip"), env=env)
    AttributeError: 'str' object has no attribute '_values'
```

`ConanFile.run(env=...)`（conan 2.29 真机源码签名）只接受**环境文件名**
（字符串，或字符串列表），不是 `Environment` 对象：

```python
def run(self, command, stdout=None, cwd=None, ignore_errors=False, env="", quiet=False,
        shell=True, scope="build", stderr=None):
    env = [env] if env and isinstance(env, str) else (env or [])
    assert isinstance(env, list), "env argument to ConanFile.run() should be a list"
```

test_package 自带 VirtualRunEnv，`conanrun` 环境文件里 host 图全部依赖
（kwayland/qtbase/qtwayland/wayland/expat/libxml2/dbus/... 共 16 个 lib
目录）的 LD_LIBRARY_PATH 已就位，故 test() 直接
`self.run('QT_QPA_PLATFORM=offscreen "<exe>"', env="conanrun")`：平台变量
内联在命令行（QCoreApplication 本不需要平台插件，offscreen 只作兜底），
不再自建 Environment。

## 迷你合成器的连接接入方式（第九轮 G2 实录）

`env` 修好之后第九轮一路跑到 test() 执行体，客户端进程退出码 1，日志里
服务端刷屏：

```
failed to accept: Invalid argument
failed to accept: Invalid argument
...
ERROR: kwayland/6.7.2@ohpcd/stable (test package): Error in test() method, line 59
	self.run('QT_QPA_PLATFORM=offscreen "%s"' % exe, env="conanrun")
	ConanException: Error 1 while executing
```

根因是服务端把 socketpair 端点交给了 `wl_display_add_socket_fd`：该接口
要的是**监听** socket（它会在事件循环里 accept() 新连接），socketpair
端点已经"连上"了，accept() 每次返回 EINVAL → 事件循环空转刷屏，客户端
对象根本建不出来，registry 一个 global 都公告不出去，客户端 5s 超时
依次挂掉。

对已连接的 fd，正确接口是 `wl_client_create(display, fd)`（socket
activation / 嵌入式同款）：它直接把 fd 变成 wl_client 挂进 display 的
事件循环，fd 所有权一并转移。改后 socketpair 两端：服务端 `sv[0]` 交
`wl_client_create`，客户端 `sv[1]` 仍经 `ConnectionThread::setSocketFd`
交给 KWaylandClient。

## 验证方式

- 真机 `conan create`：全量构建 + 12 个上游测试可执行文件编译通过。
- `conan test`：test_package E2E 往返（进程内迷你合成器 +
  KWaylandClient 全链路），断言 create_surface 到达服务端且计数 == 1。
