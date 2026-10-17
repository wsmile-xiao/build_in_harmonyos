# diction

GNU diction — 检查文本中冗长、易误用短语的命令行工具，配套 `style` 检查用词/句法问题。

- 上游主页: https://www.gnu.org/software/diction/
- 源码: https://ftp.gnu.org/gnu/diction/diction-1.11.tar.gz
- 归档版本: 1.11（见 `1.11/`）

## 提供的命令

| 命令 | 说明 |
|------|------|
| `diction` | 标记文本中冗长/易误用的短语 |
| `style` | 检查文本的句法/用词问题 |

## 运行时数据

短语库随包安装于 `share/diction/`（`C`、`de`、`en`、`en_GB`、`nl`）。
`diction` 默认相对可执行文件查找该目录（`<bindir>/../share/diction/`，未命中回退编译期 `SHAREDIR`），因此包可安装/迁移到任意前缀。

## 适配状态

| 版本 | 状态 | 说明 |
|------|------|------|
| 1.11 | 已适配 | HarmonyOS PC / aarch64；5 个平台补丁；上游测试 9/9 通过 + 消费者测试 5/5 通过（含鸿蒙迁移测试） |
