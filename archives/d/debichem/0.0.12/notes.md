# debichem 0.0.12 — 适配笔记

## 概述
Debian Pure Blend（计算化学）元包族。真实身份：**不是库**——一个 native 源包生成
**13 个 `Architecture: all` 纯元包**（`debichem-tasks` tasksel 描述包 + 12 个
`debichem-<task>` metapackage）。零编译产物、零测试；"内容" = 12 个 Deb822 任务文件 +
genblends 生成的 tasksel desc + dpkg 依赖选择语义。

## 真实身份 / 源
- salsa: https://salsa.debian.org/blends-team/debichem（sid 当前源版本 = 0.0.12）
- 源: pool `debichem_0.0.12.tar.xz`（native, sha 见 conandata，实测与 .dsc 一致）
- Build-Depends-Indep: blends-dev(>=0.6.95)；debian/rules include blends-dev 规则
  （blend-gen-control / blend-install-helper），须在 Debian 环境（apt 可用性过滤）生成。

## 真实 .deb 布局（13 个 0.0.12 .deb 实测）
- debichem-tasks: Depends tasksel；只装 `/usr/share/tasksel/descs/debichem-tasks.desc` + doc
- 12 个 metapackage: 一律 `Depends: debichem-tasks (=0.0.12)`；装
  `/usr/share/blends/tasks/debichem/<task>`（一行标题）+ doc + postinst/prerm
- 元包 Depends/Recommends/Suggests 与任务文件的关系（blends 旧格式规则）:
  任务文件无 `Format:` 头 → 其 `Depends:` 在 metapackage 里降级为 **Recommends**；
  `Suggests:` → **Suggests**。（实测 .deb 佐证）

## Conan 建模（单 metadata/registry 包，零伪造）
- 单 recipe `debichem/0.0.12`，data/metadata：package() 装真实物
  `share/debichem/tasks/*`（12 个原文）+ `share/debichem/tasksel/debichem-tasks.desc`
  （源树生成物原文）+ build() 纯解析生成的 `share/debichem/registry.json`
  （task→title/desc/depends/suggests + Debian 语义映射）+ licenses/copyright。
- **零 Conan requires**：Depends/Recommends/Suggests 全部是 OS/distro 包选择
  （metadata-only）；机械复制 109+ 个 OS 包进 requires 会造虚假依赖图 → 禁止。
- 不装 `dependency_data/*.json`（历史快照，无 0.0.12；避免误导为当前依赖）。
- test_package：结构/字段/计数/映射断言 + registry 与打包任务文件交叉复核（本地 create 已 PASS）。

## 诚实记录（drift / 事实）
- 任务文件（意图）与 .deb 实发存在 drift：0.0.12 changelog 声称新增 comet-ms / mopac /
  xtb / openmolcas / libdbcsr-dev / libbtas-dev，但 0.0.12 实装 .deb 无（apt 可用性过滤）。
  本 recipe 以 **tasks/ 源文件为准打包并如实披露**；registry 的 recommends 集 = 任务文件
  Depends（按旧格式语义），不代表 Debian 实发 Recommends 过滤结果。
- `visualisation` 任务文件标题 "3D Visualization" ≠ 包名（上游美/英拼写不一致），如实保留。
- dependency_data 目录 9 份历史 JSON（无 0.0.12），未打包。

## 上游测试
无（无 autopkgtest/CI/test）。upstream 0/0；上述为 Harmony 特有 package/data 验证。
