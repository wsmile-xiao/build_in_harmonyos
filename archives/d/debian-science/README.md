# debian-science

Debian Pure Blend（Debian Science，科研领域软件选集）的元包族。一个 native 源包生成
45 个 `Architecture: all` 包：`science-tasks`（tasksel 描述包）、`science-config`
（配置包）、`science-all`（总览元包）、`science-electronics`（过渡元包）以及 41 个
`science-<topic>` 元包。软件本体是**任务选单元数据**（Deb822 task 文件 + tasksel desc +
dpkg 依赖选择语义），无编译产物、无可执行文件、无 C/C++ 源码。

本仓库将其作为 **data/metadata package** 适配：装 46 个任务文件原文 + genblends 生成的
tasksel desc + 官方机器可读依赖快照 + 派生 `registry.json`（含 Debian 元包语义映射与
45 个 control 包声明）。**零 Conan requires**：1.15 快照中的去重依赖引用为 OS/distro
包选择，机械复制会造出虚假且不可满足的依赖图。

## 上游

- 权威仓库：https://salsa.debian.org/blends-team/science
- Debian 源包：`debian-science_1.15.tar.xz`（native，Format 3.0；sha256 见 `conandata.yml`）
- 构建依赖：`blends-dev (>= 0.7.5~)` + `debhelper-compat (= 13)`（Debian 特有）

## 适配

- 46 个任务文件（`tasks/`）→ `share/debian-science/tasks/`
- `debian-science-tasks.desc`（tasksel）→ `share/debian-science/tasksel/`
- `dependency_data/debian-science_1.15.json`（官方依赖快照）→ `share/debian-science/dependency_data/`
- `registry.json`（build 纯解析派生：46 任务 + 42 desc 段落 + 41 Key + 45 control 包 + 快照统计）
- `debian/copyright` → `licenses/`
- test_package 做结构/字段/映射交叉验证（上游无测试套件）

## 已知上游事实（如实披露）

- 4 个元包（`science-all`、`science-config`、`science-electronics`、`science-tasks`）
  没有对应的 `tasks/<topic>` 文件；5 个任务文件（`bci`、`devices`、`neuroscience-datasets`、
  `social`、`tools`）没有对应的 metapackage —— 二者是**部分重叠而非 1:1**，registry
  按实测关系记录，不做 1:1 假设。
- task 文件为旧格式（无 `Format:` 头），按 blends 规则文件级 `Depends:` 降级为元包
  `Recommends:`；`Metapackage:` 字段仅在 3 个文件（`bci`/`devices`/`tools`）出现，值均为 `false`。
- 官方快照仅打包 1.15 一份（`dependency_data/` 中的 37 份历史快照未打包，避免被误读为当前依赖）。

## 参考

- [Debian Science Blend 任务页](https://blends.debian.org/science/tasks/index)
- [Debian Pure Blend 文档](https://wiki.debian.org/DebianPureBlends)
