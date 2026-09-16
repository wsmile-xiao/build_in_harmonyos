# pytorch 2.13.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-02
- 编译器: clang 22.1.8 (tool_requires) + SDK libc++ 15 (__n1 ABI)
- 目标平台: HarmonyOS PC (aarch64), profile ohos-aarch64
- 状态: built

## 编译步骤
1. `conan create archives/p/pytorch/2.13.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=... --build=missing`
2. source() 从官方 tarball 解压，并按 pinned commit 补齐 37 个 third_party 子模块（本环境 codeload 被阻断，改用 gh-proxy.com 镜像）
3. CMake 配置：BUILD_PYTHON=OFF、USE_CUDA=OFF、USE_MKLDNN=OFF 等，产出 C++ libtorch
4. 编译 libtorch_cpu.so / libtorch.so / libc10.so + package + test_package 实质验证

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 37 个 third_party 子模块缺失 | GitHub release tarball 不含 git 子模块 | source() 按 pinned commit 从 codeload/gh-proxy.com 补齐 |
| 2 | pytorch 要求 Clang>=16，SDK 仅 clang 15 | CMakeLists 硬检查 | tool_requires clang/22.1.8，保留 SDK libc++15 |
| 3 | SONAME 缺失/版本化导致 musl 无法加载 | CMAKE_SYSTEM_NAME=HarmonyOS 不生成 SONAME | 改 OHOS + 不设 SOVERSION → 纯名 SONAME |
| 4 | HMDFS 上 cmake --install 的 .so 无法 mmap | HMDFS mmap(PROT_EXEC) 限制 | package() 从 build 目录复制 .so 覆盖 |
| 5 | codeload 被阻断 | 网络环境 | gh-proxy.com 镜像优先（codeload/ghfast 兜底） |

## 源码修改
- `patches/0001-pytorch-ohos-adapt.patch`: musl __assert_fail、std::ranges 兼容、CMake 4.x WHOLE_ARCHIVE（回退分支仅限 OHOS）等
- `patches/0002-cpuinfo-ohos.patch`: cpuinfo OHOS 平台匹配 + dumpmachine 兜底
- `patches/0003-sleef-ohos-aarch64.patch`: sleef AARCH64 交叉编译修正

### 关于 0001 中 `#if defined(__MUSL__)` 的 R8 例外说明

`torch/headeronly/macros/Macros.h` 在 `#if defined(NDEBUG)` 分支内**重新声明** `__assert_fail`，
必须与 C 库的声明逐参数一致，否则 clang 报
`error: exception specification in declaration does not match previous declaration`：

| libc | 声明 |
|------|------|
| glibc | `void __assert_fail(const char*, const char*, unsigned int, const char*) noexcept` |
| OHOS musl（`sysroot/usr/include/assert.h:19`） | `void __assert_fail (const char *, const char *, int, const char *);` |

两者在 `int` vs `unsigned int`、`noexcept` 与否上互斥，因此**必须**按 libc 分支，属
R8「无 POSIX 等价物场景」例外（预处理器无法对函数签名字符串做特性探测，也无
config.guess/config.sub 等价手段）。

- `__MUSL__` 由工具链注入而非依赖编译器内置：`ohos.toolchain.cmake:272/282/292` 与
  本配方 `conanfile.py:315/317` 的 `CMAKE_CXX_FLAGS` 均含 `-D__MUSL__`。
- 实测证据：去掉该条件后，真实 TU（`-O3 -DNDEBUG`）复现 CI 构建 #45180 的原错误；
  恢复后同批 TU 全部编译通过。

## 依赖版本
- clang/22.1.8 (tool_requires，已在 ohpcd)
- 无外部运行时 requires（third_party 子模块内置）

## 验证结果
```bash
test pytorch 2.13.0: OK (1+2+3 + 4+5+6 = 21.000000)
W3 本地 CI: Pass rate 100% (1/1)，L0/L1/L4/L5 PASS
```

## 上游测试
统计口径：C++ 为 gtest `TEST*/TEST_F/TEST_P/TYPED_TEST*` 宏计数，Python 为 `def test_*`；
运行时用例数为 gtest 实际执行数（含参数化实例化，故大于宏计数）。均对本仓库内
v2.13.0 源码树实测，脚本化可复现。

| 上游测试套件 | 文件数 | 用例数(宏) | 运行时用例 | 是否在本包执行 | 说明 |
|---|---|---|---|---|---|
| `c10/test`（核心工具库） | 51 | 669 | 868 | **是（全量）** | 仅依赖 libc10 + 上游 googletest，可同工具链编译后经 ctest 执行 |
| `test/cpp`（torch API/算子） | 198 | 2700 | - | 否 | 与完整 torch 目标同编译，单目标编译 30-60 分钟、全量运行数小时，超 CI 预算 |
| `test/*.py`（pytest） | 184 | 9926 | - | 否 | 本包 `BUILD_PYTHON=OFF`，只产出 C++ libtorch，无 python 版 torch 可测 |

