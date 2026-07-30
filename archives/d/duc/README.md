# duc

Duc 是磁盘使用量索引、检查和可视化工具。本适配使用 SQLite 数据库后端，
保留命令行索引与查询能力，不包含图形和交互式终端界面。

## 可用版本

| 版本 | 状态 | 构建系统 |
|------|------|----------|
| 1.4.6 | built | autotools |

## 构建配置

- 数据库后端：`sqlite3/3.49.1`
- 禁用：Cairo 图形、X11 GUI、ncurses UI
- 保留：`duc index`、`duc info`、`duc ls` 等命令行功能
- 使用 GitHub 官方 Release 源码包，包含 `configure`

## 验证状态

已在 OpenHarmony aarch64 真机完成 `conan-verify`、原生 `conan create` 和
仓库 CI 验证。消费者测试通过 `duc --version`、索引、信息查询和目录列表。
