# CMake 平台模块缺失使 `UNIX` 未定义，上游 `if(UNIX)` 守卫的整份实现被静默剔除

- **形态**：knowledge/drafts 条目草稿（最终编号 Exxx 由知识库主编确认；本次取号 E577）
- **配套 kv**：`knowledge/drafts/DRAFT-E577-cmake-ohos-unix-guard-silent-drop.kv`
- **申报路径**：B【知识库扩展】（L1 平台/构建系统语义层，单库发现即可申报）
- **来源 run**：libvpl/2.16.0 HarmonyOS PC 首次适配（新增包，PC 专项积分赛；2026-09-15 设备实测）

## 1. 一句规则

以 HarmonyOS/OHOS 上**默认**的 `CMAKE_SYSTEM_NAME`（Conan 由 `os=OHOS` 映射出的
`HarmonyOS`，或原生探测得到的 `HarmonyOS`）配置 CMake 时，CMake 找不到
`Modules/Platform/HarmonyOS.cmake`，于是**只有一行 warning、退出码 0**，`UNIX` 等平台布尔
变量全部未定义；上游若用 `if(UNIX)` 守卫 POSIX 实现，**整份源文件被静默排除**（连带丢
`DT_SONAME`），产物"少了一整块 API"却编译链接全绿。应在 `generate()` 中显式把系统名设为平台
真名 `CMAKE_SYSTEM_NAME=OHOS`（SDK 随带 `Platform/OHOS.cmake`，内容为 `include(Platform/Linux)`）。
**诊断时必须逐个读守卫块**——不是所有"看起来像平台开关"的东西都在 `if(UNIX)` 内（见 §2 第 4 条）。

## 2. 机理链（每环有独立可复现证据）

1. **系统名来源**：Conan 的 OHOS profile 把 `os=OHOS` 映射为
   `CMAKE_SYSTEM_NAME=HarmonyOS`（`conan/tools/cmake/toolchain/blocks.py` 的
   `{"OHOS": "HarmonyOS"}`）；原生探测路径下 CMake 取 `CMAKE_HOST_SYSTEM_NAME`，本机
   `uname -s` 同样返回 `HarmonyOS`。两条路都落到同一个不存在的平台文件。
2. **平台模块缺失**：CMake 按 `Modules/Platform/<SYSTEM_NAME>.cmake` 查找。设备上
   hnp cmake 4.1.2 与 SDK cmake 3.28 都没有 `Platform/HarmonyOS.cmake`；存在
   `Platform/OHOS.cmake`，全文只有 `include(Platform/Linux)`，系统名不是 `OHOS` 时不生效。
3. **变量未定义**：平台文件不加载 → `UNIX`、
   `CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG`、`find_package(Threads)` 等由
   `Platform/Linux.cmake` 建立的语义全部缺失。CMake 仅打印
   `System is unknown to cmake, create: Platform/HarmonyOS.cmake`，**不是错误**。
   注意 **`CMAKE_DL_LIBS` 不在此列**：它由 `Platform/GNU.cmake` 兜底，实测破损配置下
   `build.ninja` 仍有 `LINK_LIBRARIES = -ldl`（正确配置多出的是 `-pthread`）——
   把它也算作"被 `UNIX` 守卫跳过"是错误归因。
4. **静默丢功能（含两个必须避开的误判）**：`libvpl/CMakeLists.txt` 的 `if(UNIX)` 块管的是
   `src/linux/mfxloader.cpp`（1.x 全量派发：MFXInit/MFXInitEx/MFXQueryVersion/…）、
   `MFX_MODULES_DIR` 定义与 `find_package(Threads)`；
   而 **`-Wl,--version-script=src/linux/libvpl.map` 在 `if(WIN32)` 的 `else()` 分支里**，
   破损配置下**仍然生效**。实测破损产物：
   - 仍带 `LIBVPL_2.0`/`LIBVPL_2.1` 版本节点（`MFXCreateConfig@@LIBVPL_2.0`），
   - 但导出符号只有 **7** 个（全是 2.x loader 入口），且 **无 `DT_SONAME`**。

   所以正确归因是：**丢失的是 `mfxloader.cpp`（52 个 1.x 符号）与 `DT_SONAME`**；
   version script 只是"仅覆盖存活的那 7 个符号"。把它写成"version script 被 `if(UNIX)` 跳过"
   是错误归因（本条目初稿即犯过，已更正）——诊断时用
   `grep -n -B3 -A3 'version-script' libvpl/CMakeLists.txt` 看到 `else()` 边界即可避免。
5. **暴露时点**：只有消费者链接这些符号时才会 `undefined reference`，或运行期才发现
   功能缺失；上游自带单测若只覆盖存活分支则**全绿**（libvpl 的 ctest 在两种配置下
   都是 1023 注册 / 0 失败 —— 它测的是存活的 2.x loader 面，1.x 面整体不存在）。

实测对照（同一份 libvpl 2.16.0 源码、同一工具链，只差系统名）：

| 判据 | `CMAKE_SYSTEM_NAME` 留空/HarmonyOS | `CMAKE_SYSTEM_NAME=OHOS` |
|---|---|---|
| `System is unknown to cmake` 警告 | 3 行 | 0 行 |
| `mfxloader` 在构建图中的引用数 | 0 | 3 |
| `nm -D --defined-only libvpl.so \| grep -c ' T '` | **7** | **59** |
| `MFXInit` 符号 | 不存在 | `T MFXInit@@LIBVPL_2.0` |
| version node | **有**（`LIBVPL_2.0`、`LIBVPL_2.1`，仅覆盖 7 个符号） | 有（覆盖 59 个符号） |
| `DT_SONAME` | 无 | `libvpl.so.2` |

