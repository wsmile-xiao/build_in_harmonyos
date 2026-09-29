# wmnd

Window Maker 网络设备流量监视 dockapp：X11 64x64 图标窗口按 `/proc/net/dev`
实时绘制各网络接口的收发速率，支持 10 种显示模式（bits/bytes/packets/errors 等）
与多种数据来源驱动，可用 `-D <driver> -I <iface>` 无头选型。

- 上游: <https://www.thregr.org/~wavexx/software/wmnd/>
- 许可证: GPL-2.0-or-later
- 构建系统: autotools（本仓配方用 Conan `AutotoolsToolchain` 驱动）

## 本仓版本

| 版本 | 状态 | conan ref |
|------|------|-----------|
| 0.4.18 | published | `wmnd/0.4.18` |

依赖（Conan 管理，cmd-pkgs 6.4.0 X11 轨）：`libx11/6.4.0`、`libxext/6.4.0`、
`libxpm/3.5.17`、`xorgproto/2025.1`。

## OHOS 适配要点（详见 0.4.18/notes.md）

- `config.guess`/`config.sub` 平台识别补丁：HarmonyOS → `aarch64-unknown-linux-ohos`
- `generate()` 显式下发依赖 `-I/-L` 与 `LD_LIBRARY_PATH`（Conan 2.29
  `AutotoolsToolchain` 不自动传递；`AC_CHECK_SIZEOF` 探针依赖后者）
- 产物 `bin/wmnd` 经 `binary-sign-tool` 自签（E549：OHOS 只加载带有效
  `.codesign` 段的 ELF）
- 平台限制：非特权进程读 `/proc/net/dev` 被 SELinux 拒绝（EACCES），
  自动枚举接口在无头环境下不可用，属预期行为
