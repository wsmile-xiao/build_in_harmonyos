# corrade 2020.06 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-06
- 编译器: OHOS SDK clang 15.0.4 (target aarch64-linux-ohos), OHOS SDK 26.0.0.18
- 状态: built

## 编译步骤

1. 下载官方源码: `https://github.com/mosra/corrade/archive/refs/tags/v2020.06.tar.gz`
   SHA-256: `2a62492ccc717422b72f2596a3e1a6a105b9574aa9467917f12d19ef3aab1341`
2. 宿主工具 corrade-rc: 先用打补丁后的源码在宿主机编译 corrade-rc
   (本机即 HarmonyOS aarch64, 宿主=目标平台)
3. 交叉配置(关键参数):
   ```bash
   cmake -S corrade-2020.06.work -B corrade-2020.06.build \
     -DCMAKE_TOOLCHAIN_FILE=$OHOS_SDK/ohos/native/build/cmake/ohos.toolchain.cmake \
     -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
     -DCMAKE_BUILD_TYPE=Release \
     -DBUILD_TESTS=ON \
     -DWITH_INTERCONNECT=ON -DWITH_PLUGINMANAGER=ON -DWITH_TESTSUITE=ON \
     -DWITH_UTILITY=ON -DWITH_MAIN=ON -DBUILD_DEPRECATED=ON \
     -DCORRADE_RC_EXECUTABLE=<宿主 corrade-rc 绝对路径> \
     -DCMAKE_SHARED_LINKER_FLAGS="-Wl,-z,undefs" \
     -DCMAKE_MODULE_LINKER_FLAGS="-Wl,-z,undefs" \
     -DCMAKE_RANLIB=<llvm-ar s 包装脚本> \
     -DCMAKE_INSTALL_PREFIX=<前缀>
   cmake --build corrade-2020.06.build -j4
   ```
4. 运行测试: `ctest` (在构建目录)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `CORRADE_TARGET_UNIX` 未定义, `readlink` 未声明 | CMake 将本机识别为 HarmonyOS, corrade 2020.06 的 `elseif(UNIX)` 不认 OHOS/HarmonyOS, configure.h 未定义 UNIX 宏, unistd.h 未包含 | 补丁 0001: 平台判定增加 `CMAKE_SYSTEM_NAME STREQUAL "OHOS"/"HarmonyOS"`, 并定义 `CORRADE_TARGET_OHOS`; 补丁 0011: configure.h.cmake 增加宏声明 |
| 2 | CMake 4.1.2 报 "Compatibility with CMake < 3.5 has been removed" | 新 CMake 移除旧版策略兼容 | 配置时加 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 3 | 交叉编译找不到 corrade-rc | corrade 交叉编译需要宿主 corrade-rc 工具 | 先用补丁后源码在宿主构建 corrade-rc, 用 `-DCORRADE_RC_EXECUTABLE` 传入 |
| 4 | 动态插件链接失败: undefined symbol (AbstractPlugin 等) | OHOS 工具链默认 `-Wl,--no-undefined`; musl 加载器 dlopen 插件只能从自身 DT_NEEDED 链解析符号, 而 corrade 插件未链接依赖 | 补丁 0002: OHOS 插件用 SHARED 而非 MODULE; 补丁 0003-0010: 测试插件显式链接 CorradePluginManager/TestLib 及插件间依赖; 链接标志 `-Wl,-z,undefs` |
| 5 | llvm-ranlib 不存在 | OHOS SDK llvm/bin 未提供 llvm-ranlib | 用 `llvm-ar s` 包装脚本作为 `-DCMAKE_RANLIB` |
| 6 | 静态库链接 "no such file or directory" | 同上 (llvm-ranlib 缺失导致 cmake_link_script 失败) | 同上 |
| 7 | UtilityDirectoryTest 7 项失败 | OHOS 平台环境差异: `/tmp` 只读、`/sys/devices/.../scaling_governor` 不存在、配置目录布局不同、corrade-rc 未部署到 bin | 记录为平台差异 (见测试台账), 不影响库本身功能 |