## 3. 推荐修复（producer 侧，一行）

```python
# conanfile.py generate() / CMakeToolchain
if self.settings.os == "OHOS":
    tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
```

理由：`OHOS` 是平台真名，SDK 随带的 `Platform/OHOS.cmake` 即 `include(Platform/Linux)`，
一次选择同时补齐 `UNIX` / SONAME flag / Threads 语义；警告消失，
守卫分支入库、共享库带真实 `DT_SONAME`、version script 覆盖完整 API。平台身份真实，
不像"改名成 Linux"那样连带引入 Linux 专有语义。仓库内同口径先例：
`archives/d/demumble`（注释直接写明「SDK ships Platform/OHOS.cmake, so select that
canonical platform explicitly」）、`archives/d/dbus`。

## 4. fallback（诚实权衡）

- **`CMAKE_SYSTEM_NAME="Linux"`**：目标 cmake 没有 `Platform/OHOS.cmake`（纯上游 CMake）时的
  退路，仓库内最主流写法（100+ 配方）。代价：把平台**改名**成 Linux，会一并加载 Linux
  专有语义（对平台集成类工程可能引入 systemd/dbus/X11 等错误依赖），构建期身份与平台
  真实身份不一致。能用 `OHOS` 时优先用 `OHOS`。
- **扩守卫补丁**：向上游提 `if(UNIX OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")` 形态的补丁。
  代价：需维护补丁并随上游改版漂移，且必须符合 R8/P-PATCH-003（不得引入无实质逻辑的空壳）。

## 5. 反模式

1. **以"configure 通过 + build 通过"作为适配完成判据，不核对守卫分支是否进入构建图、
   不看产物导出符号**：本形态没有任何错误输出，只看日志必然误判。
   判据应固定为「构建图引用数 + 导出符号数 + SONAME」三项（**version node 不能当判据**：
   两种配置都有）。
2. **凭"关键字出现在同一文件/同一段落"就把某个构建动作归因为被平台开关跳过**：
   被测工程里 `if(UNIX)` / `if(WIN32)` 边界必须逐个读。实测反例就是 libvpl 的
   version script 在 `else()` 分支；错误归因会随草稿固化进知识库。
3. **为缺失的守卫分支补空壳 stub 让链接通过**（R8 / P-BUILD-001）：把"静默丢功能"
   变成"静默给错结果"，缺陷从链接期推迟到运行期。

## 6. 去重与关系

- **E092**（cmake-toolchain）：记录的是"CMake 不认识 HarmonyOS 平台 → configure 阶段
  失败或生成错误构建文件"，推荐方案给的是 `CMAKE_SYSTEM_NAME=Linux`。本条补的是**另一个
  后果面**：构建**全绿**、退出码 0，缺陷是"平台布尔变量（`UNIX`）未定义导致上游守卫实现被
  静默剔除 + `DT_SONAME` 丢失"，并把推荐方案校正为平台真名 `OHOS`（`Linux` 降为 fallback）。
- **E096**（cmake-cxx-standard-explicit）：同根因的"标准检测失败"后果面；本条是
  "守卫分支被排除"后果面，互补不重复。
- **`DRAFT-cmake-harmonyos-platform-soname-flag`**：同根因的"SONAME flag 未定义 → 路径形
  DT_NEEDED"后果面（链接产物缺陷）；本条的 `DT_SONAME` 丢失与它同源，但主面是
  "实现分支被排除 → API 静默缺失"，修复动作也不同（那条注入 SONAME flag，本条选择平台名）。

## 7. 原则挂钩

`P-BUILD-001`（平台限制必须降级而非绕过 —— 对应"禁止空壳 stub"反模式）、
`P-ENV-001`（优先使用构建系统原生机制 —— 对应"选平台真名而不是改名 hack"）。

## 8. 关联交付

- 本草稿与 `archives/l/libvpl/2.16.0/**` 属同一交付范围，随该适配 PR 一并提交。
- 路径 B 知识库扩展申请：Issue #3030
  （<https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/3030>）。
- 正式 E 编号由知识库主编审核后分配（本次取号 E577；E568 经复核已被
  `DRAFT-E568-mdp-*` / `E568-draft-D275` 占用，故改号）。

## 9. 五项质量门槛自检

1. 规则式标题 + 问题类 slug（无库名-版本命名；库名仅进 `source_event` 当案例）——✔
2. rec + 双 fallback（含诚实权衡）+ 2 条 forbid（reason + consequence，其中一条专门针对
   "凭关键字推断守卫边界"的误归因）——✔
3. `verification_cmd` 自包含（平台模块 ls、守卫 grep、**逐个读守卫块**、两种系统名对照
   configure、符号/SONAME 核对；新 shell 可跑，不引用本 run 日志路径）——✔
4. principles 挂钩（P-BUILD-001/P-ENV-001）、`affected_scope` 泛化句式、
   `similar_to` 链 E092/E096/soname 草稿——✔
5. 本 run 配额：仅此 1 条（libvpl 自身的 307 SKIP 归 notes.md，不另立条目）——✔
