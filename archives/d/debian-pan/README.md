# debian-pan

Debian Pure Blend（Debian Pan，PAN = Photons And Neutrons，X 射线/中子科学
软件选集）的元包族。一个 native 源包生成 18 个 `Architecture: all` 包：
`pan-tasks`（tasksel 描述包）、`pan-config`（配置包）以及 16 个
`pan-<主题>` 元包。软件本体是**任务选单元数据**（Deb822 task 文件 + tasksel
desc + dpkg 依赖选择语义），无编译产物、无可执行文件、无 C/C++ 源码。

本仓库将其作为 **data/metadata package** 适配：装 18 个任务文件原文 +
genblends 生成的 tasksel desc + 官方机器可读依赖快照 + 派生 `registry.json`
（含 Debian 元包语义映射与 18 个 control 包声明）。**零 Conan requires**：
0.4 快照中的 446 条去重依赖引用为 OS/distro 包选择，机械复制会造出虚假且
不可满足的依赖图。

## 上游

- 权威仓库：salsa.debian.org/blends-team/pan（tag `debian/0.4`）
- 源包归档：`pan-debian-0.4.tar.gz`（native，Format 3.0；sha256 见 `conandata.yml`）
- 构建依赖：`blends-dev (>= 0.6.15)` + `debhelper-compat (= 12)`（Debian 特有，
  本配方不依赖：不执行 Debian 打包流程）

## 适配

- 18 个任务文件（`tasks/`）→ `share/debian-pan/tasks/`
- `debian-pan-tasks.desc`（tasksel）→ `share/debian-pan/tasksel/`
- `dependency_data/debian-pan_0.4.json`（官方依赖快照）→ `share/debian-pan/dependency_data/`
- `registry.json`（build 纯解析派生：18 任务 + 17 desc 段落 + 16 Key +
  18 control 包 + 快照统计）→ `share/debian-pan/`
- `debian/copyright` → `licenses/`
- test_package 做结构/字段/映射交叉验证 + 鸿蒙特有测试（OHOS 平台适配预检），48 项断言

## 已知上游事实（如实披露）

- 任务文件集**严格包含**元包集：`laue`、`mx-dev` 有任务文件但**没有**
  `pan-laue`/`pan-mx-dev` 元包。registry 按实测关系记录
  （`semantics.mapping_asymmetry`），不做 1:1 归一化假设。
- task 文件为**新格式**（blends 1.1，每文件带 `Format:` 头），与同族
  debian-science（旧格式、文件级 Depends 降级为元包 Recommends）不同：
  本包无文件级 `Depends:`，元包 Recommends/Suggests 直接沿用文件级字段。
- 官方快照仅打包 0.4 一份（`dependency_data/` 中 0.1~0.3 历史快照未打包，
  避免被误读为当前依赖）。

## 参考

- 同族先例（旧格式 blend）：`archives/d/debian-science/1.15/`
- 知识草稿：`knowledge/drafts/E560-draft-218E.*`（R47 语言预检检测器盲区）、
  `knowledge/drafts/E563-draft-218E.*`（无测试上游本地验证补充模板）
