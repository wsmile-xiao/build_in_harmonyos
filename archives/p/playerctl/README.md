# playerctl

[playerctl](https://github.com/altdesktop/playerctl) 是一个基于 MPRIS 的命令行媒体播放器控制工具与库，提供 `playerctl` / `playerctld` 等可执行程序以及 `libplayerctl` 共享/静态库，供应用程序查询与控制遵循 MPRIS 规范的媒体播放器（如通过 D-Bus 暴露的播放器）。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [2.4.1.1](./2.4.1.1/) | built | 2026-09-29 |

> 版本号 `2.4.1.1` 中的末段 `.1` 为 HarmonyOS PC 适配的本地修订位（R37/L0j：上游 `2.4.1` 已先于本适配发布，依规则 bump X.Y.Z.N 新建目录）。

## OHOS 适配要点

- 构建系统为 **meson**，经 Conan `Meson`/`MesonToolchain` 驱动交叉编译至 `os=OHOS, arch=aarch64`。
- 上游通过 `gnome.gdbus_codegen` / `gnome.mkenums_simple` 在构建期生成 glib 辅助代码。受 HMDFS 对新建脚本间歇性 `execve EACCES` 影响，配方在 `generate()` 内用 `python3 <glib工具>` **预生成** 4 个静态文件并将 `meson.build` 中的 `gnome.*` 调用改写为 `files(...)` 静态引用，构建期零 exec glib 工具。
- glib 未提供 `gio-unix-2.0` 组件，配方在 `generate()` 内直写 `gio-unix-2.0.pc` 至 `generators_folder` 以补全依赖解析。
- `package()` 手工安装 `playerctl-enum-types.h`（上游经 `gnome.mkenums_simple` 产出，改为静态文件后 meson 不再 install，而 `playerctl.h` 依赖它）。
- test_package 不依赖 pkg-config：OHOS worker 上 PkgConfigDeps 注入的 `PKG_CONFIG_PATH` 不可靠，故消费者测试直接遍历 `self.dependencies` 的 `cpp_info` 拼出 clang 命令行。

## 依赖

- `glib/2.84.0.1`（gobject / gio）
- `meson/1.11.0`（build_requires）

## 功能验证

```bash
# Conan 验证（含 test_package 端到端消费者测试）
conan create archives/p/playerctl/2.4.1.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  --build=missing --user=ohpcd --channel=stable
# 预期输出: LIBPLAYERCTL_CONSUMER_OK: library linked, public API reachable
```

运行时媒体控制需目标设备具备 D-Bus 会话总线（runtime 依赖）。
