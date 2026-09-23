# ═══ Draft knowledge entry — OHOS/musl 下 CMake 动态插件系统须 SHARED + 显式链接依赖 ═══
# Timestamp: 2026-09-06
# Software: corrade 2020.06(含动态插件系统的 CMake C++ 库通用)
# Gate: conan create / 本地交叉编译 (build/link)
# Status: UNMATCHED — needs human/AI review to promote to E-entry

id: DRAFT-corrade-2020.06-ohos-cmake-plugin-shared-linking
severity: 2
category: platform|toolchain|cmake|linking
trigger_tool: clang|ld.lld|cmake
phase: linking|runtime

## 问题

HarmonyOS PC(aarch64)上编译 corrade 2020.06(BUILD_TESTS=ON)时:

1. **链接期**: OHOS 工具链在 `OHOS_COMMON_LINKER_FLAGS` 注入 `-Wl,--no-undefined`,
   测试插件 .so 引用 CorradePluginManager 的 `AbstractPlugin` 等符号,链接直接失败:
   ```
   ld.lld: error: undefined symbol: Corrade::PluginManager::AbstractPlugin::canBeDeleted()
   ```
2. **运行期**: 即使 `-Wl,-z,undefs` 放行链接,dlopen 插件时 musl 按 BIND_NOW 解析,
   插件 DT_NEEDED 无 CorradePluginManager → `Error relocating ...: symbol not found`。
3. **CMake 限制**: 插件间依赖(PitBull 继承 Dog)要求 MODULE 链接 MODULE,CMake 禁止。

## 根因

| 层 | 机制 |
|----|------|
| musl 加载器 | dlopen() 默认 BIND_NOW,要求符号加载即可解析;且符号查找范围仅自身 DT_NEEDED 链,不含主程序已加载库的全局作用域(与 glibc 不同) |
| OHOS 工具链 | `ohos.toolchain.cmake` 的 OHOS_COMMON_LINKER_FLAGS 注入 `-Wl,--no-undefined`(链接期拦截) |
| corrade 2020.06 | 非 Windows 平台插件用 `add_library(MODULE)` 且不链接依赖,依赖 glibc 全局符号作用域运行时解析 |

## 方案

1. **插件改 SHARED**: `corrade_add_plugin` 在 `CORRADE_TARGET_OHOS` 时 `add_library(SHARED)`
   (SHARED 可链接 SHARED,绕过 MODULE 限制)。
2. **显式链接依赖**: 测试插件 `target_link_libraries(... PRIVATE CorradePluginManager /
   CorradePluginManagerTestLib)`,插件间依赖(PitBull→Dog)同样显式链接。
3. **链接标志**: `-DCMAKE_SHARED_LINKER_FLAGS="-Wl,-z,undefs" -DCMAKE_MODULE_LINKER_FLAGS="-Wl,-z,undefs"`
   —— 注意 `--allow-shlib-undefined` **不能**覆盖 `--no-undefined`(实测仍失败),
   必须用 `-z undefs` 且位于命令中 `--no-undefined` 之后。

## 验证

- corrade 2020.06: 87 个 ctest 目标构建通过;PluginManagerManagerTest /
  PluginManagerManagerInitFiniTest 全部通过(修复前 2 个测试组失败)。
- 插件 NEEDED 核验: `llvm-readelf -d <plugin>.so | grep NEEDED` 包含 CorradePluginManager。

## 适用边界 / 反例

- **适用**: HarmonyOS/OHOS aarch64(musl)上含动态插件系统的 CMake C++ 库。
- **不适用**: glibc Linux(全局符号作用域,默认允许 .so 未定义符号,无需此改动);
  纯静态插件构建(Android 模式禁用动态插件时走另一分支)。
- **注意**: `-z undefs` 使 .so 可带未定义符号链接,但运行期仍须 DT_NEEDED 满足,
  否则 dlopen 报错——两步缺一不可。

## 查重差异

- `similar_to`: E004 / E078(musl BIND_NOW,Python/解释器扩展场景)、E442(libtool host-loaded
  plugin)——同属 musl 严格符号解析族;本条目为 CMake 插件系统的确定性修复
  (SHARED + 显式链接 + -z undefs),corrade 2020.06 实测通过。
- `caused_by`: musl BIND_NOW 语义 + OHOS 工具链默认 --no-undefined。
