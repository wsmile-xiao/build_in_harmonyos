# lensfun-tools

`lensfun-tools` 是 [Lensfun](https://lensfun.github.io/) 项目（镜头校正库与镜头数据库）的命令行工具子集，对应发行版的 `lensfun-tools` 包：

- `lenstool`：参考实现校正工具，基于镜头数据库对图像做畸变、色差、暗角校正与几何投影转换（PNG 输入输出）。
- `lensfun-update-data`：从上游下载并更新本地镜头数据库。
- `lensfun-add-adapter`：向本地镜头数据库追加转接环（mount adapter）兼容条目。
- `g-lensfun-update-data`：`lensfun-update-data` 的图形会话包装脚本。

## 版本

| 版本 | 状态 |
| --- | --- |
| 0.3.4 | built |

- 上游：https://github.com/lensfun/lensfun （v0.3.4）
- 构建依赖：glib2（liblensfun 核心）、libpng（lenstool 图像 I/O）
- 说明：`lenstool` 静态链接入树内 `liblensfun`，包内只交付工具与镜头数据库，不重复提供库制品；库本体见 `archives/l/lensfun`。

Homepage: https://lensfun.github.io/
