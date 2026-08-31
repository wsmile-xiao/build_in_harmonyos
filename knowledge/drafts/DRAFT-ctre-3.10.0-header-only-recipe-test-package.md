# DRAFT-ctre-3.10.0-header-only-recipe-test-package — 编译期正则模板库 CTRE 的 Conan 配方与 test_package 落地要点

## 问题现象

header-only 模板库（CTRE，Compile Time Regular Expressions）在 OHOS armv8
上做 Conan 2.x 适配时，依次遇到四类非源码错误，全部与库本体无关：

```
# 1. 源码阶段：BadZipFile（与 E321 草稿重复，见查重差异）
conan.errors.ConanException: ... BadZipFile: File is not a zip file

# 2. 配方选择器错误：默认 profile 的 libstdc++11 不被 OHOS clang 15 接受
clang-15: error: invalid library name in argument '-stdlib=libstdc++'

# 3. test_package 生成器重复实例化
ConanException: CMakeToolchain is declared in the generators attribute,
but was instantiated in the generate() method too.

# 4. test_package 的 cmake.test() 无目标
make: *** No rule to make target 'test'.  Stop.
```

## 根因分析

1. **BadZipFile**：GitHub codeload URL 末段是 tag 名（`.../tar.gz/refs/tags/v3.10.0`）无
   `.tar.gz` 扩展名，Conan `get()` 无法推断压缩格式，默认按 zip 解压。→ 已在
   `E321-conan-get-url-no-extension-badzipfile.kv`（emojify/endlessh 实证）覆盖，
   本轮 ctre 采用相同修复（conandata `filename:` 声明），**不重复建条目**。
2. **libstdc++ 选择错误**：`default` profile 的 `compiler.libcxx=libstdc++11` 与 OHOS
   NDK clang 15（仅带 libc++）不兼容，CMake 编译器探测失败报
   `invalid library name in argument '-stdlib=libstdc++'`。header-only 库必须用
   仓库 `ohos-aarch64` profile（`libc++` + `tools.build:compiler_executables`）。
3. **CMakeToolchain 双重声明**：test_package 的 `generators` 里写 `CMakeToolchain`，
   `generate()` 里又手工 `CMakeToolchain(self)` → Conan 拒绝。只能二选一。
4. **CTest 目标缺失**：`cmake.test()` 实际跑 `cmake --build --target test`，若
   test_package 的 CMakeLists 未 `include(CTest)` + `add_test()`，没有 `test` 目标。

## 解决方案

- profile：header-only/纯模板库在 OHOS 一律用 `--profile:host=ohos-aarch64`
  （libc++、clang15、显式 compiler_executables），不要用默认 libstdc++ profile。
- conanfile.py：`package_type = "header-library"`，`package()` 只 copy
  `include/*.hpp` 与 LICENSE，`package_info()` 设 `cmake_file_name/ctre`、
  `cmake_target_name/ctre::ctre` 并清空 `bindirs/libdirs`。
- test_package/conanfile.py：`generators = "CMakeDeps"`（CMakeToolchain 只出现在
  generate() 一次）；test() 用 `cmake.test()`。
- test_package/CMakeLists.txt：必须 `include(CTest)` + `add_test()`。
- CTRE 特有：`fixed_string` 作非类型模板实参须 `static constexpr`（非 static 的
  局部 constexpr 无常量地址）；本版本无 `ctre::regex_options::multiline`，直接用
  `ctre::search<pattern>`。

## 验证证据

- 归档：`archives/c/ctre/3.10.0/`（conanfile.py + conandata.yml + test_package/）
- `conan create archives/c/ctre/3.10.0 --profile:host=ohos-aarch64 --profile:build=default --build=missing`
  → 退出码 0，test_package 1/1 通过（100% tests passed），日志
  `.build-cache/ctre/w3/conan-create-8.log`。
