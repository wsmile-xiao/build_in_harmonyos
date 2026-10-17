# xset

xset 是 X Window System 的用户偏好设置命令行工具（X.Org 官方 app），用于查询和
修改 X server 侧的：bell 音量/音高/时长、keyclick、键盘 LED、鼠标加速度与阈值、
keymap 与 auto repeat、字体路径（fp）、screen saver、DPMS（显示电源管理信令）、
XKB 相关开关等。`xset q` 查询当前全部设置。

本仓库提供其在 HarmonyOS PC (aarch64) 上的 Conan 配方。

## 官网

- 上游仓库：https://gitlab.freedesktop.org/xorg/app/xset
- 源码发布：https://xorg.freedesktop.org/archive/individual/app/

## 许可证

MIT（见 `COPYING`，打包进 `licenses/COPYING`）

## 常用方式

```sh
xset -version                 # 打印版本（不需要 X server）
xset q                        # 查询当前全部设置（需要 X server）
xset -b                       # 关闭 bell
xset b 50 400 1200            # 设置 bell volume/pitch/duration
xset s 300 60                 # 屏保 timeout/cycle
xset dpms 600 900 1200        # DPMS standby/suspend/off
xset -dpms                    # 关闭 DPMS
xset q --                     # 查询并复位部分设置
```

## 编译信息

| 版本 | 状态 | 编译日期 | 构建系统 | 补丁数 |
|------|------|----------|----------|--------|
| 1.2.5 | 见 `1.2.5/manifest.yaml` | 2026-09-25 | autotools | 0 |

## 依赖

- `libx11/6.4.0`、`libxext/6.4.0`、`xorgproto/2025.1`（均为 ohpcd 制品仓已发布的
  conan 依赖）
- **libXmuu**：xset 的 `configure.ac` 无条件要求 pkg-config 模块 `xmuu`
  （`xset.c` 的 X 错误回调用 `XmuPrintDefaultErrorMessage`）。ohpcd 制品仓没有
  libxmu 包（配方已合入 main，但制品未发布），故本配方按仓库既有的 vendored
  依赖模式从 X.Org 官方源只构建 `libXmuu`（5 个源文件、只依赖 x11）并静态链入，
  不构建需要 `xt` 的全量 libXmu。细节见 `1.2.5/conanfile.py` 头部与
  `1.2.5/notes.md`。

## 已知平台问题

- **完整功能需要 X server**：无 X 会话的环境（CI、以及未起 X 的真机）只能验证
  `-version`、usage 分支与"非法 display 优雅失败"三条路径；`xset q` 与各设置
  子命令未覆盖，口径与 xterm/410、xclip、xsel/1.2.1、xeyes/1.3.1 一致。
- `xf86misc` 上游默认关闭；`fontcache`（`xfontcache` 未发布）在本配方显式
  `--without-fontcache` 关闭，以保证 CI 与本地走同一分支。
- 静态链入的 libXmuu 来自上游 libXmu 1.1.4（本仓库无已发布的 libxmu 制品），
  与 xset 自身版本无关，升级 xset 版本时若上游改用了新的 Xmu API 需同步复核。
