# pidgin — OpenHarmony PC 适配

## 软件信息
- **名称**：pidgin
- **版本**：2.14.14
- **官网**：https://pidgin.im/
- **许可证**：GPL-2.0-or-later
- **类别**：network（即时通讯）
- **构建系统**：autotools

## 适配范围
本归档仅包含 **libpurple 核心库**（静态库），不包含 GTK 桌面 UI 或 finch ncurses UI。

### 为什么只编译 libpurple？
- pidgin 的 GTK UI 依赖 X11/Wayland，OpenHarmony PC 用 ArkUI
- libpurple 是 GLib 库，跨平台兼容性最好
- finch ncurses UI 在 OH 上可运行但需要额外工作
- 大多数 OH 应用只需要 libpurple 的协议/账号抽象能力

## 编译验证
| 项目 | 结果 |
|------|------|
| libpurple.a | 7.2 MB ARM64 静态库 ✅ |
| test_pidgin | 37.6 MB ARM64 可执行 ✅ |
| qemu-aarch64 运行 | ✅ 通过 |
| libpurple 版本 | 2.14.14 |
| 协议插件数 | 0（仅核心） |

## 使用方式
```bash
# 编译产物在根目录
file libpurple.a        # ELF 64-bit LSB relocatable, ARM aarch64
file test_pidgin            # ELF 64-bit LSB executable, ARM aarch64, dynamically linked

# 链接 libpurple.a
aarch64-linux-gnu-gcc --sysroot=<OHOS_sysroot> \
    your_app.c -L. -lpurple -lglib-2.0 -lgobject-2.0 \
    -o your_app_arm64
```

## 依赖
- glib-2.0 >= 2.16.0
- libxml2
- 静态链接（默认）

## 不包含
- GTK UI (--disable-gtkui)
- Finch ncurses UI (--disable-finch)
- 协议插件 (IRC/Jabber/GG) — 需要单独编译 prpl/

## 版本历史
- **2.14.14** (2026-07-21): 首次 OH 适配成功，libpurple 核心编译 + qemu 验证通过

## 后续工作
- 编译 prpl 协议插件
- 编译 finch
- 真机测试
