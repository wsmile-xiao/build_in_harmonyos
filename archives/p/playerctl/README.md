# playerctl

## 简介
playerctl 是 MPRIS（Media Player Remote Interfacing Specification）媒体播放器控制器，
通过 D-Bus 与实现 MPRIS 规范的播放器通信。本包包含三部分产物：

- `bin/playerctl` — CLI 控制器（play/pause/metadata/`--follow`/`--format` 等）
- `bin/playerctld` — 守护进程，跟踪并切换到「当前活动」播放器
- `lib/libplayerctl.so` — 公共 C 库（`playerctl/playerctl.h`），消费方可链接

## OHOS 适配（conan，2.4.1）

### 依赖（ohpcd 制品仓已发布）
- glib/2.84.0.1（共享构建，GObject 类型系统一致性）
- 源码零补丁：上游仅依赖 GLib/GObject/GIO（`gio-unix-2.0`），
  无 gudev、无 Linux 专有 syscall、无 glibc 专有宏（已 grep 确认）

### 关键适配点
- **meson 解释器改写（E232 泛化）**：OHOS 下 conan 子进程无法 exec HMDFS 上的
  shebang 脚本（`bin/meson` 是 `#!/bin/sh`），报 `Permission denied` + Error 126。
  配方覆写 `run()`，仅在 `settings.os == "OHOS"` 时把 `meson <args>` 改写为
  `<python> <meson.py> <args>`。
- **glib codegen 工具**：meson 需要 `gdbus-codegen` / `glib-mkenums`（python 脚本）。
  `MesonToolchain` 不把宿主依赖的 `bin/` 放上 PATH → `generate()` 生成 `runpy`
  wrapper 并注入 `.pc` 变量（`gdbus_codegen=` / `glib_mkenums=`）。
- **`gio-unix-2.0` 转发 .pc**：glib 配方只导出 glib-2.0/gobject-2.0/gio-2.0 组件，
  上游 `dependency('gio-unix-2.0')` 由配方生成转发型 `.pc` 满足。
- **native file 补全**：MesonToolchain 不写 `ar`/`ranlib`/`pkg-config`，
  配方按绝对路径注入 `[binaries]`（OHOS 的 llvm-ar 不在 PATH）。
- **`.so` 别名物化**：构建沙箱不支持 `symlinkat`/`linkat`（`ln -s` 退出 1、
  `os.link` EPERM，而 `cp`/`copy2` 正常），meson install 跳过全部符号链接 →
  `package()` 用 `shutil.copy2` 把 `libplayerctl.so`、`libplayerctl.so.2`
  物化为同尺寸实体文件（与已发布 glib 包的打包形态一致）。
- **ELF 自签**：鸿蒙 PC XPM 要求被 exec 的 ELF 有签名 → 安装后
  `llvm-objcopy --remove-section .codesign` + `binary-sign-tool -selfSign 1`
  重签 `bin/` ×2 与 `lib/` ×3 共 5 个 ELF。
- **禁用 introspection / gtk-doc / shell completions**：OHOS worker 无
  `g-ir-scanner`、`gtkdoc-scan`，GIR 与 man/completion 属绑定与文档产物。

## 依赖
- glib/2.84.0.1

## 功能验证
```
<pkg>/bin/playerctl --version
# 输出: v2.4.1
```

消费方链接（`pkg-config --cflags --libs playerctl`）：
```c
#include <playerctl/playerctl.h>
/* 链接: -lplayerctl（公开头还需 glib 的
 *   -I<glib>/include/glib-2.0 -I<glib>/lib/glib-2.0/include） */
```

> 被测 ELF 无 RUNPATH（上游 meson 未设置），裸跑需
> `LD_LIBRARY_PATH` 指向 `<pkg>/lib` 与 glib 的 `lib/`；
> conanrun（VirtualRunEnv）环境已自动处理。

## 测试
- **上游测试（R51 三步法）**：`make test` = `dbus-run-session python3 -m pytest -sq`，
  `test/` 下 6 个文件共 **18 用例**。适配后实测 **11 通过 / 7 失败 / 0 跳过**，
  逐项名称与失败根因见 `2.4.1/notes.md` 的 R51 申报表。
  失败 6 项同源于依赖层 glib 2.84.0.1 的 GObject 内部断言（`gobject.c:649
  object_bit_unlock`），1 项为沙箱无 D-Bus system bus，均非本配方缺陷。
- **test_package（消费者视角）**：`test_playerctl.c` 19 条断言全过
  （版本宏契约 / 公共 GObject 类型注册 / `playerctl_player_name_copy()` 深拷贝 /
  真实执行 `bin/playerctl`、`bin/playerctld`）。
- **test_ohos（适配方新增鸿蒙消费者用例）**：8 项用例 / 57 条断言全过，
  `python3 test_ohos/run_ohos_test.py <pkg>`。

## 预编译包内容
- `bin/playerctl`、`bin/playerctld`
- `lib/libplayerctl.so.2.4.1` + 物化别名（`.so.2` / `.so`）
- `lib/pkgconfig/playerctl.pc`
- `include/playerctl/`（playerctl.h + 5 个子头）
- `share/dbus-1/services/org.mpris.MediaPlayer2.playerctld.service`
- `share/man/man1/playerctl.1`

## 参考
- 源码: https://github.com/altdesktop/playerctl
- 规范: https://specifications.freedesktop.org/mpris-spec/latest/
