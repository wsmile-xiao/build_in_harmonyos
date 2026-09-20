# libahp-gt 1.7.3 — HarmonyOS PC 适配说明

## 概况

libahp-gt 用于驱动 AHP GT（兼容 Skywatcher）步进控制器：串口/UDP 通信、步进配置、
goto/跟踪、RA-Dec 与 Alt-Az 互转，以及 SynScan 兼容服务端。

- 上游：https://github.com/iliaplatone/libahp-gt （源码来源为 Debian orig tarball）
- 构建：CMake（单个 `ahp_gt.c` + `ahp_gt.h.cmake` 生成的头）
- 依赖：无（仅 libm/pthread）
- 许可证：MIT

## 适配要点

| # | 问题 | 处理 |
|---|------|------|
| 1 | `cmake_minimum_required(2.6)` | 新 CMake（3.27+）拒绝 3.5 以下的最小版本要求 → 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（`libftdi` 同法） |
| 2 | **clang 15 下 `-Wreturn-type` 默认是错误** | 上游 `ahp_gt.c` 有几十处 `int`/`double` 函数用裸 `return;` 做守卫（gcc 只警告，clang 15 在 C 里直接报错，构建中断）→ 用 `-Wno-error=return-type` 降级为警告，**不改上游任何源码**；受影响函数都只在有控制器时才有效 |
| 3 | `execute_process(doxygen ...)` | 沙箱无 doxygen：该调用未检查返回值，配置继续；生成头 `ahp_gt.h` 来自 `ahp_gt.h.cmake`，按上游布局安装到 `include/ahp/` |
| 4 | 硬件依赖 | 多数 getter/setter 由 `ahp_gt_is_detected()` 守卫，无硬件时为空操作 → 消费者测试只覆盖无硬件时定义良好的 API |

## 测试

上游无测试套件（库通过串口驱动控制器）。`test_package/test_ahp_gt.c` 针对**安装后**的
头文件/库做 10 条断言，全部无需硬件：

- `ahp_gt_get_version() == 0x173`（版本宏为十进制拼接：1.7.3 → 0x173）
- `ahp_set_debug_level`/`ahp_get_debug_level` 往返与复位
- `ahp_set_app_name`/`ahp_get_app_name` 往返
- `ahp_gt_set_axes_limit`/`ahp_gt_get_axes_limit` 往返（未受守卫）
- `ahp_gt_get_current_device() >= 0`
- 默认未连接：`ahp_gt_is_connected() == 0`、`ahp_gt_get_fd() == -1`、`ahp_gt_is_detected(0) == 0`
- 未连接时 `ahp_gt_disconnect()` 安全

## 已知限制

- 硬件相关路径（连接、检测、goto/跟踪、RA-Dec 转换）在无控制器时无法验证；上游这些函数
  在未检测到设备时按设计提前返回。
- 未修改上游源码与测试（无 `patches/`）。
