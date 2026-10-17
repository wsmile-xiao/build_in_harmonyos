# plasma-wayland-protocols 1.21.0 适配笔记

## 为什么是 1.21.0（R37）

kwin 6.7.2 / kwayland 6.7.2 硬性要求：

```cmake
find_package(PlasmaWaylandProtocols 1.21)
```

ohpcd 制品仓此前没有 plasma-wayland-protocols 包——libkscreen 6.7.2
的配方是携带 1.21 tarball 作第二源、注入 `PLASMA_WAYLAND_PROTOCOLS_DIR`
绕过 find_package。本配方把 pwp 做成一等包,让 kwin 依赖链直接从制品仓消费:

```
wayland-protocols 1.48 → plasma-wayland-protocols 1.21.0
                       → kwayland 6.7.2 → kwin 6.7.2
```

## 上游构建结构

- CMake ≥ 3.16,`find_package(ECM 5.69.0 NO_MODULE)`,纯数据包:安装 30 个
  协议 XML 到 `${KDE_INSTALL_DATADIR}/plasma-wayland-protocols`,外加 2 个
  向后兼容改名文件(`zkde-screencast-unstable-v1.xml` → `screencast.xml`、
  `org-kde-plasma-virtual-desktop.xml` → `plasma-virtual-desktop.xml`),
  共 **32 个 XML**。
- 同时安装 `PlasmaWaylandProtocolsConfig.cmake` / ConfigVersion.cmake 到
  `share/cmake/PlasmaWaylandProtocols/`;Config 内容仅设置
  `PLASMA_WAYLAND_PROTOCOLS_DIR`(PATH_VARS 相对计算,可重定位)。
