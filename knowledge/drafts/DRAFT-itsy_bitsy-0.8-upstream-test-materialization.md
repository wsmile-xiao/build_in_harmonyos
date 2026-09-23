# itsy_bitsy 0.8：测试子模块物化与安装配置复制残留

> 路径 B 知识草稿；待官方审核后再决定是否提升为正式条目。

## 触发场景

`itsy_bitsy` 0.8 是 CMake `INTERFACE`/header-only C++ 库。GitHub 源码归档包含
`.gitmodules`，但 `vendor/range-v3` 和 `vendor/span-lite` 目录为空；上游测试的
`tests/CMakeLists.txt` 又直接把这两个目录加入 include path。仅解压主 tarball
会导致测试配置或编译缺头文件。

同一版本的 `cmake/itsy.bitsy-config.cmake.in` 还残留了 sol2 项目的
`sol2-targets.cmake`、`sol2` 目标和 `SOL2_*` 变量。主库构建可通过，但安装后
消费者执行 `find_package(itsy.bitsy)` 会在加载配置阶段失败，属于 header-only
包容易漏掉的“构建成功、消费失败”问题。

## 可复用方案

0. **build 期 Python 生成器必须与宿主 locale 解耦。** 上游 `single/single.py`
   在 build 阶段用 `os.popen('git describe --tags --abbrev=0').read()` 取版本戳，
   这条管道按**解释器从宿主 locale 推导的文本编码**解码。CI worker 上该编码是
   str-buffered 的（idna/punycode 一族），于是 `codecs.py` 的
   `self.buffer + input` 变成 `str + bytes`，抛
   `TypeError: can't concat str to bytes`，`make` 在 1% 就中止；而设备端同一份
   代码里 `locale.getpreferredencoding(False)` 恒为 `UTF-8`、`read()` 干净返回
   空串，本地全绿。凡是 build 期调用 Python 脚本（single header、 amalgamation、
   codegen）的包都可能踩同一坑。做法是在 `generate()` 用
   `conan.tools.env.Environment` 给 build 作用域 pin
   `PYTHONUTF8=1` + `PYTHONIOENCODING=utf-8`，让 make 派生的子 python 不再继承
   宿主 locale；不改上游源码、不加平台宏、不跳测试。判据：source 生成的
   `conanbuild.sh` 后 `locale.getpreferredencoding(False)` 必须是 `utf-8`。
1. 在 `conandata.yml` 固定测试依赖的官方 release tarball 和 SHA256。
2. 在 Conan `source()` 阶段将它们解压到上游期待的 `vendor/` 路径；`range-v3`
   只服务 upstream CTest，而 `span-lite` 同时作为 C++17 `bit_span` 的公共 Conan
   依赖；测试源码本身不复制进最终 package。
3. 用窄补丁修复安装配置：加载 `itsy.bitsy-targets.cmake`，为导出的
   `itsy.bitsy` 建立 `itsy::bitsy` alias，并提供对应的 `ITSY_BITSY_*` 变量。
4. 对 OHOS CMake toolchain 设置 `CMAKE_SYSTEM_NAME=Linux` 仅用于进入上游
   兼容 Unix 分支；对上游 `-Werror` 只记录并处理已复现的两个诊断：OHOS
   libc++ C++17 的 `allocator::construct` deprecated，以及
   `shared_allocator_tests.hpp:118` 的 unused-but-set-variable。

## 测试统计边界

本次上游 `tests/` 正式测试树注册并验证了 6 个 CTest 入口：两个 runtime
驱动、两个 compile-time 可执行和两个预期失败的 negative compile。两个 runtime
驱动各自报告 554 个 Catch2 逻辑用例和 3,640,828 条断言，因此逻辑用例执行数为
1,108。`examples/` 是独立的可选检查，启用时另有 14 个示例入口通过，完整配置
的 CTest 总数为 20；PR 的上游入口字段按正式 `tests/` 口径填写 6。Conan
`test_package` 另有 5 个安装后消费者 CTest 用例（27 条运行期断言 + 1 条
`static_assert`），统计时单独列出，也不与上游断言数混算。

