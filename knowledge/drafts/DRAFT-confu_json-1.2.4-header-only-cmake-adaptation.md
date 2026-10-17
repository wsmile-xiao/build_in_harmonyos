# DRAFT-confu_json-1.2.4-header-only-cmake-adaptation — 头文件-only CMake 库适配：compile_commands 复制目标守卫 + conan CMakeDeps 下 boost 头文件-only（SYSTEM include）消费

> 来源：confu_json 1.2.4 适配（R02，task confu_json-1.2.4-r02-pc2-18-20260922T052638Z）
> 环境：HarmonyOS PC aarch64，OHOS SDK clang 15.0.4 / libc++ 15，Conan 2.29.1（OHOS），CMake 4.1.2

## 错误特征

```
Error copying file ".../build/compile_commands.json" to ".../compile_commands.json".
make[2]: *** [CMakeFiles/copy_compile_commands_json.dir/build.make:73: .../compile_commands.json] Error 1
ld.lld: error: undefined symbol: init_unit_test()
>>> referenced by unit_test_main.cpp ... in archive .../libboost_unit_test_framework.a
```

（两个相互独立但常见于头文件库/测试构建的错误类别；本条目按同一适配场景合并记录。）

## 触发条件

- 构建系统：cmake（头文件-only / INTERFACE 目标）
- 阶段：build（make）与 link（测试目标）
- 触发点 1：无编译规则的库 + 上游无条件 `add_custom_target(copy_compile_commands_json ALL)` 复制
  `${CMAKE_BINARY_DIR}/compile_commands.json`（该文件根本不会生成）
- 触发点 2：conan CMakeDeps 消费 boost 且测试目标同时链接 `Catch2::Catch2WithMain`；
  上游 `Boost::headers` 目标名在 CONFIG 模式下不存在

## 根因分析

1. 头文件-only（INTERFACE）CMake 库没有任何编译规则，`compile_commands.json` 不会被生成；
   上游自定义目标无条件复制它 → 构建必然失败。这与 E074/E525（make -j1/FIFO）不同根因。
2. conan CMakeDeps 对 boost 只生成 `Boost::boost` 伞目标（INTERFACE，链接全部组件静态库，
   含自带 `main()` 的 `libboost_unit_test_framework.a`）；上游常用的 `Boost::headers`
   （find_package(Boost) MODULE 模式命名）在 CONFIG 模式下不存在。测试可执行同时链接
   Catch2 的 main 与 boost 的 main → 链接器冲突（undefined symbol: init_unit_test）。

## 解决方案

### 推荐方案
1. **守卫自定义目标**：`if (EXISTS ${CMAKE_BINARY_DIR}/compile_commands.json)` 包住
   `copy_compile_commands_json` 目标；有真实编译规则时行为不变。
2. **boost 头文件-only 消费**：不链接 `Boost::boost`；改为
   `target_include_directories(<lib> SYSTEM INTERFACE ${Boost_INCLUDE_DIRS})` 仅注入头文件目录；
   SYSTEM 同时豁免项目 `-Werror`（`-Wold-style-cast`/`-Wsign-conversion` 等）对 boost 头文件的拦截。
   boost::json 实现由测试 TU 内 `#include <boost/json/src.hpp>` 提供（header-only 模式）。
3. boost::mpl 依赖类型（`boost::mpl::at<...>::type`）在 clang15/libc++15 严格 C++20 下
   需显式 `typename`（P0634 不完整，与 DRAFT-332 同族）。

### 禁止做法
- ❌ 不守卫自定义目标而是删除它（破坏有编译规则时的正常行为）
- ❌ 链接 `Boost::boost` 后靠 `-Wl,--allow-multiple-definition` 掩盖 main 冲突
- ❌ 把 conan 包缓存的绝对路径硬编码进 INTERFACE include（不可复现）

## 验证

```bash
cmake -S <src> -B build -DBUILD_TESTS=OFF -DCMAKE_TOOLCHAIN_FILE=<conan>/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build -j1                      # 头文件库构建 exit 0
cmake --install build --prefix <prefix>      # 头文件安装正确
cmake -S <src> -B build-tests -DBUILD_TESTS=ON -DCMAKE_TOOLCHAIN_FILE=<conan>/conan_toolchain.cmake
cmake --build build-tests -j1 --target _test # 测试链接成功（无 init_unit_test 冲突）
cd build-tests/test && ./_test               # 47/47 通过（123 断言，exit 0）
```

实测：confu_json 1.2.4 按此修复后 conan create（干净构建）+ test_package 消费者用例全部通过。

## 关联条目

- 相关：E074/E525（make -j1/FIFO）、E035（Boost.Build/b2 header-only-install）、
  DRAFT-E998（boost 组件包拆分）、DRAFT-332（clang15 C++20 typename）
- 前置：conan CMakeDeps 的 boost 目标生成行为（工具链）
- 冲突：无
