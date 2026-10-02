# plasma-wayland-protocols 1.20.0 适配笔记

## 编译环境
- 构建系统: CMake (>=3.16) + ECM (extra-cmake-modules)
- 上游版本: 1.20.0（2026-01-13 发布，Plasma 6.6 前置）
- 编译日期: 2026-09-28
- 编译器: clang 15.0.4 (aarch64-unknown-linux-ohos)（纯数据包，无编译产物）
- 状态: built

## 编译步骤

```bash
cmake --preset conan-release -DBUILD_TESTING=OFF
cmake --build --preset conan-release
cmake --install build/Release
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(ECM) 失败风险 | ECM 是上游 REQUIRED 构建依赖（KDEInstallDirs/KDECMakeSettings/ECMSetupVersion 宏来源） | requirements() 声明 extra-cmake-modules/6.29.0（制品仓已有） |
| 2 | ECM KDEMetaInfoPlatformCheck 不认 HarmonyOS | ECM 平台白名单无 OHOS | `KF_IGNORE_PLATFORM_CHECK=true`（bluez-qt/6.28.0 先例） |
| 3 | ECM 打包产物缺 ECMVersionHeader.h.in | ecm_setup_version 的 configure_file 需要 | generate() 中 if-not-exists 生成缺失模板（bluez-qt 同款） |
| 4 | 上游 autotests 无法运行 | BUILD_TESTING 需 WaylandScanner + Wayland Client；制品仓 wayland 包 scanner 二进制动态链 libexpat.so/libxml2.so，HMDFS 禁止动态加载共享库无法执行 | conanfile.py 从 wayland 1.22.0 源码静态编译 scanner（仅依赖 libc.so，wayland-protocols/1.36.1 已验证方案）随包发布 bin/，test_package 对 30 个 XML × 3 模式 --strict 扫描实跑——90 项上游扫描测试等价覆盖全部通过；仅 30 项 build 测试（需链接 Wayland Client 共享库）平台限制 skipped |
| 5 | 最初按 .pc 断言写测试，test_package 失败 | 上游 1.20.0 实际不安装 pkg-config 文件（实测包产物仅 CMake Config + XML），消费入口是 find_package(PlasmaWaylandProtocols) | 移除 .pc 相关处理与断言，改为校验 Config 包内 PLASMA_WAYLAND_PROTOCOLS_DIR 变量声明 |
| 6 | 首次 conan create CXX 编译器自检失败 `-stdlib=libstdc++` | 默认 profile `compiler.libcxx=libstdc++11`，OHOS clang 15 只提供 libc++ | 用仓库预置 `ci/conan/profiles/ohos-aarch64`（libcxx=libc++）；不在配方内写死 -stdlib（R33） |
| 7 | OHOS 沙箱并行构建失败 | mkfifo jobserver 不支持 | cmake.build -j1（opensp 先例） |

## 源码修改

无补丁。所有 HarmonyOS 特殊处理均在 conanfile.py（工具链变量/模板补全/.pc 修正），上游源码零修改。

## 依赖版本

- extra-cmake-modules/6.29.0（构建期，唯一依赖）

## 上游测试

- autotests/CMakeLists.txt：30 个协议 × 4 项（client-header/server-header/private-code 用 `wayland-scanner --strict`，build 用 C 编译器编译生成代码），共 120 项。
- 平台限制：scanner 二进制动态链 libexpat/libxml2 在 HMDFS 下不可执行；Wayland Client 共享库同样禁动态加载。
- 处置：configure 期禁用 ctest（BUILD_TESTING=OFF）；静态 scanner（wayland 1.22.0 源码编译，仅依赖 libc）随包发布 bin/，test_package 实跑 30 XML × 3 模式 `--strict` 扫描（90/90 通过，plasma-window-management 与上游同口径豁免 strict 告警）+ shell 产物结构断言（14 组）。30 项 build 测试因 Wayland Client 共享库 HMDFS 限制 skipped，MANIFEST.yml 如实声明。
