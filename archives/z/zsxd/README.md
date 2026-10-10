# zsxd

https://gitlab.com/solarus-games/games/zsxd

Zelda Mystery of Solarus XD 是 Solarus 引擎（https://gitlab.com/solarus-games/solarus）
的游戏任务数据包（quest data）：一个 2D 塞尔达类游戏。本包只含游戏数据与启动脚本，
**无任何 C/C++ 编译**——上游 CMakeLists.txt 仅把 `data/` 压成 `data.solarus`、
生成一行 `bin/zsxd` 启动脚本（`solarus-run <prefix>/share/solarus/zsxd $*`）并安装
图标/desktop 入口。

## OHOS Adaptation

- 纯数据/脚本包：无编译阶段——build() 只做数据自检并用 Python 标准库
  zipfile 复刻上游 CMake 打包（条目集合=上游 CMake glob 的 674 个文件，arcname 相对
  `data/` 无前缀），package() 纯搬运，不依赖外部 `zip` 二进制。
- `bin/zsxd` launcher 按脚本自身相对位置解析 quest 目录（`dirname $0/..` →
  `share/solarus/zsxd`），不写死构建期绝对路径，Conan 重定位后依然可用。
- launcher 增加 `--version`/`--help` 自处理分支（引擎为运行期外部依赖，打包/CI 环境
  无 `solarus-run` 时 launcher 仍可自检）；真实启动仍 `exec solarus-run`。
- 运行期环境变量 `ZSXD_QUEST_DIR` 由配方 runenv_info 自动导出，消费方可直接取用
  quest 数据目录。

## Usage

```
zsxd --version            # zsxd 1.12.2
zsxd                      # 启动游戏（需 solarus-run 在 PATH）
```

## Installation layout

- `share/solarus/zsxd/data.solarus` — quest 数据归档（上游等价路径）
- `bin/zsxd` — launcher 脚本（Solarus 引擎入口）
- `share/applications/zsxd.desktop`、`share/pixmaps/zsxd.png` — 桌面入口/徽标
- `licenses/license.txt`、`share/doc/zsxd/readme.md` — 许可与说明

## License

混合许可（见 license.txt）：Lua 脚本 GPL-3.0-only；自创数据 CC BY-SA 4.0；
部分素材属 Nintendo/Mojang（上游以 fair use 名义提供）。