- 源码官方核验：tag `v3.10.0` commit `e34c26ba149b9fd9c34aa0f678e39739641a0d1e`，
  tarball SHA-256 `b17e6c9a6cc0cea65132f62a6c699cefed952721063569d6339eb3ca471045e6`。

## 适用边界

- 适用：C++17/20 header-only 模板库（纯头文件、无编译期产物、无外部依赖）。
- 不适用：需链接库/生成头/代码生成器/导出 CMake 目标做链接验证的库
  （链接型消费走 E307/E229 的编译期直接验证或普通 CMakeDeps）。
- 与 E035（boost b2 的 header-only-install）、E307（无 CMake 环境 compile-only）
  场景不同：本文档是 CMake 环境存在时 header-only 配方的完整落地模板。

## 查重结论

- BadZipFile / codeload 无扩展名 → 与 `E321` 草稿（emojify/endlessh）重复，
  本轮不新建条目，仅采用其推荐修复（filename 声明）。
- libc++ profile 选择、CMakeToolchain 双重声明、CTest test 目标注册、
  header-only 配方完整模板 → 知识库无对应正式条目（grep index.tsv 与 doc/ 无命中），
  本轮新建 DRAFT-ctre-3.10.0-header-only-recipe-test-package 沉淀可复用要点。

## R03 上游测试补充（同草稿内追加，2026-08-30）

R03 逐入口真实运行上游测试后，新增两项可复用发现（保持 .md/.kv 语义一致并重做查重）：

**补充 1 — 上游 hexdec>=0x80 编译期断言在 clang15 下失败**
- 现象：`tests/generating.cpp:56-58` 三处 static_assert
  `same_f(CTRE_GEN("\\x80"), ctre::character<char32_t{0x80}>())`（\xFF、\x{FF} 同）失败；
  `\x40/\x7F`（<0x80）通过；C++17 与 C++20 一致失败；CMake `--target ctre-test` 同。
- 根因：clang15 对 hexdec 转义值 >=0x80 的解析与 CTRE 3.10.0 生成器断言不符，
  属上游测试/编译器行为差异，非环境工具链缺项、非本库配方问题。
- 处置：不改动上游断言（任务边界），记录为该库上游测试首错；
  官方聚合 25 入口中该 1 项失败，其余 24 项通过。
- 查重：知识库无该精确模式条目，追加于本草稿 error_signature。

**补充 2 — 上游 benchmark 使用本版本头文件不存在的字面量操作符**
- 现象：`tests/benchmark/*.cpp`（same/unique/many-of-same-*）用
  `operator""_pcre`/`_pcre_test`，v3.10.0 `include/ctre/literals.hpp` 仅提供
  `_ctre`/`_ctre_test`/`_ctre_gen`/`_ctre_id`/_ctre_syntax（grep=0）。
- 根因：benchmark 文件与 3.10.0 头文件字面量 API 不匹配（上游库内文件年代差异）；
  `benchmark-exec/` 另缺 re2/re2.h、`benchmark-range/measurement.cpp` 缺 boost/regex.hpp。
- 处置：官方聚合入口（make/CMake ctre-test）均不含 benchmark 目录；
  该类入口记录为外部依赖阻塞，不进入 ctre 适配门禁统计。
- 查重：无既有条目，追加于本草稿 error_signature。

## R04 高位字节 hex 兼容性修复（同草稿内追加，2026-08-30）

R03 记录的 `tests/generating.cpp:56-58` 失败在 R04 定位到真实根因并完成最小修复，
25 项官方聚合三入口全部通过。本次追加为草稿的**完整结论版本**（R03 记录的行为差异
描述已升级为确定性根因+修复）。

### 真实根因（确定性）

- 位置：`include/ctre/actions/hexdec.inc.hpp` 的 `finish_hexdec` 动作。
- 缺陷：`constexpr size_t max_char = (std::numeric_limits<char>::max)();`
  用**平台相关的 char 符号性**决定 hexdec 转义值的类型归属。
