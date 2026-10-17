# counters 4.1.0 适配记录

## W0/W0b

- 依赖预检未发现 Conan 依赖；语言预检为 C++，构建系统为 CMake。
- 官方源码 tarball SHA-256：`35875780b8f12f39e734ea7c0c89a9457bffa620ff14837701ec019cb33f0824`。
- 项目是 header-only 接口库，CMake 通过 INTERFACE target 安装头文件和 package config。

## 构建与测试

- Conan recipe 打开 `COUNTERS_INSTALL` 和 `COUNTERS_BUILD_TESTS`，运行官方 CTest benchmark smoke test。
- test_package 真实调用 `event_count`、`event_aggregate` 和 `has_performance_counters`，不强制要求设备具备 perf 权限。

## 路径判断

- 当前改动是该库自身的 CMake/Conan 封装；设备 staging 路径误判已留在工作记录，尚未形成新的跨库知识草稿。
---

**编译结束**: 2026-09-03 02:13
**最终状态**: built

## 对话记录

### 对话 #1（2026-09-03）

- 初始框架的绝对 staging 路径判定失败，但 Conan 配方的真实 configure/build/install、上游 CTest smoke test、test_package 和 W3 均通过。
- `test_package` 真实调用 `event_count`、`event_aggregate` 和性能计数器可用性探测；不伪造 perf 权限。
- 该问题属于本库归档封装细节，当前没有抽取新的跨库知识草稿；保留 G0 框架误判日志供审计。

## 结束

最终状态: built
