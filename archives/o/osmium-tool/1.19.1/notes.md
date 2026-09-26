# osmium-tool 1.19.1 适配笔记

## 编译环境

- 构建系统：CMake（上游 CMake，`cmake_minimum_required 3.10`）
- 编译日期：2026-09-24
- 编译器：clang/clang++ 15.0.4（OHOS NDK，profile `ci/conan/profiles/ohos-aarch64`）
- CMake：4.1.2（`/data/service/hnp/bin/cmake`）
- Conan：2.29.1
- 状态：built

## W0 依赖发布检查（`conan download --only-recipe` / `conan list` 实测）

已发布（ohpcd）：
- boost/1.90.0.4（program_options 必需，`CMakeLists.txt:64` CONFIG 模式 REQUIRED）
- nlohmann-json/3.11.2（`command_export.cpp` 无条件 `#include <nlohmann/json.hpp>`）
- zlib/1.3.1.1.1、bzip2/1.0.8、expat/2.8.2.1、lz4/1.10.0

未满足：
- **libosmium**：ohpcd 只有 `libosmium/2.23.0`，而上游 `find_package(Osmium 2.23.1 REQUIRED)`
  要求 **>= 2.23.1**。两者差异不只是补丁号：2.23.1 回退了 2.21.0 引入的对象排序改动
  （`object_comparisons.hpp` 的 `object_order_type_id_reverse_version` 不再把 `visible()`
  纳入比较），该排序被 `osmium sort / apply-changes / merge-changes` 直接使用，
  用 2.23.0 头文件会产出错误结果 → **不能"降版本要求"绕过**，必须用 2.23.1。
- **protozero**：ohpcd 有 `protozero/1.8.2`，本可作为常规 `requires`；但 osmium-tool 通过
  自带 `cmake/FindProtozero.cmake` 以"兄弟目录/`PROTOZERO_INCLUDE_DIR`"方式查找，
  且 libosmium 已改为 vendored，为保持头文件版本一致，同样采用 vendored 方式固定
  protozero v1.8.2（需求为 >= 1.6.3）。

## W0b 历史经验核验

同软件无历史归档（`git ls-tree origin/main archives/o/osmium-tool` 空）。
同族先例：`archives/o/osmcoastline/2.5.0`（同为 osmcode 系、同一套 FindOsmium/FindProtozero
模块，采用"构建时下载 header-only 源码 + 缓存变量注入"策略），本库沿用其思路，
但把 vendored 源改到 `source()` 阶段下载（固定 sha256、写入 conandata.yml），
比在 `build()` 里硬编码镜像 URL 更干净。

## 语言预检（R47）

C++ 主体（src/ 全部 .cpp/.hpp），与任务声明语言 cpp 一致。

## 配方要点

- `package_type = "application"`；产物 `bin/osmium`。
- `requires`：boost/1.90.0.4、nlohmann-json/3.11.2、zlib/1.3.1.1.1、bzip2/1.0.8、
  expat/2.8.2.1、lz4/1.10.0。
- vendored（`source()` 下载，`conandata.yml: vendored:` 声明官方 URL + sha256）：
  libosmium v2.23.1、protozero v1.8.2 → 解压到 `<source>/vendor/<name>`，
  经 `OSMIUM_INCLUDE_DIR` / `PROTOZERO_INCLUDE_DIR` 注入。
- C++ 标准：`USE_CPP_VERSION=17`（与 profile `compiler.cppstd=17` 对齐，上游默认也是 17）。
- `WITH_LZ4=ON`（上游默认），PBF 支持 zlib+lz4（`osmium --version` 实测输出
  `Supported PBF compression types: none zlib lz4`）。

## 遇到的问题与解决（最终实测）

1. **`find_package(Osmium)` 报 `Could NOT find Osmium (missing: BZIP2_FOUND)`**
   根因：CMake 4.x 的 `FindBZip2` 只设置混合大小写的 `BZip2_FOUND`，上游
   `cmake/FindOsmium.cmake`（XML 组件）仍检查旧式 `BZIP2_FOUND`。
   解决：补丁 `0001-cmake4-findbzip2-compat.patch`（在 `find_package(BZip2)` 后加
   兼容别名，保留真实探测结果）。同款修法见已合入的 `osm2pgsql/2.3.1` 补丁 0002。

