# Skill 草稿：Qt6 CMake 项目 + 非 Qt 第三方库混链的 OHOS Conan 适配模式

> 来源：qastools 1.4.0 适配（2026-09-19）。
> 适用场景：上游用 CMake 的 Qt6 项目，同时链接非 Qt 第三方库（alsa-lib、libudev 等），
> 且上游用裸 `SET()`/`TARGET_LINK_LIBRARIES( ... ${FOO_LIBRARIES} )` 管理依赖而非
> 现代 CMake target。目标平台 OHOS aarch64（musl）。

## 一类问题的定义

「Qt6 CMake 应用 + 非 Qt 库混链」在 Conan/OHOS 下的五个固定卡点：

1. **Qt 组件跨包分布**：qtbase 只带 Core/Gui/Widgets/Network/DBus，Svg 在 qtsvg 包、
   Tools 在 qttools 包……上游 `find_package(Qt6 REQUIRED COMPONENTS X)` 在 X 属于
   独立包时必然找不到。
2. **LinguistTools 工具链缺失**：制品仓 qtbase 变体普遍不构建 lupdate/lrelease，
   上游把 LinguistTools 设为 REQUIRED 时 configure 直接失败。
3. **头目录不向子目录传递**：顶层 `INCLUDE_DIRECTORIES` 不进入子目录 CMakeLists 的
   作用域；CMakeDeps 的导入 target 也无法替换上游裸 `SET()` 出的变量。
4. **子目录 `SET()` 覆盖顶层 cache 变量**：上游 `-DFOO_LIBRARIES=<绝对路径>` 被子目录
   `SET(FOO_LIBRARIES foo)` 覆盖回裸名，静态库/无搜索路径环境下链接必挂。
5. **musl 头链更短**：glibc 下靠间接包含的 STL 头（`<sstream>`、`<string>` 等）
   在 musl/libc++ 下变成显式缺失。

## 通用解法（按卡点编号）

| # | 卡点 | 通用解法 |
|---|------|---------|
| 1 | Qt 组件跨包 | conanfile `generate()` 把**每个** Qt 包目录拼进 `CMAKE_PREFIX_PATH`，并对每个组件设 `Qt6<Comp>_DIR=<包目录>/lib/cmake/Qt6<Comp>` 缓存变量 |
| 2 | LinguistTools 缺失 | 上游无运行时依赖 .qm（翻译运行时加载）时，patch 守卫 `FIND_PACKAGE(Qt6 QUIET COMPONENTS LinguistTools)`，缺失则跳过 i18n 子目录；若有编译期依赖（Q_INIT_RESOURCE 嵌 .qm）则必须先补建含 LinguistTools 的 qtbase 变体 |
| 3 | 头目录不传递 | 在顶层 CMakeLists `PROJECT()` 之后 patch 注入 `INCLUDE_DIRECTORIES(${X_INCLUDE_DIRS})`，值由 conanfile 通过 `tc.cache_variables` 传入绝对路径 |
| 4 | SET() 覆盖 | conanfile 改传 `FOO_LIBRARIES_CACHE=<绝对路径>`（避免被同名 SET 覆盖），patch 子目录 `IF(DEFINED FOO_LIBRARIES_CACHE) SET(FOO_LIBRARIES "${FOO_LIBRARIES_CACHE}") ELSE() SET(FOO_LIBRARIES foo) ENDIF()` |
| 5 | musl 短头链 | 报错头文件处显式 `#include`；无法自动化，按报错逐个补 |

## 验证命令（可复现）

```bash
# 修复前（复现 P2/P3/P4）：
conan create archives/q/qastools/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望首错序列：LinguistTools → Qt6Svg_DIR → libudev.h → undefined symbol: udev_new

# 修复后（验证通过）：
conan create archives/q/qastools/1.4.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# 期望：TP-001..006 全 PASS，日志 .ci_logs/target_qastools.log
```

## 迁移到同类库的检查清单

1. 上游 CMake 里 `find_package(Qt6 ... COMPONENTS <X>)` 的每个 `<X>`：查制品仓哪个包提供
   （`conan search` 包目录 `lib/cmake/Qt6<X>Config.cmake` 存在性）；
2. 上游是否 `find_package(Qt6 ... LinguistTools)`：制品仓 qtbase 变体均无 → 准备守卫 patch；
3. 上游依赖是否走裸 `SET()`（grep `SET (` + 大写下划线 + `_LIBRARIES`）：是则准备
   `_CACHE` 后缀 + 子目录守卫 patch；
4. 上游头文件依赖是否只在顶层 `INCLUDE_DIRECTORIES`：是则准备顶层注入 patch；
5. 编译报错里的 `implicit instantiation`/`undeclared identifier`：musl 补头文件。

## 对同类问题的影响

- **高**：kde 系、qt 应用系（qalculate-gtk、qbe 等 archives 中的 Qt 项目）、任何
  alsa+udev 混链的音频 GUI（如 alsamixer 系工具）。
- 与 E438 的关系：E438 解决「单 qtbase 包消费」，本模式扩展为「多 Qt 包目录 + 非 Qt 库
  裸 SET 混链」，是 E438 在真实应用层的必要扩展。
