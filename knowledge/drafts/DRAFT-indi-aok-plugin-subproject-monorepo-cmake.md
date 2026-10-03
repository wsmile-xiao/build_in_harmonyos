# DRAFT-indi-aok-plugin-subproject-monorepo-cmake

> 草稿（待主编提升为正式 E 条目）
> 来源适配：`archives/i/indi-aok/2.0-20221222093242`（样例库，1 补丁＝仅改构建脚本的组件列表）
> 配套产物：`archives/i/indi-aok/2.0-20221222093242/knowledge-extension/{README.md,strategy.md,detect-cmake-plugin-subproject.sh,reproduce.sh}`
> 环境：HarmonyOS PC aarch64 / clang 15.0.4 / CMake 4.1.2 / libindi 2.2.2.1 / libnova 0.16

## 一句话

单体仓里的插件式子项目用仓库级手写 `Find*.cmake` 找依赖，而这些依赖在鸿蒙制品仓里是 conan
预编译包——于是出现三个连锁适配点：**探测提示须由配方注入**、**缺失的 finder 须由配方生成私有
config 包**、**源码代次须与预编译依赖对齐**；驱动类产物是插件式可执行文件，还须做**运行期闭包**校验。

## 命中场景（三条独立信号，任一条即应处理）

1. 子项目 CMakeLists 出现 `LIST(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake_modules/")`，
   且被 `find_package()` 请求的依赖由 conan 提供 → 需注入探测提示（S1）。
2. `find_package(<Name> REQUIRED)` 在源码树内无 `Find<Name>.cmake`，依赖包也不提供
   `<Name>Config.cmake`（样例 `Nova`）→ 需生成私有 config 包（S2）。
3. 子项目 `CMAKE_CXX_STANDARD` 低于依赖头文件要求，或直接引用依赖已删除的 API → 需代次对齐（S3）。

## 为什么会踩

- **模块模式与 config 模式互不回落**：`find_package(INDI COMPONENTS driver lx200)` 只认 `FindINDI.cmake`；
  conan CMakeDeps 生成的是按包名命名的 `libindi-config.cmake`，两者名字与查找机制都不同。
- **制品仓只给预编译包**：上游发行版里额外安装的 cmake 文件（如 `NovaConfig.cmake`）在 conan 包里没有。
- **代次错配**：制品仓只有一个可用代次；旧代源码面向更早的依赖 API，而 R8 禁止改被编译源码。
- **插件式可执行文件**：`bin/indi_lx200aok` 由 INDI 主程序按需 `dlopen`，`share/indi/indi_aok.xml` 登记；
  `libindilx200.so` 未声明 `NEEDED libindidriver`，符号由后者提供 → 闭包不完整时加载即失败。

## 推荐处理（详见样例库 `knowledge-extension/strategy.md`）

| 策略 | 做法 | 适用 |
|---|---|---|
| S1 | `tc.variables["INDI_ROOT"] = dependencies["libindi"].package_folder` | 信号 1 |
| S2 | `generators_folder` 内生成最小 `NovaConfig.cmake`（路径全取 cpp_info）+ `Nova_DIR` 指向它 | 信号 2 |
| S3 | 源码 ref 对齐同代上游 tag（v2.2.2，自带 C++17 / cmake_minimum_required 3.16） | 信号 3（首选） |
| S4 | 补丁改仓库级 `cmake_modules/*.cmake`（R8：只改构建脚本，不得引入平台宏） | 信号 3 的次选 |
| S5 | `test_package` 4 项断言：产物形态 / XML↔bin 交叉引用 / **DT_NEEDED 静态审计（确定性闸门）** / 宿主加载器探针（`env="conanrun"`，平台拒绝记 SKIP） | 插件式可执行文件 |

## 实测证据（indi-aok 2.0-20221222093242）

| 阶段 | 结果 |
|---|---|
| A1 未注入提示 | `find_package(INDI)` → "Could not find INDI include directory" |
| A2 注入 `INDI_ROOT` | `Found INDI: …/libindidriver.so;…/libindilx200.so (found version "2.2.2")` |
| A2' 未补 Nova | `find_package(Nova REQUIRED)` → 无 `FindNova.cmake` / `NovaConfig.cmake` |
| B 处理完毕 | configure rc=0、build rc=0；`bin/indi_lx200aok` 88576 B（AArch64 musl 动态 ELF） |
| B' 消费者校验 | test_package 4 断言全过（含 **DT_NEEDED 闭包静态审计**；宿主加载器探针按平台限制记 SKIP）；删除 `bin/indi_lx200aok` 后判 FAIL（L1e 反向验证） |
| B'' 补丁 | **1 个**（`0001-indi-aok-CMakeLists-link-indi-client.patch`：给 `find_package(INDI COMPONENTS …)` 补 `client` 组件，使 `libindiclient` 入 DT_NEEDED；只改构建脚本，R8/PF5 合规） |

## 与既有条目的关系

- `DRAFT-libfli-findindi-version-regex-quoted-macro`：同属 `FindINDI.cmake` 家族，但讲的是**版本正则**
  解析带引号宏的缺陷（v2.2.2 代上游已修）；本条讲**依赖探测提示与 finder 缺失的配方层补齐**。
- `DRAFT-conan-popfront-module-path`（`DRAFT-E5xx-conan-module-path-popfront`）：讲 `CMAKE_MODULE_PATH`
  的 `POP_FRONT` 顺序问题；本条不涉顺序，而是**模块模式缺少外部提示**。
