# kidletime 6.26.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-23
- 编译器: clang/clang++ (OHOS arm64 交叉工具链)
- 状态: built

## 编译步骤

```bash
# Conan 配方验证（此前会话已完成 G0-G4 PASS）
conan create --profile=ohos-aarch64 -tf test_package  # 见 reports/conan-create.log

# 关键 CMake 配置（generate() 注入）
#  - KF_IGNORE_PLATFORM_CHECK=TRUE   ：OHOS 不在 KDE 平台白名单，跳过平台检测
#  - WITH_X11=OFF / WITH_WAYLAND=OFF ：制品仓无 x11/xcb 与 PlasmaWaylandProtocols，禁用后端
#  - CMAKE_CXX_STANDARD=20 + -std=c++20 ：KF6 代码生成头需要 C++20
#  - ECM_MODULE_PATH 手动设置：CMakeDeps 生成的 ECMConfig.cmake 不透传该变量
#  - conan_cmakedeps_paths.cmake 手动创建：qtbase cmake_find_mode=none，
#    需把 qtbase lib/cmake 加入 CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH
#  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG=-Wl,-soname, ：CMake 无 Platform/HarmonyOS
#    模块，手动补齐 soname 标志以满足 L5 SONAME 质量门禁
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 不识别 OHOS 平台 (E092) | CMake 无 Platform/HarmonyOS 模块 | KF_IGNORE_PLATFORM_CHECK=TRUE 绕过平台检测 |
| 2 | 无 x11/xcb/Wayland 依赖 | OHOS 制品仓无这些组件 | WITH_X11=OFF、WITH_WAYLAND=OFF，核心库仅依赖 Qt6Core/Qt6Gui |
| 3 | ECM_MODULE_PATH 丢失 | CMakeDeps 生成的 ECMConfig.cmake 不透传 | generate() 中手动设置 ECM_MODULE_PATH |
| 4 | qtbase 的 cmake 目录未进 CMAKE_PREFIX_PATH | qtbase cmake_find_mode=none | 手动生成 conan_cmakedeps_paths.cmake |
| 5 | 运行时无 poller 后端 | 未打包 X11/Wayland poller 插件 | test_package 按 R40 降级处理：只验证 API/链接可用性 |

## 源码修改

无补丁（patches/ 为空）。全部适配通过 conanfile.py generate() CMake 变量注入完成。

## 依赖版本

- qtbase/6.11.1（已发布到 ohpcd ✅）
- ecm/6.26.0（tool_requires，已发布到 ohpcd ✅）

## 验证结果

```bash
# conan create 成功（test_package 实质调用 KIdleTime API）
kidletime test_package: PASS
# 输出: KIdleTime 6.26.0: instance OK, poller-backend=ABSENT, idleTime()=0 msec
# 说明: OHOS 无 poller 插件属预期（WITH_X11/WAYLAND=OFF），PASS 覆盖链接/API 可用性（R40）
```

## 测试统计（R51 如实申报）

| 测试类型 | 适配后用例数 | 说明 |
|----------|-------------|------|
| 单元测试 | 0 | 上游无测试套件（N=0） |
| 集成测试 | 0 | - |
| 鸿蒙特有测试 | 1 | 消费者测试 test_package（R34 实质 API 调用：KIdleTime::instance() + addIdleTimeout() + idleTime()） |
| **合计** | **1** | 新增测试通过率 1/1 (100%) |

- 上游测试 N=0（实测，上游仅库代码无测试框架）
- 适配后按 rule8 补增消费者测试 M=1（test_package，R34 实质调用被测包 API）
- 运行测试：通过 1，失败 0，跳过 0（test_package 在 conan create 内实际执行并 PASS）

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | OHOS 适配配方 |
| conandata.yml | 官方源码 + sha256 |
| test_package/ | 消费者测试（R34 实质 API 调用） |

## 注意事项

- kidletime 是纯库包（libKF6IdleTime.so），无命令行工具，无需 commands.json（R38 不适用）
- 系统无同名库，动态链接由 Conan 管理（R26 不适用）
- `if self.settings.os in ("Linux", "OHOS")` 符合 R32 要求
---

**编译结束**: 2026-09-24 00:50
**最终状态**: built