## 源码修改

补丁 11 个 (archives/c/corrade/2020.06/patches/):
- 0001-CMakeLists.txt.patch: OHOS/HarmonyOS 平台识别 + CORRADE_TARGET_OHOS
- 0002-modules-UseCorrade.cmake.patch: OHOS 插件 SHARED
- 0003-0010: PluginManager 测试插件依赖链接 (animals/custom-suffix/deletable/disabled-metadata/doggo/food/init-fini/wrong-metadata)
- 0011-src-Corrade-configure.h.cmake.patch: 宏声明

## 测试台账 (双口径)

### 口径一: 源码声明总数 (source_declared_total)
按可复制规则: 枚举 `src/Corrade/**/Test/*.cpp` 中 `addTests({ ... })` 注册条目数。

| 模块 | 声明用例数 |
|------|-----------|
| Containers | 556 |
| Interconnect | 32 |
| PluginManager | 59 |
| TestSuite | 93 |
| Utility | 441 |
| **合计** | **1181** (79 个测试源文件) |

### 口径二: 当前配置可执行注册数 (configured_executable_total)
ctest 注册 87 个测试目标 (84 个独立可执行文件 + 3 个子目标); 运行时 "with N test cases" 注册用例总数: 1571。
(与源码 1181 的差异: 同一测试源文件被编译进多个目标, 如 CppStandardTest.cpp 编译为 Cpp11/14/17/2a 等多个可执行, 每目标各自注册。)

### 执行结果 (ctest 权威口径)
- 87/87 目标全部运行
- 86 通过, 1 失败 (UtilityDirectoryTest)
- 用例级: 1571 注册用例, 1564 通过, 7 失败 (均属 UtilityDirectoryTest)

### 失败用例明细 (UtilityDirectoryTest, 7 项, 均为 OHOS 平台环境差异, 非库缺陷)
| 用例 | 原因 |
|------|------|
| executableLocation | 期望可执行文件旁有 corrade-rc 工具 (宿主工具未部署到测试 bin) |
| configurationDir | OHOS 配置目录为 /data/storage/el2/base/haps/entry/files/corrade, 无 autostart/dconf/Trolltech.conf |
| tmp | Directory::tmp() 返回 /tmp, 该路径只读 |
| fileSizeNonSeekable | /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 不存在 |
| fileSizeEarlyEof | 同上 |
| readNonSeekable | 同上 |
| readEarlyEof | 同上 |

全量通过率: 1564/1571 (99.55%); 当前配置可执行集合通过率: 86/87 (98.85%)。
注: 7 项失败均为平台环境 (只读 /tmp、无 sysfs cpufreq、OHOS 目录布局、工具部署位置), 在标准 Linux 桌面环境不存在, 属可接受平台差异, 记录为 quality_warnings。

## 依赖版本
- 无强制外部依赖 (corrade 基础库); 测试可选 SDL/EGL 未启用
- 工具链: OHOS SDK 26.0.0.18, clang 15.0.4, CMake 4.1.2, ninja/make

## 验证结果

```bash
cd corrade-2020.06.build
ctest   # 86/87 通过, 仅 UtilityDirectoryTest 因平台环境差异失败 7 检查项
```

## 注意事项
- OHOS (musl 加载器) 下动态插件必须显式链接依赖, 与 Linux/glibc 的运行时符号解析不同
- `-Wl,-z,undefs` 用于允许测试插件的跨库符号; 库本体使用默认链接
- corrade-rc 宿主工具构建后需要随 `CORRADE_RC_EXECUTABLE` 传入

## 知识候选台账 (knowledge_candidate_ledger)

