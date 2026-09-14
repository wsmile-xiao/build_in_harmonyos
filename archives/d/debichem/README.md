# debichem

Debian Pure Blend（计算化学领域）的元包族。一个 native 源包生成 13 个 `Architecture: all`
包：`debichem-tasks`（tasksel 描述）+ 12 个 `debichem-<task>` metapackage。软件本体是
**任务选单元数据**（Deb822 task 文件 + tasksel desc + dpkg 依赖选择语义），无编译产物。

本仓库将其作为 **data/metadata package** 适配：装 12 个任务文件原文 + genblends 生成的
tasksel desc + 派生 registry.json（含 Debian 元包语义映射）。**零 Conan requires**：
所有依赖选择均为 OS/distro 包，机械复制会造虚假依赖图。

## 上游
- 权威仓库：https://salsa.debian.org/blends-team/debichem
- Debian 源包：`debichem_0.0.12.tar.xz`（native；sid 当前源版本 = 0.0.12）

## 适配
- 12 个任务文件（`tasks/`）→ `share/debichem/tasks/`
- `debichem-tasks.desc`（tasksel）→ `share/debichem/tasksel/`
- `registry.json`（build 纯解析派生，记录 task→Depends/Suggests + 旧格式降级语义）
- test_package 做结构/字段/映射交叉验证（无上游测试套件）。

## 已知上游事实（如实披露）
- 0.0.12 changelog 称新增 comet-ms/mopac/xtb/openmolcas 等，但 0.0.12 实装 .deb 无
  （genblends 在目标套件的 apt 可用性过滤所致）。
- `visualisation` 任务标题 "3D Visualization" 与包名拼写不一致（上游事实）。