2. **编译 `lz4.hpp: fatal error: 'lz4.h' file not found`（其他依赖头文件都正常）**
   根因：Conan 工具链（`conan_toolchain.cmake`）默认
   `set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)`，于是 `find_package(LZ4/ZLIB/EXPAT/BZip2)`
   都走 CMakeDeps 生成的 `*-config.cmake`（只设置**小写**变量与 imported target），
   上游却读取**大写**旧式变量：`FindOsmium` 里 `${ZLIB_INCLUDE_DIR}` 仍是缓存变量
   （我们注入了）所以 zlib 能找到，但 `${LZ4_INCLUDE_DIRS}` 与 `${LZ4_LIBRARIES}`
   由 `FindLZ4.cmake` 在 LZ4_FOUND 时才设置，CONFIG 模式下为空。
   解决：在 `generate()` 中显式注入 `ZLIB_LIBRARIES`、`LZ4_INCLUDE_DIRS`、
   `LZ4_LIBRARIES`（以及 EXPAT/BZIP2 的复数变量）。

3. **`cmake --install` 会让产物不可加载**（OHOS `.codesign` fs-verity 哈希失效）
   解决：`package()` 不调用 install，直接字节复制构建树中的 `src/osmium` 到 `bin/`
   （与 osmcoastline 同款处理）。

4. **test_package 里 `osmium` 一律 rc=127**
   两层原因：①自定义 `run()` 函数把日志路径也当成命令参数传入（`timeout 60 <log> osmium ...`）；
   ②expat 是共享库，运行需 `conanrun` 的 `LD_LIBRARY_PATH`。
   解决：修正 `run()` 的参数处理；`test()` 以 `env="conanrun"` 执行 `test.sh`。

5. **`osmium tags-filter` 无 `-o` 时退出码 2**
   （不是缺陷）该子命令要求显式输出文件，测试改为 `-f opl -o filtered.opl`。

## 上游测试账本（实测）

- 命令：`ctest --output-on-failure`（配方 `build()` 内执行，cwd = CMake 构建根）
- 注册数（`ctest -N` 实测）：**375**
  - `unit_tests`：1（Catch2，源码 83 个 `TEST_CASE` 聚合为 1 个 CTest 用例）
  - `help_cmd_*`：23（23 个子命令的 `-h` 用法断言）
  - 其余 351：各子命令端到端输出比对（`cmake/run_test_compare_output.cmake`，
    调用构建出的 `osmium` 与 `test/` 下参考文件逐字节比对；含 formats 组 PBF 二进制比对）
- 实测结果：`100% tests passed, 0 tests failed out of 375` → **375/375 通过**，
  `RUN_TESTS_WITH_BINARY_COMPARE` 保持上游默认 ON 亦全过。
- 未执行项：无（`WITH_EXTRA_TESTS` 上游默认 OFF 的 `testinstall` 不计入）。

## 消费者测试（test_package）

`test_package/test.sh` 共 **18 项断言**（全部通过）：
版本契约（`osmium version 1.19.1`）/ `--help` 列出 COMMANDS / `cat -h` 用法 /
XML→OPL（node/way/tag）/ XML→PBF / `fileinfo -e` 读回节点与 way 计数 /
PBF→OPL 与 XML→OPL 逐字节一致 / `tags-filter w/highway` 过滤语义。

## 已知限制

- expat 制品为共享库（`libexpat.so.1`），因此 `bin/osmium` 运行期需要
  `LD_LIBRARY_PATH` 指向 expat 包（`conanrun` 环境提供）。CI 的 L2 冒烟在
  无 conanrun 环境下直接执行 `bin/osmium --version` 会加载失败（非阻塞），
  真实可用性由 `test_package`（conanrun）验证。
- 上游 man 手册需要 pandoc 生成（本环境/CI 无 pandoc），因此不随包安装；
  `osmium --help` / `osmium <cmd> -h` 等内置用法输出不受影响。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/osmium | 命令行工具（23 个子命令）|
| licenses/LICENSE.txt | GPL-3.0-or-later |

## 验证结果

- 本地 `conan create`：rc=0（G2 干净构建通过）
- 上游测试：375/375 通过
- 消费者测试：18/18 通过
- 补丁：`patches/0001-cmake4-findbzip2-compat.patch`（portability，无平台宏）
