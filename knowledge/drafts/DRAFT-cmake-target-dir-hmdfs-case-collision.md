# DRAFT: HMDFS 大小写不敏感使 CMake 仅大小写不同的双目标构建/autogen 目录碰撞，应重命名目标并用 OUTPUT_NAME 保留安装名

- **草稿 ID**: `DRAFT-cmake-target-dir-hmdfs-case-collision`
- **来源**: kglobalacceld-6.7.2 适配 run（patch 0004；失败证据 ci03 log 行 423–439，修复后 ci04 起构建正常）
- **状态**: DRAFT（随 kglobalacceld feat 分支交付，待主编/AI 审核提升为 E 条目）
- **配套文件**: `knowledge/drafts/DRAFT-cmake-target-dir-hmdfs-case-collision.kv`（同 stem 配对）
- **申报域**: 构建系统语义（build-system）｜分层 **L1**（平台文件系统语义 × CMake 目录命名规则，单库可申报，复发面由平台保证）

## 问题现象

CMake 工程在同一目录下存在仅大小写不同的两个 target（典型：库
`KGlobalAccelD` + 守护进程 `kglobalacceld`）时，在 OHOS HMDFS 构建树上
AUTOMOC 产物静默丢失，编译报：

```
src/kglobalaccel_interface.cpp:65:10: fatal error: 'moc_kglobalaccel_interface.cpp' file not found
src/component.cpp:383:10: fatal error: 'moc_component.cpp' file not found
src/kglobalacceld.cpp:562:10: fatal error: 'moc_kglobalacceld.cpp' file not found
src/kserviceactioncomponent.cpp:182:10: fatal error: 'moc_kserviceactioncomponent.cpp' file not found
```

make 生成器下同因不同症：`No rule to make target
'src/CMakeFiles/KGlobalAccelD_autogen_timestamp_deps.dir/depend'`。

## 根因

1. **HMDFS 大小写不敏感**（E193 平台属性）：仅大小写不同的路径解析为同一物理目录。
2. **CMake 按 target 名派生构建目录**：`CMakeFiles/<target>.dir` 与
   `CMakeFiles/<target>_autogen.dir`（AUTOMOC 目录名派生自 target 名）。
3. **双目标目录在 HMDFS 上物理合并**：库 `KGlobalAccelD_autogen` 与可执行
   `kglobalacceld_autogen` 为同一目录；后构建的可执行 autogen（HEADERS 为空，
   SOURCES 仅 main.cpp）将库的 `AutogenInfo.json`、`mocs_compilation.cpp`、
   `include/` 全部静默覆盖 → `moc_*.cpp` 从未生成。
4. 触发命令 `cmake --build`；失败证据：kglobalacceld-6.7.2 run ci03 log 行
   423–439（Ninja）、ci02（make）。AutogenInfo.json 实测 `HEADERS: []`、
   `SOURCES: [main.cpp]` 是覆盖发生的直接物证。

## 方案空间

- **rec_*（主方案）**：重命名可执行目标（如 `<name>_daemon`），
  `set_target_properties(... PROPERTIES OUTPUT_NAME <原名>)` 保留安装文件名
  与消费者兼容（patch 0004 实证，ci04 起构建正常）。
- **fallback_1**：改重命名库目标（daemon 名保留），代价是 EXPORT/CMake
  config 中库名变化，消费者 `find_package` 目标名需兼容层——仅当库名无下游
  消费者时可用。
- **fallback_2**：对可执行目标关 AUTOMOC（`AUTOMOC OFF`）并手动 moc——掩盖
  问题且维护成本高，仅作退路。

**禁止模式**：

- `forbid_1`：删除/改名**安装产物**迁就构建目录（rename OUTPUT_NAME 安装名）——
  破坏下游消费者对二进制名/CMake 目标名的兼容假设；test_package 与生态消费者
  全部失配。
- `forbid_2`：把两个目标放进不同源目录来"避开"碰撞——同目录双目标是上游结构，
  强行拆目录造成与上游 diff 膨胀，patch 难维护且不解决同目录新目标复现。

## 验证证据（自包含探针，任何人开新 shell 可跑）

```sh
# 1) 平台属性探针：HMDFS 上仅大小写不同的目录为同一 inode
mkdir -p /storage/Users/currentUser/tmp/probe/{KGlobalAccelD.dir,kglobalacceld.dir}
stat -c '%i' /storage/Users/currentUser/tmp/probe/* | sort -u | wc -l   # =1 即碰撞成立
rm -rf /storage/Users/currentUser/tmp/probe
# 2) 构建失败复现：任一"库名与 exe 名仅大小写不同"的 CMake 工程，Autogen 后
#    ls <build>/src/CMakeFiles/<exe>_autogen/ 与 <lib>_autogen/ 指向同一物理目录，
#    编译报 fatal error: 'moc_*.cpp' file not found
#    （kglobalacceld-6.7.2 run ci03 行 423–439；修复后 ci04–ci15 全绿）
```

## 四范围多轴查重（含 Auditor 修正项 2）

检索范围：`knowledge/graph/index.tsv`（766 条）+ `knowledge/drafts/` + 经验仓
`ophs_ci_review`（grep case.insens/AUTOMOC 零命中）；检索词：hmdfs、
case-insens、AUTOMOC/autogen、dual-case、大小写。

| 近邻条目 | 逐项差异（不构成重复） |
|---|---|
| E193 | 同平台属性（HMDFS 大小写不敏感），但作用层是**测试**（skip-case-sensitive-tests），不涉 CMake 构建目录与 AUTOMOC |
| **E416** | 同"双 case 并存"现象域，但层是 **CI/仓管理**：官方大写元数据目录与新增小写 recipe 目录在质量门禁（L0m slug、L4 误扫）与 git loose ref 上的碰撞；无 CMake target/AUTOMOC 语义。引用其"大小写不敏感 FS 上物理合并"表述，机理层不同 |
| **E470** | 同"大小写不敏感 FS × 构建目录"现象域，但碰撞物是**源码树内文件 vs conan cmake_layout 构建目录**（Bazel `BUILD` vs `build/`，NotADirectoryError）；本条是**构建树内两个 CMake target 派生目录**的碰撞且静默覆盖产物，修复模式（rename target + OUTPUT_NAME）与 E470（build_folder 换名）不同类 |
| E011/E046/E050/E079 等 HMDFS 族 | 权限/符号链接/硬链接面，非大小写语义 |

**新增价值**：构建系统语义层的"同目录物理合并 → 静默覆盖 AUTOMOC 产物"机理
与 rename+OUTPUT_NAME 修复模式在库内首次发现，四条近邻均不覆盖。

## 适用边界

- 适用：任何在 HMDFS 等大小写不敏感文件系统上构建的 CMake 工程，其同一目录
  下存在仅大小写不同的两个 target 名（典型：`libX.so` 库 + 同名小写守护进程，
  KDE 生态高频命名惯例）。
- 不适用：大小写敏感文件系统（Linux ext4 等）；不同名双目标；非 CMake 构建系统
  的目录派生（参见 E470 的 conan cmake_layout 场景，修复模式不同类）。

## 关键词

HMDFS, case-insensitive, 大小写不敏感, CMakeFiles/<target>.dir, _autogen.dir,
AUTOMOC, mocs_compilation.cpp, moc_*.cpp file not found, 静默覆盖, rename
target, OUTPUT_NAME, kglobalacceld, KGlobalAccelD

## 挂钩

- `similar_to`: E193, E416, E470（HMDFS 大小写语义族）
- `principles`: P016（HMDFS 限制必须用替代方案）, real-evidence-over-assumption, minimal-recipe-diff
