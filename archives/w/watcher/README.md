# watcher

一个 C++ 文件系统监控库与命令行工具。

## 简介

`wtr.watcher` 是一个实时文件系统事件监控器，支持检测文件/目录的创建、修改、重命名、删除等事件。提供多后端自动适配：

- **fanotify**（Linux ≥ 5.9，需 root/CAP_SYS_ADMIN）— 优先后端
- **inotify**（Linux）— fanotify 不可用时自动 fallback
- **kqueue**（macOS）
- **warthog**（轮询模式，作为最终 fallback）

## 主要功能

- 单头文件 C++ 库（`wtr/watcher.hpp`）— 直接 `#include` 即可使用
- C 语言库（`watcher-c`）— 提供 `wtr_watcher_open/close` C API
- 命令行工具: `wtr.watcher`（完整版）和 `tw`（精简版）
- pkg-config 支持: `watcher.pc`, `watcher-c.pc`
- JSON 格式事件输出，便于程序集成

## 已编译版本

| 版本 | 状态 | 日期 | 补丁数 | 备注 |
|---------|--------|------|--------|-------|
| 0.14.5 | published | 2026-06-01 | 1 | HarmonyOS fanotify 常量补丁 |

## HarmonyOS 适配说明

- **运行时**: 普通用户下 fanotify 不可用（无 CAP_SYS_ADMIN），自动 fallback 到 inotify 适配器，功能完整
- **补丁**: `0001-include-wtr-watcher.hpp.patch` — 为 HarmonyOS 缺失的 Linux 5.9+ fanotify 常量添加 `#ifndef` 保护定义
- **兼容性**: 补丁使用 `#ifndef` 保护，未来内核升级包含这些常量时自动适配，无需修改
- **事件检测**: 实测验证 create/modify/rename/destroy 四种事件类型均正确检测

## 使用示例

```bash
# 监控目录，输出 JSON 事件
wtr.watcher /path/to/dir -s

# 查看版本
wtr.watcher --version
# 输出: 0.14.5

# C++ API
#include <wtr/watcher.hpp>
wtr::watcher::watch("/path", [](wtr::watcher::event ev) {
    std::cout << ev << std::endl;
});
```

## 产物列表

| 产物 | 说明 |
|------|------|
| bin/wtr.watcher | 完整版 CLI 文件监控工具 |
| bin/tw | 精简版 CLI 文件监控工具 |
| lib/libwatcher-c.so | C 共享库 |
| lib/libwatcher-c.a | C 静态库 |
| include/wtr/watcher.hpp | C++ 单头文件库（2429 行） |
| include/wtr/watcher-c.h | C API 头文件（74 行） |
| lib/pkgconfig/watcher.pc | watcher pkg-config |
| lib/pkgconfig/watcher-c.pc | watcher-c pkg-config |