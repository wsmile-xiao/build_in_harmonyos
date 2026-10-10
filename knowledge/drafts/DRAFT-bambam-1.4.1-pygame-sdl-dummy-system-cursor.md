# DRAFT-bambam-1.4.1-pygame-sdl-dummy-system-cursor — SDL dummy 无系统光标：pygame 应用 boot 冒烟判据

> **Contributor**: bambam-1.4.1 | **Status**: DRAFT | **Updated**: 2026-10-04
> **Severity**: medium | **Category**: python / pygame / sdl / dummy / headless / test_package
> **Audience**: 所有在无头 OHOS CI（SDL_VIDEODRIVER=dummy）上做 test_package 冒烟验证的 pygame/SDL2 应用

## 问题（真实首错）

bambam/1.4.1 在 `SDL_VIDEODRIVER=dummy` 下做 boot 冒烟（`pygame.mouse.set_cursor(
pygame.SYSTEM_CURSOR_HAND)`）实测报错：

```
pygame.error: Error while creating system cursor
  File ".../pygame/cursors.py", line 139, in set_cursor
    pygame.mouse._set_cursor(**{cursor.type: cursor.data})
```

SDL dummy 视频驱动不提供 system cursor 实现。pygame 2.6.1（OHOS arm64）确认复现。

## 根因

`SDL_VIDEODRIVER=dummy` 是无显示/无头环境的软件回退驱动，仅提供最小 framebuffer，
不实现 `SDL_CreateSystemCursor`。任何在启动路径调用
`pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_HAND)` 的 pygame 应用在 dummy 下
都会在此处异常退出——若 test_package 的 boot 冒烟要求"进程自然存活/干净退出"，
会误判为适配失败（实际核心 boot 已成功）。

## 解决方案

boot 冒烟正确判据（bambam test_bambam_ohos.py 落地）：
1. 短超时（如 8s）运行 `bin/bambam`（SDL dummy 环境），进程存活到超时
   （已进入事件循环 `poll_for_any_key_press`）→ **PASS**；
2. 若进程仅因 SDL dummy 无系统光标（stderr 含 "Error while creating system
   cursor"/"set_cursor"）提前退出 → 视为核心 boot（pygame.init / set_mode /
   资源加载）已成功的**已知 dummy 限制**，如实上报、不算失败；
3. 其他异常提前退出 → FAIL。
并输出可审计的 `HMBS_TEST_PACKAGE_RESULT=<json>`。

补充：`bin/bambam --help` 在 `pygame.init()` 之前由 argparse 解析并退出 0，
是无显示环境下最稳的 CLI 实质验证。

## 验证

- bambam/1.4.1：SDL dummy 下进程存活到 8s 超时（event loop reached）→ boot
  smoke PASS；直接 `set_cursor` 单独复现 dummy 报错；conan create exit 0。
- 相关条目：E472（SDL dummy headless 测试签名）、E483（dummy 软件渲染回退）
  覆盖 dummy 驱动一般能力，本条专指 pygame.mouse 系统光标限制。

## 适用边界

- ✅ 适用：pygame/SDL2 应用在 SDL dummy（无头 CI）下的 test_package boot 冒烟。
- ❌ 不适用：有真实显示服务器（X11/Wayland 设备端）的场景，set_cursor 正常。