- OHOS aarch64（AAPCS64）默认 `char` 为 **unsigned**（`__CHAR_UNSIGNED__=1`），
  `std::numeric_limits<char>::max() = 255`；x86-64 等 signed-char 平台为 127。
- `N <= max_char` 时产出 `character<char{N}>`，否则 `character<char32_t{N}>`：
  - aarch64 上 `\x80`(128)、`\xFF`(255)、`\x{FF}`(255) 全部 `<=255` → 误入
    `character<char{N}>` 分支，与上游断言期望的 `character<char32_t{N}>` 类型不符；
  - 而 `\x40/\x7F`(<128) 与 `\x{FFF}/\x{ABCD}`(>255) 不受影响 → 恰好仅 56-58 行失败，
    与 R03 实测完全吻合。
- 上游语义（generating.cpp:55 注释"only characters with value < 128 are char
  otherwise they are internally char32_t"）要求阈值恒定 128，与平台无关。

### 最小修复（补丁层，不改上游断言）

- 补丁：`archives/c/ctre/3.10.0/patches/0001-hexdec-char32-threshold-0x7f.patch`
  （`patch_type: portability`，SHA-256 `40326d784265e6a9b82865973148a276ee6be9a372847ebabce3bd3ccc7f2c6c`）。
- 改动：`max_char` 从 `std::numeric_limits<char>::max()` 固定为 `0x7F`（127），
  使 `>=0x80` 一律产出 `character<char32_t>`，与平台 char 符号性解耦。
- 接线：conandata.yml `patches:` 声明 + conanfile.py 已有 `apply_conandata_patches`，
  打包制品内头文件确认含修复（`max_char = 0x7F`）。
- 未改动任何上游测试断言、未禁用/排除测试。

### 验证证据（R04）

- 官方聚合三入口全部 25/25 通过（含 `tests/generating.cpp`）：
  - `make CXX=clang++ CXX_STANDARD=17 -k -j20`：exit 0，25 对象；日志
    `.build-cache/ctre/w3/r04-src/make-cxx17.log` SHA-256 `2a42205d...`
  - `make CXX=clang++ CXX_STANDARD=20 -k -j20`：exit 0，25 对象；日志
    `.build-cache/ctre/w3/r04-src/make-cxx20.log` SHA-256 `1796fe40...`
  - CMake `--target ctre-test`（C++20）：exit 0；日志
    `.build-cache/ctre/w3/r04-src/cmake-ctre-test.log` SHA-256 `cef1932b...`
- Conan/test_package：`conan create ... --profile:host=ohos-aarch64 --profile:build=default`
  exit 0，test_package 1/1 通过；日志 `.build-cache/ctre/w3/r04-conan-create.log`
  SHA-256 `5c291aac...`；Full reference `ctre/3.10.0#46a08f08...:6b129b06...`。
- 消费者验证：用打包制品 include 直接编译
  `ctll::front("\\x80"_ctre_gen)` 为 `character<char32_t{0x80}>`（std::is_same_v
  正向 3 项 + 反向退化 char 2 项均通过）；consumer5.cpp 编译 exit 0。

### 适用边界

- 适用：所有在 **unsigned-char 平台（aarch64/AArch64/OHOS、AAPCS64）** 上消费 CTRE
  `\xN`/`\x{N}` hexdec 转义（值 >=0x80）的工程；此修复是通用可迁移的 header 层改动。
- 不适用：signed-char 平台（x86-64/amd64）不受影响（原行为已符合断言，修复不改变其语义）；非 hexdec 的其他转义/字符类不涉及。
- 与 E321（BadZipFile/codeload）、E035/E229/E307（header-only 编译消费）正交。

### R04 查重结论

- 根因模式`(std::numeric_limits<char>::max)()`+hexdec>=0x80+unsigned-char 平台 →
  知识库 index.tsv 与 doc/ 无对应条目（grep 无命中，属新查重完成的追加内容）。
- 仍在既有同 stem 草稿内追加，未创建正式 `E###` 条目或索引。
