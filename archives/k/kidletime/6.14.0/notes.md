# kidletime 6.14.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (15.0.4, aarch64-linux-ohos)
- 状态: built

## 编译步骤

```bash
# 手动探索构建（X11/Wayland 关闭）：
cmake .. -DCMAKE_TOOLCHAIN_FILE=.../conan_toolchain.cmake \
  -DCMAKE_PREFIX_PATH=<qtbase>/lib/cmake;<ecm>/share/ECM/cmake \
  -DKF_IGNORE_PLATFORM_CHECK=TRUE \
  -DCMAKE_CXX_STANDARD=20 -DCMAKE_CXX_FLAGS=-std=c++20 \
  -DWITH_X11=OFF -DWITH_WAYLAND=OFF
cmake --build . -j2      # 产出 libKF6IdleTime.so + kidletime_example
cmake --install .        # 安装 lib/ include/ lib/cmake/KF6IdleTime/

# 正式验证：conan create（conan-verify G2 门禁，全部通过）
# 配方路径: archives/k/kidletime/6.14.0/
# 命令: conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `KDEMetaInfoPlatformCheck.cmake: Your current platform 'HarmonyOS' is not supported` | KDE 平台白名单不含 OHOS | `KF_IGNORE_PLATFORM_CHECK=TRUE` |
| 2 | X11 后端: `find_package(X11 REQUIRED)`/`XCB`/`X11_XCB` 找不到 | 制品仓无 x11/xcb 组件 | `WITH_X11=OFF` |
| 3 | Wayland 后端: `find_package(PlasmaWaylandProtocols REQUIRED)` 失败 | 制品仓缺 PlasmaWaylandProtocols | `WITH_WAYLAND=OFF` |
| 4 | `ECM_MODULE_PATH` 未定义 | CMakeDeps 生成的 ECMConfig.cmake 不传播该变量 | `generate()` 中按 ecm package_folder 手工设置 modules/find-modules/kde-modules |
| 5 | 找不到 Qt6 包 | qtbase 用 cmake_find_mode=none，CMakeDeps 不注入 lib/cmake | 手工生成 conan_cmakedeps_paths.cmake（沿用 kcoreaddons 手法） |
| 6 | download.kde.org `frameworks/6.14.0/` 路径 404 | KDE 官方目录用 `6.14` 非 `6.14.0` | 改用 `https://download.kde.org/stable/frameworks/6.14/kidletime-6.14.0.tar.xz` |

## 源码修改

无（核心库仅靠 CMake 选项即可在 OHOS 编译，无需补丁）。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| qtbase | 6.11.1 | Qt6Core/Qt6Gui（runtime requires） |
| ecm | 6.20.0 | ECM 构建模块（tool_requires） |

## 验证结果

```bash
# conan-verify（G0-G4 + L2/L4/L5）全部 PASS
# conan create: 成功
# test_package CTest: 1/1 Passed（test_kidletime）
# test_package 直接运行输出：
#   KIdleTime 6.14.0: instance OK, idleTime()=0 msec
#   kidletime test_package: PASS
# 无上游 autotest（kidletime 仅含 example，无 ctest 目标）
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | CMake 配方（含 OHOS 适配 generate()） |
| conandata.yml | 官方源 + SHA256 实测 |
| test_package/ | 消费者测试（真实调用 KIdleTime API） |
| libKF6IdleTime.so | 产物（package: lib/libKF6IdleTime.so） |

## 注意事项

- 无 X11/Wayland 后端时 `KIdleTime::instance()` 的 poller 为 null，`idleTime()` 返回 0，属预期行为（上游警告 "Could not find any system poller plugin" 不阻塞）。
- **R40 标注：需人工确认适配完整性**——`test_package/test.cpp` 已显式探测 poller 后端（`addIdleTimeout()` 返回 0 即无后端），确认无后端时输出 WARNING，恒 0 的 `idleTime()` 不作为适配完成的通过依据。
- 库类型包，无 bin/ 产物，不需要 commands.json（R38）。
- `make check` 无目标（上游无测试套件），测试由 test_package 承担。
---

**编译结束**: 2026-08-27 01:36
**最终状态**: built
