# magic_enum 0.9.8 适配笔记

## 库简介

Header-only C++17 静态反射库，为 enum 提供编译期反射能力（枚举名 ↔ 值互转、
遍历、计数等），无需任何宏或样板代码。零运行时依赖。

- 上游仓库：https://github.com/Neargye/magic_enum
- 版本标签：v0.9.8
- License：MIT

## 上游源码核验

| 项目 | 值 |
|------|-----|
| 源码 URL | https://github.com/Neargye/magic_enum/archive/refs/tags/v0.9.8.tar.gz |
| SHA-256 | `1e54959a3f3cb675938d858603ad69d0f3f7c82439fc2bf86d7232daec2bd10e` |
| C++ 标准 | C++17（README 明示；magic_enum.hpp 依赖 if constexpr / structured bindings） |
| 运行时依赖 | 无（header-only，零依赖） |
| License | MIT |

## include 目录结构（实测）

```
include/magic_enum/
├── magic_enum.hpp              # 主头（enum_name/enum_cast/enum_values/enum_count 等）
├── magic_enum_all.hpp          # 聚合头（包含下面所有）
├── magic_enum_containers.hpp
├── magic_enum_flags.hpp        # 位标志枚举支持
├── magic_enum_format.hpp
├── magic_enum_fuse.hpp
├── magic_enum_iostream.hpp     # operator<< / operator>>
├── magic_enum_switch.hpp
└── magic_enum_utility.hpp
```

共 9 个 `.hpp`。上游 CMakeLists.txt 定义 `INTERFACE` 库 + 别名
`magic_enum::magic_enum`（EXPORT_NAMESPACE = `${PROJECT_NAME}::`）。

## 关键构建选项

| 选项 | 说明 |
|------|------|
| package_type | header-library（无需编译，只打包头文件） |
| no_copy_source | True（header-only，源码不复制到 build 目录） |
| package_id | self.info.clear()（所有配置产出相同包） |
| BUILD_EXAMPLES / BUILD_TESTS | 不调用上游 CMake，无需设置 |

## 产物

- 头文件：`include/magic_enum/*.hpp`（9 个）
- LICENSE：`licenses/LICENSE`

## 验证

### 上游官方测试套件（真实执行）

上游 `test/` 目录共 6 个独立测试源文件，由 `test/CMakeLists.txt` 经
`make_test()` 注册为 ctest 目标，按编译器支持的 C++ 标准分组（cpp17 恒注册；
cpp20/23/cpplatest 条件注册）。在 OHOS aarch64 + clang 15.0.4 环境下：

- clang 15 支持 `-std=c++17` 与 `-std=c++20`，不支持 `-std=c++23`（需 `c++2b`，
  上游 CMake 的 `check_cxx_compiler_flag(-std=c++23)` 判定失败）。
- `test_nonascii.cpp` 受 `MAGIC_ENUM_OPT_ENABLE_NONASCII` 门控（默认 OFF），
  该文件用 emoji 枚举标识符 `U+1F603`（😃），需 C++23 P2174 词法支持，
  clang 15 / C++17 下编译报 `unexpected character <U+1F603>`，属真实环境限制。

上游测试目标统计（`ctest -N` 实测）：

| C++ 标准 | test | test_flags | test_aliases | test_containers | test_wchar_t | test_nonascii | 小计 |
|----------|------|-----------|--------------|-----------------|--------------|---------------|------|
| cpp17    | ✓    | ✓         | ✓            | ✓               | ✓            | — (门控关闭)   | 5    |
| cpp20    | ✓    | ✓         | ✓            | ✓               | ✓            | — (门控关闭)   | 5    |
| cpp23    | —    | —         | —            | —               | —            | —             | 0    |
| **合计** |      |           |              |                 |              |               | **10** |

实际执行（conan create build() → ctest --output-on-failure -j4）：

```
1/10 Test  #1: test-cpp17 .......................   Passed
2/10 Test  #2: test_flags-cpp17 .................   Passed
3/10 Test  #3: test_aliases-cpp17 ...............   Passed
4/10 Test  #4: test_containers-cpp17 ............   Passed
5/10 Test  #5: test_wchar_t-cpp17 ...............   Passed
6/10 Test  #6: test-cpp20 .......................   Passed
7/10 Test  #7: test_flags-cpp20 .................   Passed
8/10 Test  #8: test_aliases-cpp20 ...............   Passed
9/10 Test  #9: test_containers-cpp20 ............   Passed
10/10 Test #10: test_wchar_t-cpp20 ...............   Passed
100% tests passed, 0 tests failed out of 10
```

- 编译通过：10/10（测试目标）+ test_nonascii.cpp 编译失败（emoji 词法限制）
- 运行通过：10/10
- 跳过：test_nonascii（2 个潜在目标 cpp17/cpp20）因门控默认 OFF 未注册

### Conan 消费者测试（test_package）

test_package 真实测试 7 项 API 断言（非空壳）：
1. `magic_enum::enum_name(Color::GREEN)` 返回 "GREEN"
2. `magic_enum::enum_cast<Color>("RED")` 返回 Color::RED
3. `magic_enum::enum_cast<Color>("blue", case_insensitive)` 大小写不敏感
4. `magic_enum::enum_values<Color>()` 返回全部枚举值
5. `magic_enum::enum_count<Color>()` 等于 3
6. `magic_enum::enum_integer(Color::GREEN)` 返回底层整数值
7. `magic_enum::enum_name(Permission::Write)` 位标志枚举基础支持

每项用返回值与断言（不匹配则 `return 1`）验证，非仅 include + return 0。
`conan create` test 阶段实测输出 `PASS (7/7 assertions OK)`。

### recipe 调整说明（仅限 magic_enum 目录内）

`conanfile.py` 的 `build()` 新增上游测试集成：用 `subprocess` 调用 cmake/ninja
构建上游 `test/` 套件并经 `ctest` 执行。`can_run(self)` 守护运行阶段。唯一新增
编译选项 `-Wno-unused-command-line-argument` 仅用于抑制 OHOS clang++ 包装脚本
在 `-c` 编译阶段注入的无关链接器标志（`-Wl,--code-sign -fuse-ld=lld -L...`）
触发的 `-Werror` 误报——不触及任何测试源码、断言或语义。未删测试、未降断言、
未跳过失败用例。

### L1e 破坏性反向验证

CI 移除 `include/` 后 `conan test` 编译失败 → 证明测试真实依赖被测包。
