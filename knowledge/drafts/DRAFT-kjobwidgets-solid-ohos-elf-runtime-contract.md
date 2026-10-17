# DRAFT-kjobwidgets-solid-ohos-elf-runtime-contract：OHOS 共享库可消费产物闭环

OHOS 上的 Conan/CMake 共享库可能同时缺少稳定 `DT_SONAME`、把 Conan 缓存绝对路径写入 `DT_NEEDED`，并在消费者运行时因 ELF 签名或运行库布局被加载器拒绝。KJobWidgets 和 Solid 的修复矩阵表明，可靠交付需要在任务私有产物中完成 SONAME 修复、依赖名规范化、运行库实体化和重新签名；仅设置 RPATH、`LD_LIBRARY_PATH` 或 Conan runtime env 不足。

## 身份与当前结论

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-kjobwidgets-solid-ohos-elf-runtime-contract` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-kjobwidgets-solid-ohos-elf-runtime-contract.kv` |
| 当前状态 | 已有验证证据待审 |
| 建议去向 | 补充既有模式 |
| 实际贡献者 | zxyAtom |
| 来源任务/PR | [#7389](https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/merge_requests/7389) |
| 提取方式 | 已有普通 PR 升级 |
| 本次交付 PR | 原位升级为 #7389 |
| 包及配方版本 | kjobwidgets / 6.18.0；Solid / 6.18.0 为交叉验证 |
| 上游版本与源码 | KDE Frameworks 6.18.0；`source_sha256` 见各自 manifest |
| 知识来源提交 | `976b5abe6706964cb1e5a6a6058168dca2058ceb` |
| 被验证提交 | `976b5abe6706964cb1e5a6a6058168dca2058ceb` |
| 最后更新 | 2026-09-07 |

本草稿验证了 KJobWidgets 和 Solid 在 OHOS CI Worker 上的共享库消费闭环。仍未证明：真实物理设备上的相同加载策略，以及未覆盖的上游 GUI/DBus 测试行为。

## 从普通 PR 提取的依据

原 PR 标题、状态与提取基线：`【依赖项】feat(kjobwidgets): 6.18.0 适配 HarmonyOS PC`；当前 HEAD 为 `976b5abe6706964cb1e5a6a6058168dca2058ceb`，CI Buildbot `#41659` / buildid `47322` 通过。

| 原 PR 事实 | 具体位置与版本 | 提炼出的可复用机制 | 本次补充 |
|---|---|---|---|
| OHOS CMake SONAME 规则 | `archives/k/kjobwidgets/6.18.0/conanfile.py`，commit `f86e007c44f5` | 为 HarmonyOS 显式提供 shared-library SONAME 链接规则 | 与 Solid `24a1c77303bf` 交叉验证 |
| 包产物依赖名规范化 | 同上，commit `976b5abe6706` | 安装后仅在任务私有产物中去除 Conan 缓存绝对 `DT_NEEDED` 前缀 | KJobWidgets Build `#41645` 到 `#41659` 的反例/通过对照 |
| ELF 签名与消费者 staging | 同上，commits `6dc87fb1bd42`、`1aca2adf3601` | 消费前准备实际构建目录中的运行库并重新签名 ELF | Solid Build `#41619` 独立复现 |

原 PR 已有的贡献：KJobWidgets 配方、OHOS 选项裁剪、消费者测试和上述实现提交。

本次提炼新增的贡献：将多轮失败归纳为一个可复用的产物契约，并绑定失败/成功 Buildbot 日志；相对已有 E537/E077/E452，补充了四个条件必须在同一消费者执行边界闭合的证据。

## 1. 触发条件与可辨认现象

目标为 OHOS aarch64 CI Worker，Conan/CMake 构建 KF6 动态库并运行 `test_package` 消费者。典型失败包括：

```text
libKF6JobWidgets.so missing DT_SONAME
DT_NEEDED contains .../.conan2/p/...
Error loading shared library libKF6JobWidgets.so.6
IMPORTED_NO_SONAME TRUE
```

建议错误签名：`missing DT_SONAME|DT_NEEDED.*\\.conan2/p/|IMPORTED_NO_SONAME|Error loading shared library.*libKF6`。

## 2. 根因与排除项

缺少 SONAME 时 CMake 会把 imported target 的绝对 Conan 路径传给链接器；该路径会进入 `DT_NEEDED`，在另一执行目录不可重定位。即使依赖名已修复，OHOS loader 仍会校验 ELF 签名并要求运行库位于实际消费者可见的任务目录，因此只设置搜索路径不能替代产物 staging 和签名。

历史尝试已排除单独依赖 `LD_LIBRARY_PATH`、RPATH、Conan `conanrun` 和普通符号链接作为完整修复；这些尝试分别见 Solid Build `#41532/#41538/#41539/#41543/#41545` 和 KJobWidgets Build `#41626/#41645` 的原始日志。

## 3. 最小修复与选择条件

1. 在 OHOS CMake toolchain 中设置 `CMAKE_SHARED_LIBRARY_SONAME_C_FLAG/CXX_FLAG`。
2. 安装后仅处理任务私有包产物，将 `DT_NEEDED` 的 Conan 绝对路径归一为库名。
3. 将消费者运行所需 `.so` 放入实际 build/bindir 运行目录，并在执行前对任务私有 ELF 重新签名。
4. 保持 Conan 缓存只读；不得用未重新签名的 `patchelf` 产物代替正式包。

## 4. 验证矩阵与证据绑定

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 |
|---|---|---|---|---|
| EVID-01 | historical/target-executed | KJobWidgets Build `#41626` / buildid `47287` | L5 artifact audit + consumer | SONAME、绝对 `DT_NEEDED`、`IMPORTED_NO_SONAME` 失败 |
| EVID-02 | historical/target-executed | KJobWidgets Build `#41645` / buildid `47308` | 同上 | SONAME 已通过，绝对 `DT_NEEDED` 仍失败 |
| EVID-03 | target-executed | KJobWidgets HEAD `976b5abe`，Build `#41659` / buildid `47322` | `test_kjobwidgets`、L0/L1/L4/L5 | 全部通过；consumer 输出 `PASS: KStatusBarJobTracker constructed OK` |
| EVID-04 | historical/target-executed | Solid Build `#41516` / `47177`、`#41532` / `47193` | L5 + consumer | 先后暴露 SONAME 缺失和 loader 运行失败 |
| EVID-05 | target-executed | Solid HEAD `c623b924`，Build `#41619` / `47280` | `test_solid`、L0/L1/L4/L5 | 全部通过；`PASS: Solid block-device query returned 0 valid entries` |

## 5. 测试统计与边界

- KJobWidgets 消费者：`1/1` 通过；L0/L1/L4/L5 全通过；L2 因无 `bin/` 目录跳过。
- Solid 消费者：`1/1` 通过；L0/L1/L4/L5 全通过；L2 为非阻塞能力探测跳过。
- 上游 CTest 未在当前配方中启用（`BUILD_TESTING=OFF`），不能把消费者 smoke 计作上游覆盖；未执行的上游用例须按源码清单逐项说明。当前使用的 `qtbase/6.11.1` 变体关闭 `FEATURE_dbus`；远端另有开启 DBus 的 `qtbase-sql-dbus/6.11.1` 变体，但本 PR 尚未切换依赖图。
- 证据来自远程 OHOS CI Worker，不等同于真实物理设备验证。

## 6. 与已有知识的关系及增量

| 已核验条目 | 已有内容 | 本次新增 | 建议处理 |
|---|---|---|---|
| E537 | Conan 绝对 `DT_NEEDED` 与链接期 SONAME | 两个 KF6 包证明安装后规范化在任务私有边界可行，并给出失败到通过的 CI 矩阵 | 补充 |
| E077/E452 | OHOS ELF 签名与私有副本重签 | 证明签名必须与实际消费者 staging 同时闭合，且 RPATH/`LD_LIBRARY_PATH` 单独无效 | 补充 |

本条目不主张新建独立错误模式；#7389 作为主案例，#7390 作为交叉验证。

## 7. 来源索引与自检

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 修复实现 | `archives/k/kjobwidgets/6.18.0/conanfile.py`、`test_package/conanfile.py` | `976b5abe` |
| 交叉实现 | `archives/s/solid/6.18.0/` | `c623b924` |
| 证据报告 | `archives/k/kjobwidgets/6.18.0/reports/knowledge-evidence.md` | 本次交付 |
| 原始验证记录 | Buildbot `#41659/#41619` | buildid `47322/47280` |

最终处理建议：作为 E537/E077/E452 的补充候选提交。

原 PR 升级建议：支持原位升级；保留原有标题，不改为 `【知识库扩展】`。

剩余问题及下一项具体动作：等待知识审核和平台合入；如维护者要求，补充上游 CTest 的精确库存清单。
