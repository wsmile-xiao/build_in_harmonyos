# 知识库拓展：单体仓插件式子项目的三个共性适配点（探测模块 / 缺失 config 包 / 代次对齐）

> 样例演示库：`archives/i/indi-aok/2.0-20221222093242`（本目录即其知识库拓展产物，随该库适配同 PR 提交）
> 检测脚本：`detect-cmake-plugin-subproject.sh`　复现脚本：`reproduce.sh`　处理策略：`strategy.md`
> 相关草稿：`knowledge/drafts/DRAFT-<id>-indi-aok-*.kv`（待主编提升）

## 1. 一句话

上游把**几十个插件式子项目**放在一个单体仓里（indi-3rdparty 的 `indi-aok/`、`indi-eqmod/`…），
每个子项目都靠**仓库级 `../cmake_modules/`** 里的手写 `Find*.cmake` 找依赖，而这些依赖在鸿蒙
制品仓里是以 **conan 预编译包**形式提供的。于是出现三个连锁的共性适配点：

1. 手写模块的探测提示变量（`INDI_ROOT`）不会凭空存在 → `find_package(INDI COMPONENTS … REQUIRED)` 直接失败；
2. 某些 `find_package(<Name> REQUIRED)` 既无树内 `Find<Name>.cmake`、依赖包也不提供 `<Name>Config.cmake`
   （样例：`Nova`）→ 只能由配方在**构建目录内生成私有 config 包**兜住；
3. 子项目源码代次与制品仓可得的预编译依赖代次不匹配（样例：2.0 代驱动源码面向 libindi 1.9 API +
   C++14，而制品仓只有 libindi 2.2.2.1）→ 在「改被编译源码（R8 禁止）」与「对齐源码代次」之间必须做选择。

## 2. 识别条件（三条独立信号，命中任一条即需按对应策略处理）

1. **仓库级探测模块**：子项目 CMakeLists 里出现
   `LIST(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/../cmake_modules/")`
   或 `include(.../../cmake_modules/...)`，且被探测的依赖由 conan 提供。
   关键事实：conan 的 CMakeDeps 生成的 config 包名跟随**包名**（`libindi-config.cmake`），
   而 CMakeLists 请求的是**模块名**（`find_package(INDI)`），两者不互通；`find_package(INDI COMPONENTS driver lx200)`
   走的是模块模式，只会用树内 `FindINDI.cmake`。
2. **缺失的 config 包**：`find_package(<Name> REQUIRED)` 在源码树内无 `Find<Name>.cmake`，
   依赖包目录里也无 `<Name>Config.cmake` / `<name>-config.cmake`（样例 `Nova` 两条都不满足）。
3. **代次不匹配**：子项目声明的 `CMAKE_CXX_STANDARD` 低于依赖头文件要求（样例 libindi 2.2.2 的头用
   `std::any` ⇒ 需 C++17，2.0 代仓库级 `CMakeCommon.cmake` 仍是 14），或直接使用依赖已删除/降级的 API。

`detect-cmake-plugin-subproject.sh <源码目录>` 自动完成三步判定并打印证据行（命中时退出码 1）。

## 3. 为什么在鸿蒙 PC 适配中高频出现

- 制品仓**只提供预编译包**，不提供上游的手写 `Find*.cmake`；而单体仓的驱动子项目**不改用** config 模式
  （上游同时支持 Debian 打包与源码构建，选择了模块模式）。适配者若不注入提示，配置阶段即失败——
  错误信息是 "Could not find INDI include directory"，很容易被误判为「libindi 没有适配」。
- 依赖包由 conan 构建时，**不会**顺带产出上游发行版里的额外 cmake 文件（样例 libnova 只装
  `include/`、`lib/`，没有 `NovaConfig.cmake`），于是「驱动 required 的 config 包」只能由适配方补齐。
- 单体仓里的驱动是**插件式可执行文件**：由 INDI 主程序按需 `dlopen`（`share/indi/indi_aok.xml` 里登记），
  因此「编译通过」不等于「可运行」——运行期依赖闭包必须完整（样例：`libindilx200.so` 未声明
  `NEEDED libindidriver`，符号由后者提供），否则加载期报 `Error loading shared library libindidriver.so.2`。