## 与已有知识的差异

E092 已覆盖 CMake 不识别 HarmonyOS 的一般处理，E150 覆盖归档不含 submodule
内容，E301 覆盖 `CMake.test()` 的 `cli_args` 是构建参数而非 CTest 参数。
本草稿新增的是它们在 header-only Conan 包中的联合边界：测试依赖必须固定并
物化但不进入包；声明为公共依赖的头文件级依赖必须用负对照证明其必需性；
且必须同时审计安装配置中的复制残留——否则上游测试和主构建均可能通过，
实际消费者仍会失败。

另一个与 E301 相邻、但根因不同的新边界：`CMakeToolchain.cache_variables`
传入 Python `list`/`tuple` 时会按 Python repr 序列化进 CMake 缓存，于是
`CMAKE_CTEST_ARGUMENTS` 生成的 `make test` 规则变成
`ctest ['--output-on-failure']`，ctest 直接把字面量当参数处理（表现为
`Unknown argument` 类失败）。正确形态是普通字符串
`tc.cache_variables["CMAKE_CTEST_ARGUMENTS"] = "--output-on-failure"`；
CMake 需要的是分号分隔字符串，而不是 Python 容器。同时说明为何此处保留
build-system 的 `test` 目标而不用 `CMake.ctest()`：后者会注入
`--parallel <tools.build:jobs>`，在多核设备上放大并发，不符合按 -j2 控
并发的工作区约束。

## 公共依赖必需性的负对照

header-only 包最容易虚报依赖：只要测试没走到需要该依赖的头文件，删掉依赖
也照样"通过"。本次做法是给消费者测试单独放一个必然经过该依赖的用例，并做
一次负对照——只保留被测包头文件路径、去掉 span-lite 头路径后编译同一份
测试源码：

```text
include/itsy/detail/span.hpp:47:2: error: "Cannot use this feature:
a span of some sort is required! Please pull in the submodules or provide your own span on the include paths."
```

编译失败即证明 `span-lite` 是 `itsy/bit_span.hpp` 的真实公共依赖，而不是
顺手加上的可选装饰。

## 断言可失败性

5 个消费者 CTest 用例（27 条运行期断言 + 1 条 `static_assert`）逐条把期望值
改错后重跑，每一条都产生了带文件名/行号的真实失败（含 `static assertion
failed due to requirement ...` 与 `FAIL: <expr> (line N)`），随后复原并 5/5
通过，且复原前后测试源码 sha256 一致。这一轮取证与 CI 的 L1e 破坏产物目录
互补：L1e 只能证明"测试依赖被测包"，无法证明"每条断言都能失败"。

## 证据

- 上游原始失败：`include/itsy/detail/bit_detail.hpp` 的
  `allocator::construct<char16_t/char32_t>` deprecated 诊断；
  `include/itsy/tests/shared_allocator_tests.hpp:118` 的
  `index` unused-but-set-variable 诊断，均因上游测试 `-Werror` 失败。
- 设备端用窄诊断选项完成 `make -j2` 全量构建，`tests/` 正式 CTest `6/6` 通过；
  `examples/` 独立检查 `14/14` 通过（启用 examples 时完整 CTest 为 `20/20`）；两个
  runtime 驱动均为 `554` 用例 / `3640828` 断言，退出码 0。
- 错误使用相对 profile 路径时，Conan 会命中 `~/.conan2/profiles/` 下的同名
  残留副本（缺 `os.version`），首条真实错误为
  `ERROR: There are invalid packages: ... 'settings.os.version' value not defined`；
  改用与 CI 相同的绝对 profile 文件路径后消失。
- 安装后的消费者测试实际链接 `itsy::bitsy`，并调用 `bit_vector`、`count`、
  `flip`、`popcount` 与 `bit_span`（后者经 `nonstd::span.hpp`）。
