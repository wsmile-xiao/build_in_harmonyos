# its-playback-time（上游程序 `ipbt`）

带 ncurses 的 ttyrec 终端会话录像播放器，支持前进、后退和跳转到任意帧。

Debian 源包名叫 `its-playback-time`，上游 tarball 与实际安装的程序叫 `ipbt`。

## 软件信息

| 字段 | 值 |
|------|-----|
| Conan 包名 | `its-playback-time` |
| 安装的程序 | `ipbt`（交互式播放器）、`ipbt-dump`（非交互转换器） |
| 构建系统 | CMake ≥ 3.10 |
| 许可证 | MIT |
| 上游主页 | https://www.chiark.greenend.org.uk/~sgtatham/ipbt/ |
| 上游 git | https://git.tartarus.org/simon/ipbt.git |
| 维护者 | Simon Tatham / Debian: Ian Jackson |

## 它做什么

`ipbt` 内嵌了 PuTTY 的终端模拟器：先把整份 ttyrec 录像喂进模拟器，把每一帧的屏幕状态存进内部「电影数组」，之后就可以任意顺序取帧。因此它不只能像普通播放器那样暂停和调速，还能往回倒、也能直接跳到第 N 帧。

`ipbt-dump` 是配套的非交互工具，把一份录像转成 hex dump（`-H`）、typescript（`-S`，即 `script(1)` 那样的原始终端数据）或逐帧屏幕内容的 XML（`-x`）。

## 产出物

| 路径 | 说明 |
|------|------|
| `bin/ipbt` | 交互式 curses 回放播放器 |
| `bin/ipbt-dump` | 录像转换器（hex dump / typescript / 屏幕 XML） |
| `share/man/man1/ipbt.1` | man 手册页（tarball 自带的预生成版本） |
| `share/doc/its-playback-time/README` | 上游 README |
| `licenses/LICENCE` | MIT 许可 |

## 依赖

| 包 | 用途 |
|----|------|
| `ncurses/6.6` | 宽字符 curses 库（静态链入两个可执行文件）；运行期还需其 terminfo 数据库 |

`halibut` 仅在**重新生成** man page 时才需要，本包不使用它作构建依赖（交叉构建无法执行 OHOS aarch64 的 halibut），改为安装 tarball 自带的 `ipbt.1`。

## 已适配版本

| 版本 | 状态 | 适配说明 |
|------|------|------|
| `0.2026-05-26.fdcd2b0` | built | 首个版本；1 个可移植性补丁（FindCurses 头文件识别兜底），无需 HarmonyOS 特判 |

详细适配过程、补丁理由与验证证据见
[`0.2026-05-26.fdcd2b0/notes.md`](./0.2026-05-26.fdcd2b0/notes.md)。