### 候选 1: OHOS/musl 下 CMake 动态插件系统须 SHARED + 显式链接依赖 (核心候选)
- 真实错误: `ld.lld: error: undefined symbol: Corrade::PluginManager::AbstractPlugin::canBeDeleted()`; 运行期 `Error relocating InitFiniDynamic.so: ... symbol not found`
- 根因: musl dlopen 默认 BIND_NOW, 符号查找范围仅插件自身 DT_NEEDED 链(不含主程序已加载库的全局作用域); OHOS 工具链注入 `-Wl,--no-undefined`; corrade 插件用 MODULE 且不链接依赖
- 修复: 插件改 SHARED (corrade_add_plugin 在 CORRADE_TARGET_OHOS 下 add_library(SHARED)) + 显式 target_link_libraries 依赖 + `-Wl,-z,undefs`(注意 `--allow-shlib-undefined` 不能覆盖 `--no-undefined`,须用 `-z undefs`)
- 验证: 87 个 ctest 目标构建通过, PluginManagerManagerTest / PluginManagerManagerInitFiniTest 全过
- 适用范围: HarmonyOS/OHOS aarch64 上含动态插件系统的 CMake C++ 库; 不适用 glibc Linux
- 四范围查重:
  - 正式知识 (graph/E*.kv): E004/E078(musl BIND_NOW, Python 扩展场景)、E442(libtool host-loaded plugin)——同属 musl 严格符号解析族, 但场景与修复机制不同(CMake SHARED + 显式链接 + -z undefs)
  - 知识 doc (doc/E*.md): E004/E078/E442 配套文档, 均未覆盖 CMake 插件系统场景
  - 图谱 (index.tsv): 无 corrade/CMake 插件 SHARED 链接条目
  - 草稿 (drafts/): 无对应草稿 (DRAFT-E321 仅覆盖 CMAKE_POLICY_VERSION_MINIMUM)
- 七轴: exact_duplicate=no, causal_duplicate=no(机制同源 E004/E078 但对象/修复不同), trigger_overlap=partial(同为 symbol not found), solution_overlap=no(SHARED+显式链接是新方案), combination_novelty=yes(CMake 插件系统 + musl + OHOS 工具链 --no-undefined 三因素组合), boundary_novelty=yes(C++/CMake 插件 vs Python/libtool), test_migration_novelty=yes(PluginManager 测试组修复前后对比)
- 关系: similar_to=E004,E078,E442; caused_by=musl BIND_NOW + OHOS 工具链默认 --no-undefined

### 候选 2: CMake 4.x 拒绝 <3.5 的 cmake_minimum_required
- 真实错误: `Compatibility with CMake < 3.5 has been removed`
- 修复: conanfile generate() 用 `tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"`
- 查重: DRAFT-E321 (etcd-cpp-apiv3 0.15.4) 已完整覆盖同根因同方案 → **exact_duplicate=yes, reuse_existing=DRAFT-E321**, 不另建草稿

### 候选 3: OHOS SDK llvm/bin 缺 llvm-ranlib
- 真实错误: `llvm-ranlib: inaccessible or not found` (静态库链接失败)
- 修复: 用 `llvm-ar s` 包装脚本作为 CMAKE_RANLIB
- 查重: E385(aws-lc-sys, OHOS cmake toolchain CMAKE_RANLIB=llvm-ar s)已覆盖同方案 → **solution_overlap=yes**, 复用 E385 方案, 不另建草稿 (corrade 为纯 CMake 场景, 与 E385 的 cargo build.rs 场景同方案)

### 候选 4: CMake 平台识别不认 OHOS/HarmonyOS (elseif(UNIX) 分支)
- 真实错误: CORRADE_TARGET_UNIX 未定义 → readlink 未声明
- 修复: CMakeLists 平台判定增加 `CMAKE_SYSTEM_NAME STREQUAL "OHOS"/"HarmonyOS"` 并定义 CORRADE_TARGET_OHOS
- 查重: E092(CMake 不识别 HarmonyOS 平台, 方案为 -DCMAKE_SYSTEM_NAME=Linux toolchain 覆盖)部分覆盖 → trigger_overlap=yes, solution_overlap=partial(E092 走 toolchain 覆盖, 本轮为项目内 CMakeLists 平台判定扩展), boundary_novelty=yes(项目内平台宏判定 vs CMake toolchain 覆盖); 归入候选 1 的 corrade 草稿适用边界, 不另建草稿

