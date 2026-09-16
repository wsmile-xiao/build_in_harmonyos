# wayneko

**wayneko** 把一只会动的 Neko 猫画在 Wayland 合成器输出（屏幕）的底部。它是一个
使用 `zwlr-layer-shell-unstable-v1` 协议的 Wayland 客户端（layer-shell），猫会在
深夜打瞌睡、被指针靠近时惊醒并沿屏幕边缘奔跑。

- 上游仓库：<https://git.sr.ht/~leon_plickat/wayneko>
- 许可证：GPL-3.0-or-later
- 构建系统：纯 GNU Makefile（无 configure、无 CMake/Meson）

## 功能概述

- 基于 `zwlr-layer-shell-unstable-v1` 在指定 layer（background/bottom/top/overlay）绘制动画
- neko / inu 两种角色（`--type neko|inu|random`）
- 可配置背景色 / 描边色（`--background-colour`、`--outline-colour`，`0xRRGGBB[AA]`）
- 可配置空闲睡眠时间与“困倦度”（`--idle-sleep`、`--sleepiness`、`--sleepiness-night`）
- 指针跟随（`--follow-pointer`）与表面关闭后重建（`--survive-close`）
- 附带 `wayneko.1` man 手册与 bash / zsh 补全

## 依赖

- **运行/编译依赖**：`wayland/1.22.0.1`（libwayland-client）、`pixman/0.46.4.3`
- **构建期工具**：`wayland-scanner`（recipe 内从 wayland 1.22.0 源码静态编译，见下）

## HarmonyOS PC 适配要点

1. **wayland-scanner 执行问题（关键）**：`wayland/1.22.0.1` 包内的
   `bin/wayland-scanner` 在 OHOS 上执行报 `Operation not permitted`（HMDFS/签名限制，
   从 Conan 缓存取出的二进制不可执行）。沿用仓库内已验证先例
   (`archives/w/wayland-protocols/1.36.1`)，在 `build()` 内从 wayland 1.22.0 源码
   编译一个**静态链接**（仅依赖 libc）的 `wayland-scanner`，再用它生成
   three 个协议绑定。Device 上已验证该静态 scanner 可执行
   （`wayland-scanner 1.22.0`，exit 0）。
2. **不依赖 pkg-config**：上游 Makefile 用 `pkg-config` 取 pixman 编译/链接参数；
   recipe 直接以 Conan 依赖解析出的 package 路径构造 `CC/CFLAGS/LIBS`
   （R33：不裸用 `${CC}` 等 shell 变量）。
3. **RPATH**：安装后的可执行文件内嵌指向 wayland/pixman `lib/` 的 RPATH，使其在
   `conanrun` 环境之外也能直接运行（CI L2 冒烟测试即直接执行 `--help`）。
4. **无头限制**：wayneko 需要实现了 `zwlr-layer-shell-unstable-v1` 的合成器才能
   真正绘制；CI 与单元测试只校验 CLI 行为/动画状态机/颜色解析，无法验证实际画面。

## 上游测试

上游**没有任何测试**：无 `tests/` 目录、无 `check`/`test` make 目标、无 CI 配置。
本仓库**补充**了两层真实测试（见版本级 `test_package/MANIFEST.yml`）：

- 层 1（`build()` 内）：`tests/test_wayneko.c` 直接编译真实的 `wayneko.c`
  （重命名入口 `main`→`wayneko_cli_main`），对真实函数做 117 条断言。
- 层 2（`test_package/`）：执行**已安装**的二进制并断言真实退出码/错误文本（23 条断言）。

## 参考资料

- 上游源码：<https://git.sr.ht/~leon_plickat/wayneko>
- 本仓库内先例：`archives/w/wayland-protocols/1.36.1/conanfile.py`（静态 scanner）、
  `archives/w/wayland/1.22.0.1/conanfile.py`（依赖 .pc/环境修正）