- 与既有知识条目的方向不同：`DRAFT-libfli-findindi-version-regex-quoted-macro` 讲的是**同一个手写
  `FindINDI.cmake` 在解析带引号宏时的正则缺陷**（v2.2.2 代上游已修），`DRAFT-conan-popfront-module-path`
  讲的是 `CMAKE_MODULE_PATH` 的顺序问题；本条讲的是**模块模式依赖必须由配方注入提示 + 缺失 config 包
  由配方补齐 + 代次取舍**，属于配方层适配范式，故单列。

## 4. 处理策略

见 `strategy.md`，四条：

| 策略 | 适用信号 | 代价 |
|---|---|---|
| S1 注入探测提示（`INDI_ROOT=<依赖包目录>`） | 信号 1（样例采用） | 最小，不动任何源码 |
| S2 构建目录内生成私有 `<Name>Config.cmake`（路径全取 cpp_info） | 信号 2（样例采用） | 小，R49 合规（不注入共享前缀） |
| S3 源码代次对齐（取与预编译依赖同代的上游 ref） | 信号 3（样例采用） | 中，需在 notes.md 写明取舍与验证证据 |
| S4 改仓库级构建脚本（补丁） | 信号 3 的另一种解法 | 中，跨代维护成本高，仅当无法对齐代次时用 |

## 5. 复现与验证

```sh
# 检测（先判定是否命中；命中退出码 1）
sh detect-cmake-plugin-subproject.sh /path/to/src            detect.log

# 复现 + 验证（阶段 A 未处理 → 配置失败；阶段 B 按策略处理 → conan create 通过 + 运行期闭包校验）
sh reproduce.sh <含本归档的仓库根> "${TMPDIR:-/tmp}/indi-aok-repro" "${TMPDIR:-/tmp}/indi-aok-repro/logs"
```

`reproduce.sh` 全程把输出重定向到日志文件（不使用 `| head`，规避 SIGPIPE），并逐阶段打印退出码与关键
计数（`Found INDI` 行、`NovaConfig` 生成情况、`indi_lx200aok` 字节数、test_package 断言计数）。
脚本不写死本机路径、不依赖本地 conan 缓存（阶段 B 用 `conan create --build=missing` 全流程）。

## 6. 样例库实测数据（indi-aok 2.0-20221222093242，HarmonyOS PC aarch64 / clang 15 / CMake 4.1.2）

| 阶段 | 结果 |
|---|---|
| A1 未注入提示 | `find_package(INDI)` 报 "Could not find INDI include directory"（配置失败） |
| A2 注入 `INDI_ROOT` 后 | `Found INDI: …/libindidriver.so;…/libindilx200.so (found version "2.2.2")`；随后 `find_package(Nova REQUIRED)` 报无 `FindNova.cmake`/`NovaConfig.cmake`（配置失败） |
| A3 代次未对齐（2.0 代源码 + libindi 2.2.2.1） | libindi 属性 API/`std::any` 编译错误；仓库级 `CMakeCommon.cmake` 仍是 `CMAKE_CXX_STANDARD 14` |
| B 按 S1+S2+S3 处理 | `cmake configure rc=0`、`cmake --build rc=0`；产物 `bin/indi_lx200aok` 88576 B（AArch64 musl 动态 ELF）；`share/indi/indi_aok.xml` 登记 `<driver name="LX200 AOK">indi_lx200aok</driver>` |
| B 消费者校验 | `test_package` 4 项断言全过（ELF 架构 / XML 与 bin 交叉引用 / **DT_NEEDED 闭包静态审计** / 宿主加载器探针按平台限制记 SKIP）；移除 `bin/indi_lx200aok` 后判 FAIL（满足 L1e 破坏性验证） |
| 补丁数 | **1**（只改构建脚本 `indi-aok/CMakeLists.txt` 的组件列表，使 `libindiclient` 入 DT_NEEDED；被编译源码零改动，R8 合规） |

完整构建与测试结论见 `../reports/test-report.md`、决策取舍见 `../notes.md`。
