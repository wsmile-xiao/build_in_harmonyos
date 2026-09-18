# debian-electronics

Debian Pure Blend（Debian Electronics，电子设计/EDA 领域软件选集）的元包族。一个 native
源包生成 15 个 `Architecture: all` 包：`electronics-tasks`（tasksel 描述包）、
`electronics-all`（总览元包，Recommends 全部 13 个 topic 元包）以及 13 个
`electronics-<topic>` 元包（analog / asic-dev / cad-gui / digital / doc / dsp-dev /
fpga-dev / gadgets / measurements / microcontrollers / pcb / radio-dev / simulation）。
软件本体是**任务选单元数据**（Deb822 task 文件 + tasksel desc + dpkg 依赖选择语义），
无编译产物、无可执行文件、无 C/C++ 源码。

本仓库将其作为 **data/metadata package** 适配：装 13 个任务文件原文 + genblends 生成的
tasksel desc + 官方机器可读依赖快照（0.2，0.3 源树无新快照）+ 派生 `registry.json`
（含 Debian 元包语义映射与 15 个 control 包声明）。**零 Conan requires**：快照/control
中的去重依赖引用为 OS/distro 包选择，机械复制会造出虚假且不可满足的依赖图。

## 上游

- 权威仓库：https://salsa.debian.org/blends-team/electronics
- Debian 源包：`debian-electronics_0.3.tar.xz`（native，Format 3.0；sha256 见 `conandata.yml`）
- 构建依赖：`blends-dev (>= 0.7~)`（Debian 特有）

## 适配

- 13 个任务文件（`tasks/`）→ `share/debian-electronics/tasks/`
- `debian-electronics-tasks.desc`（tasksel）→ `share/debian-electronics/tasksel/`
- `dependency_data/debian-electronics_0.2.json`（官方依赖快照）→ `share/debian-electronics/dependency_data/`
- `registry.json`（build 纯解析派生：13 任务 + 14 desc 段落 + 13 Key + 15 control 包 + 9 个 apt 降级 + 快照统计）
- `debian/copyright` → `licenses/`
- test_package 做结构/字段/映射交叉验证（上游无测试套件）

## 已知上游事实（如实披露）

- 2 个元包（`electronics-all`、`electronics-tasks`）没有对应的 `tasks/<topic>` 文件；
  13 个任务文件全部有对应的 metapackage —— 集合为**部分重叠而非 1:1**，registry
  按实测关系记录。
- task 文件为新 blends 1.1 格式（13/13 带 `Format:` 头），**无**旧格式
  `Depends: -> Recommends:` 降级；但 genblends 的 apt 可用性过滤仍把 9 个 topic 元包的
  若干任务文件 `Recommends:` 项降为元包 `Suggests:`（如 analog 的 gwave/qucs），
  registry.demotions 逐包记录。
- 0.3 源树**没有** 0.3 官方依赖快照（`dependency_data/` 仅 0.1/0.2），本包打包最新 0.2
  并在 notes/registry.semantics 披露，不伪造 0.3 快照。

## 参考

- [Debian Electronics Blend 任务页](https://blends.debian.org/electronics/tasks/index)
- [Debian Pure Blend 文档](https://wiki.debian.org/DebianPureBlends)
- 同族先例：`archives/d/debian-science/1.15`（旧格式 45 元包）、
  `archives/d/debichem/0.0.12`、`archives/d/debian-parl/1.9.33+nmu1`