- `BUILD_TESTING=ON` 时:`find_package(WaylandScanner REQUIRED)` +
  `find_package(Wayland COMPONENTS Client REQUIRED)` + autotests。
  autotests 对 src/protocols/*.xml 逐协议注册 **4 项测试**(共 30 协议):

  1. `wayland-scanner --strict client-header` → `<proto>-client-protocol.h`
  2. `wayland-scanner --strict client-header` → `<proto>-server-protocol.h`
     (上游以 client-header 传参生成服务端头,保留原样)
  3. `wayland-scanner --strict private-code` → `<proto>-protocol.c`
  4. `${CMAKE_C_COMPILER} build-<proto>.c <proto>-protocol.c
     -I ${Wayland_INCLUDE_DIRS} -Wl,--unresolved-symbols=ignore-all`
     (build.c 仅 include 两个头 + 空 main,验证生成代码可编译)

  1–3 为 FIXTURES_SETUP、4 为 FIXTURES_REQUIRED;1–3 设
  `FAIL_REGULAR_EXPRESSION ".+"`(scanner 输出任何告警即失败),
  仅 `plasma-window-management` 豁免(上游已知既有问题)。
  合计 **120 项上游测试**。

## OHOS 适配决策

1. **wayland 钉 1.22.0,不用 1.24.0**——qtbase/6.11.1.x 与
   qtwayland/6.11.1 都钉 wayland/1.22.0,混用触发版本图冲突
   (libkscreen 6.7.2 配方已实证并记录)。pwp 的
   `find_package(Wayland COMPONENTS Client)` 无最低版本要求,1.22.0 满足;
   kwin 链后续包(kwayland 等)经 qtwayland 也锚在 1.22.0,整链一致。
2. **静态 wayland-scanner**(wayland-protocols 1.47/1.48 同款机制):
   HMDFS 禁止从 Conan 缓存动态加载共享库,`wayland` 包自带的 scanner
   (链接 libexpat.so/libxml2.so)在本平台无法执行。故从 wayland 1.24.0
   源码编译 `-static` scanner(仅依赖 libc,静态链接 SDK 的
   `libexpat.a`,路径 `/data/service/hnp/expat.org/expat_2.7.3/lib/`),
   并把 `WaylandScanner_EXECUTABLE` 钉到该二进制——scanner 在
   `build()` 内先于 `cmake.configure()` 编译,configure 时文件已存在
   (ECM FindWaylandScanner 经 pkg-config 找不到 wayland-scanner.pc,
   钉住可执行文件后 `Wayland::Scanner` 目标成立,libkscreen 先例)。
3. **测试在 build() 内直跑**(kdecoration 6.7.2 先例):
   `BUILD_TESTING=ON` + configure/build 后 `ctest` 直跑 120 项。
   scan 测试执行静态 scanner(--strict),build 测试执行
   `${CMAKE_C_COMPILER}`(与 conan 构建同一编译器),均无共享库加载需求。
4. **find_package(Wayland) 走 CMakeDeps config**:
   `CMAKE_FIND_PACKAGE_PREFER_CONFIG ON` + 手工
   `conan_cmakedeps_paths.cmake`(把 wayland 的 lib/cmake 加进
   CMAKE_PREFIX_PATH)——CMakeDeps 生成的 WaylandConfig.cmake 提供
   autotests 需要的 `Wayland_INCLUDE_DIRS` 变量
   (layer-shell-qt 先例;ECM 的 FindWayland 模块走 pkg-config,
   而 wayland-scanner.pc/wayland-client.pc 不在搜索路径)。
5. **KF_IGNORE_PLATFORM_CHECK=TRUE**——OHOS 不在 KDE 平台清单
   (libkscreen/kdecoration 先例)。**ECM_MODULE_PATH 手工设置**——
   CMakeDeps 生成的 ECMConfig.cmake 不传播该变量
   (libkscreen 先例),KDEInstallDirs/KDECMakeSettings/ECMSetupVersion
   依赖它。
6. **package_info 用 cmake_find_mode=none**——上游自带
   PlasmaWaylandProtocolsConfig.cmake(无 find_dependency,内容极简),
   不遮蔽(kdecoration/libkscreen 先例);消费者(kwayland 6.7.2 配方)
   把 `share/cmake/PlasmaWaylandProtocols` 加进 CMAKE_PREFIX_PATH 即可。

无 patch(patches: {})。pwp 不引用 wayland-protocols 的 XML
(src/protocols/*.xml 无 `<import>`),无需 wayland-protocols 依赖。

## 真机验证记录(2026-10-02)

conan-verify 八门禁 Verdict PASS(reports/conan-verify-report.md,
2026-10-02T18:00:33):G0/G1/G2/G3/G4 全 PASS,L2/L4/L5 无 cache
路径跳过。

- **上游测试 120/120**:`BUILD_TESTING=ON` + configure/build 后
  build() 内 ctest 直跑(`--output-on-failure --no-tests=error
  --timeout 90`),`100% tests passed, 0 tests failed out of 120`,
  Total Test time 10.33s;静态 wayland-scanner 注入使 scan 类测试
  可在平台执行,逐项明细 reports/conan-create.log。
- **test_package 7 组断言全过**:CMake 消费者
  `find_package(PlasmaWaylandProtocols 1.21 CONFIG REQUIRED)` 解析
  + `PLASMA_WAYLAND_PROTOCOLS_DIR` 有效性 + 32 XML + 5 代表性文件
  (configure 阶段 `pwp consumer check PASS: 32 XMLs`),shell 深检
  `[ok] pwp 产物完整: 32 XML(plasma_window_management 等 30 协议
  + 2 兼容改名,内容一致)`。

### G1 首轮修正

首轮 G1 报 `conanfile.py 缺少: 补丁应用调用`——本包零补丁
(conandata `patches: {}`),但统一配方口径要求保留标准补丁链调用,
已在 source() 补 `apply_conandata_patches(self)`(零补丁时为空操作)
并补 import,修正后 G1 PASS。package_type 定为 `"unknown"`(纯 XML
数据包无编译产物,免 shared 选项校验;wayland-protocols 1.48 先例)。

### 真机下载链路

设备无外网:验证时设备副本的 conandata.yml 临时换用本地
http.server 镜像 URL(同一 tarball 字节,sha256 与官方一致:
plasma-wayland-protocols-1.21.0.tar.xz `698a7b28…`,
wayland-1.24.0.tar.gz `78008588…`),验证后恢复官方 URL——
该临时改法不进入提交。