### 路径决定
- **new_draft**: DRAFT-corrade-2020.06-ohos-cmake-plugin-shared-linking (.kv/.md 配对已建立, graph validate 通过)
- 本任务为【知识库扩展】路径 B: 候选 1 已验证、可跨库复用、查重为未命中且存在新增差异 → 建草稿; 候选 2/3 完整重复或方案重叠 → 复用既有条目 (DRAFT-E321, E385); 候选 4 归入草稿适用边界
- reuse_existing: DRAFT-E321 (CMAKE_POLICY_VERSION_MINIMUM), E385 (llvm-ar s wrapper)
- new_draft: DRAFT-corrade-2020.06-ohos-cmake-plugin-shared-linking
---

**编译结束**: 2026-09-07 00:35
**最终状态**: built

## R03 适配记录: Directory::tmp() 临时目录适配 (0013-src-Corrade-Utility-Directory.cpp.patch)

### 问题
OHOS 上 /tmp 为 erofs 只读挂载, UtilityDirectoryTest tmp() 用例失败 (can't open /tmp/a)。

### 适配
Directory::tmp() 在 CORRADE_TARGET_OHOS 分支:
1. 优先返回 `std::getenv("TMPDIR")`(如已设置且指向可写目录)
2. 其次返回 `join(std::getenv("HOME"), "tmp")`
3. 均不可用时回退原始 `/tmp`
其他平台 (APPLE sandbox/ANDROID/Windows/其他 Unix) 行为完全不变。

### 临时目录选择优先级
$TMPDIR → $HOME/tmp → /tmp (仅 OHOS; 其他平台仍为 /tmp 或平台既有逻辑)

### 适用边界 / 反例
- 适用: HarmonyOS/OHOS aarch64, /tmp 只读 (erofs), 存在可写 $TMPDIR 或 $HOME 的场景
- 反例/限制: $TMPDIR 指向只读路径时仍会失败(本实现不做可写性探测, 遵循环境变量约定);
  $TMPDIR 未设置且 HOME 未设置时回退 /tmp (OHOS 上仍只读); 非 OHOS Unix 平台不受影响 (无 CORRADE_TARGET_OHOS 宏)

### 验证
- 修复前: tmp() FAIL [36] (can't open /tmp/a), 7 errors out of 222 checks, exit=1
- 修复后: tmp() OK [36], 6 errors out of 223 checks, exit=1 (剩余 6 项均为任务明确不得改变的其他平台限制: sysfs scaling_governor/OHOS 配置目录/corrade-rc 未部署)
- 日志: r03_rerun.log (SHA-256 7f18b4549dcda964544c6faab5e108a143da5a83b8db93c5c4e1827614382f65), r03_utility_directory_test_full.log (SHA-256 b8f4d077d55d4cf79008a4697cdc5f15346741f72914d02e5d5d720ac0ee6ff2)
- 命令/cwd: ./Release/bin/UtilityDirectoryTest @ /storage/Users/currentUser/tmp/builds/corrade-2020.06.build, exit=1

### 原子性复核
- diff 仅限 archives/c/corrade/2020.06/: conandata.yml + manifest.yaml (补丁清单 13→14) + 新增 0013 Directory.cpp 补丁 + 0013→0014 configure.h.cmake 补丁纯重命名 (SHA-256 一致 b987234b...)
- 其他库/框架/知识正式条目/索引改动数: 0
- 本轮未 commit/push/PR/rebuild (任务不授权), HEAD 仍为 R01 commit 1cc07ee100