**已执行的全量 c10 测试**（`conanfile.py build() -> _run_upstream_c10_tests()`）：
按与上游 `c10/test/CMakeLists.txt` 相同的 `file(GLOB_RECURSE ... *_test.cpp)` 口径
发现全部 **51 个目标**（50 个 `*_test` + `c10_cpp17_header_build_test`），
共 **868 个运行时用例**、**1802 条 `EXPECT_*/ASSERT_*` 断言**：

```bash
# build() 内自动执行：主构建完成后重新配置 BUILD_TEST=ON，构建全部 c10 测试目标
# 注意 INSTALL_TEST=OFF：BUILD_TEST=ON 会把 INSTALL_TEST 自动置 ON（cmake_dependent_option），
# 从而使 benchmark 等未构建二进制也生成 install 规则，导致 package() 的 cmake.install() 失败
cmake -S <source> -B <build> -DBUILD_TEST=ON -DINSTALL_TEST=OFF
cmake --build <build> --target <51 个 c10_* 目标> -- -jN
TMPDIR=<build>/upstream-test-tmp TEST_TMPDIR=<build>/upstream-test-tmp \
  ctest --test-dir <build> -R "^(c10_..._test)$" --output-on-failure
```

**本地实测（全量 51 目标）**：`51/51` 目标通过，868 用例中 **867 通过 + 1 skipped**，
**0 失败**；全部用例运行耗时约 4 秒。
skipped 的 1 例为 `ssizeTest.promotes_to_64_bit_on_32_bit_platform`（32 位平台专用，
64 位下按上游 gtest 逻辑跳过，非失败）。

**使全量通过所需的两个补丁**（`conandata.yml` 已登记，build() 阶段套用）：

| 补丁 | 目标 | 原因 |
|---|---|---|
| `0004-c10-enumerate-ssize-musl.patch` | `c10/util/Enumerate.h` | 使用 `ssize_t` 未 include `<sys/types.h>`；glibc 传递提供、musl 不提供 → `c10_Enumerate_test` 编译失败 |
| `0005-googletest-captured-stream-tmpdir.patch` | `third_party/googletest/.../gtest-port.cc` | CapturedStream 在非 Android/iOS 分支硬编码 `/tmp/`，HarmonyOS PC 的 `/tmp` 只读 → death test 全部 abort（`exception`/`logging`/`nofatal`/`small_vector`）。改用 `testing::TempDir()`（同上游 Android 分支机制，读 `TEST_TMPDIR`/`TMPDIR`，缺省回退 `/tmp`） |
| `0006-c10-test-targets-cxx20.patch` | `c10/test/CMakeLists.txt` | conan 工具链把 `CMAKE_CXX_STANDARD` 钉在 profile 的 17 且遮蔽 pytorch 顶层的 CACHE 赋值，而上游测试按 C++20 基线编写（`std::unordered_set`/`std::set` 的 `.contains`）→ `c10_DispatchKeySet_test`、`c10_ThreadLocalDebugInfo_test` 编译失败。仅对测试目标设 `CXX_STANDARD 20`，库目标保持工具链标准（避免全量重编） |

> 迭代记录：
> 1. 首轮接入 14 目标子集时 CI 报 `c10_exception_test` abort（`/tmp` 只读）→ 定位 gtest 硬编码路径问题（补丁 0005）；
> 2. 扩展为全量 51 目标后 CI 报 `c10_DispatchKeySet_test` 编译失败（`std::unordered_set::contains`）→
>    定位工具链 C++ 标准与上游测试基线不一致：conan 工具链按 profile `compiler.cppstd=17` 钉住 `CMAKE_CXX_STANDARD`，
>    遮蔽 pytorch 顶层的 CACHE 赋值，而上游测试按 C++20 编写（补丁 0006，仅作用于测试目标）；
> 3. 本机按 CI 同款工具链把 50 个 `*_test` 目标全部编译运行（C++17 下 2 例失败 → 用 CI 真实警告标志集在 C++20 下复检 50/50 通过），
>    最终全量 51 目标通过。
>
> 说明：`test_package/MANIFEST.yml` 记录了完整统计与执行明细；`test/cpp` 与 pytest
> 套件因编译量/python 绑定缺失未在本包执行，需要时可在 worker 上手动开启。

## 交付物
- libtorch.so / libtorch_cpu.so / libc10.so / libtorch_global_deps.so
- libtorch C++ API 头文件（include/torch 等）

## 注意事项
- 本包产出 C++ libtorch（判 cpp），非 python 包
- 子模块下载依赖镜像源，网络不稳定时有重试机制

---

**编译结束**: 2026-09-02
**最终状态**: built
