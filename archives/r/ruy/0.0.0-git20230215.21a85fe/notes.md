# ruy 0.0.0-git20230215.21a85fe 适配笔记

> 任务：`ruy` ｜ 版本 `0.0.0-git20230215.21a85fe` ｜ 路径 A 基础适配
> 构建系统：CMake（自研规则函数，由 bazel_to_cmake 生成）｜ 语言：C++14
> 许可证：Apache-2.0 ｜ 上游：https://github.com/google/ruy

---

## 1. 上游事实（对 commit 21a85fe tarball 实测审计）

| 项 | 值 |
|---|---|
| 上游仓库 | `google/ruy` |
| commit（全） | `21a85fef159f9942f636a43b14c64b481c2a05b2` |
| commit 日期 | 2023-02-15T19:37:59Z —— 与任务版本号 `git20230215.21a85fe` 精确对应 |
| tarball 大小 | 282524 bytes |
| sha256 | `e151a5b55059a6e83ded001787e1a8889ba1e5e4eaa5bc836b9b660e7e1cb519` |
| 许可证文件 | `LICENSE`（全大写；与 reliable 的 `LICENCE` 拼写不同，按实际拼写 copy） |
| 外部依赖 | 仅 `cpuinfo` |
| 产出库目标 | 30 个（见 §2.2） |
| 上游测试 | 33 条 ctest（32 + profiler 1） |

**ruy 是什么**：Google 的矩阵乘法库，为神经网络推理引擎（最初是 TensorFlow Lite）
提供 GEMM 内核、packing 策略与量化整数路径。对外主 API 是 `ruy::Mul(lhs, rhs,
mul_params, context, &dst)` 与 `ruy::Matrix<T>` / `ruy::MulParams<Accum, Dst>`。

### 1.1 CMakeLists.txt 关键点（逐条核对）

```cmake
# 顶层 CMakeLists.txt
23:  if (PROJECT_NAME STREQUAL CMAKE_PROJECT_NAME)
24:    set(RUY_IS_TOPLEVEL TRUE)
25:    set(RUY_MINIMAL_BUILD_DEFAULT_VALUE OFF)     # ← 顶层默认「不裁剪」
26:  else()
27:    set(RUY_IS_TOPLEVEL FALSE)
28:    set(RUY_MINIMAL_BUILD_DEFAULT_VALUE ON)
29:  endif()
31:  option(RUY_MINIMAL_BUILD "Disable ruy's tests, examples, etc." ${RUY_MINIMAL_BUILD_DEFAULT_VALUE})
32:  if (NOT RUY_MINIMAL_BUILD)
33:    enable_testing()                              # ← 测试注册的总开关
34:  endif()
41:  option(RUY_ENABLE_INSTALL "Enable install rule" ${RUY_IS_TOPLEVEL})
47:  option(RUY_FIND_CPUINFO "Use find_package to find cpuinfo" OFF)
50:  if (NOT TARGET cpuinfo::cpuinfo)                # ← 判据正好是平台 cpuinfo 的 target 名
51:    if (RUY_FIND_CPUINFO)
52:      find_package(cpuinfo REQUIRED)
...
101: if (NOT RUY_MINIMAL_BUILD
102:     AND NOT TARGET gtest
103:     AND EXISTS ".../third_party/googletest/CMakeLists.txt")   # ← EXISTS 保护，缺失则静默跳过
104:   add_subdirectory("third_party/googletest" EXCLUDE_FROM_ALL)
105: endif()
107: add_subdirectory("ruy")
109: if (NOT RUY_MINIMAL_BUILD)
110:   add_subdirectory("example")                   # ← example 会被编译
111: endif()
113: if (RUY_ENABLE_INSTALL)
114:   install(EXPORT ${PROJECT_NAME}Targets ... DESTINATION lib/cmake/${PROJECT_NAME})
```

关键推论（都影响本配方）：

1. **`RUY_MINIMAL_BUILD` 在 conan 构建时默认 OFF** —— conan 以 ruy 源码根为项目根，
   `PROJECT_NAME STREQUAL CMAKE_PROJECT_NAME` 成立 ⇒ `RUY_IS_TOPLEVEL=TRUE`。
2. **`enable_testing()` 与 33 条 `ruy_cc_test` 都依赖 `NOT RUY_MINIMAL_BUILD`**。
3. **`find_package(cpuinfo REQUIRED)` 的判据是 `NOT TARGET cpuinfo::cpuinfo`** ——
   平台版 cpuinfo 声明的 `cmake_target_name` 正是 `cpuinfo::cpuinfo`，天然对接。
4. **googletest 的引入带 `EXISTS` 保护** —— tarball 里该目录是空的（子模块未 checkout），
   所以会静默跳过，不报错（见 §3.2）。
5. **`ruy_add_all_subdirs()` 的实现有一个上游笔误**：
   ```cmake
   foreach(_CHILD ${_CHILDREN})
     if((NOT(subdir MATCHES third_party)) AND ...)   # ← subdir 未定义，应为 _CHILD
   ```
   未定义变量展开为空串，`"" MATCHES third_party` 为假 ⇒ `NOT` 为真 ⇒ 该条件恒成立，
   于是**所有**含 CMakeLists.txt 的子目录都会被纳入。`ruy/profiler` 正是由此被自动
   add_subdirectory（ruy/CMakeLists.txt 末尾第 1844 行调用该函数），其
   `ruy_cc_test` 无任何守卫 ⇒ 第 33 条测试来自这里。

### 1.2 两个补丁都是为了 CMake 4.x / CMakeDeps 环境（非 OHOS 专属）

**补丁 0001 — `cmake_minimum_required()` 的位置**

上游把它写在 `project()` 的**下一行**：

```cmake
15: cmake_policy(SET CMP0012 NEW)
16: cmake_policy(SET CMP0048 NEW)
17: project(ruy CXX)
18: cmake_minimum_required(VERSION 3.13)  # Copied from IREE   ← 位置非法
```

CMake 要求在最早的 `project()` 调用**之前**调用 `cmake_minimum_required()`。
上游 issue #328 记录了这个问题，Conan Center 也用同样的方式处理（只是它的实现是
把该行删除后在版权注释后重新插入；本补丁把它统一挪到文件开头的第一个 CMake 命令处，
语义等价、更符合"as early as possible"的官方要求）。

**补丁 0002 — 去掉硬编码的 `STATIC`**

```cmake
# cmake/ruy_cc_library.cmake:67（原）
add_library(${_NAME} STATIC ${_RULE_SRCS} ${_RULE_HDRS})
```

本仓库模板 R26 要求 `options` 必须含 `shared`，而 ruy 上游把每个库硬编码成静态，
`-DBUILD_SHARED_LIBS=ON` 完全无效。去掉 `STATIC` 后由 CMake 依据 `BUILD_SHARED_LIBS`
决定库类型。Conan Center 对同一行做了同样的替换。

> 两处改动都**不是**为了绕开 OHOS 的限制，而是让上游在 CMake 4.x + Conan 常规环境下
> 按预期工作。补丁文件见 `patches/`。

---

## 2. 适配决策

| 决策 | 内容 | 理由 |
|---|---|---|
| 2.1 | **不设 `RUY_MINIMAL_BUILD`**（保持 OFF） | 设 True 会让 33 条 ctest 一条都不注册（见 §3.1）。这是本配方与 Conan Center 的**关键分歧** |
| 2.2 | `cpp_info.libs` 写 30 个库的显式列表 | 静态库链接顺序敏感；且 x86_64 判据不裁剪库目标（见 §2.3），30 项在 aarch64 上同样成立 |
| 2.3 | 用 `RUY_FIND_CPUINFO=ON` + conan 依赖 `cpuinfo/0.0-git20250905.877328f`（**裸 ref**） | 不使用 `third_party/cpuinfo` 子模块：它在 tarball 里同样是空目录，且 `RUY_IS_TOPLEVEL` 时会直接 `message(FATAL_ERROR "...git submodule update --init")` |
| 2.4 | vendor googletest v1.14.0 到 `third_party/googletest` | 让上游那段 `add_subdirectory` 生效（见 §3.2） |
| 2.5 | `INSTALL_GTEST=OFF`、`BUILD_GMOCK=OFF` | 前者防止 gtest 产物混进 ruy 包；后者省一份编译量（ruy 全树无 gmock 引用，已 grep 实测） |
| 2.6 | `package()` 里 `rmdir(lib/cmake)` | 上游 `install(EXPORT ruyTargets ...)` 会写出 `lib/cmake/ruy/*.cmake`，与 CMakeDeps 的 `ruy-config.cmake` 同名碰撞 |
| 2.7 | 不改动 `ruy_cc_binary` | 它没有任何 install 规则（逐行核对 `cmake/ruy_cc_binary.cmake`），example 会被编译但不进包 ⇒ 包内无 `bin/`（见 §5 L0k） |
| 2.8 | `system_libs = ["m", "pthread"]`，判据 `os in ("Linux", "OHOS")` | OHOS 侧 clang 驱动不隐式带入；R32 要求 os 判断用 `in` 而非 `==` |

### 2.3 为什么 30 个库在 aarch64 上都存在

`ruy/CMakeLists.txt` 里有三处 `CMAKE_SYSTEM_PROCESSOR` 的 x86_64 判据
（第 693、765、837 行），逐个核对后确认它们**只 `set()` 编译选项**：

```cmake
693:  if((CMAKE_SYSTEM_PROCESSOR STREQUAL x86_64 OR ... ) AND NOT MSVC)
694:    set(ruy_7_mavx512..._arch_AVX512 ";-mavx512f;...")
697:  endif()
699:  ruy_cc_library(          # ← 紧随其后的库定义是无条件的
```

即 aarch64 上这些库照样生成，只是不带 AVX 编译选项。**故不存在"ARM 上少几个库"**
的问题，`cpp_info.libs` 可与 Conan Center 保持同一份 30 项清单。

---

## 3. 上游测试怎么跑

### 3.1 最关键的坑：`RUY_MINIMAL_BUILD` 会让测试全部消失

```cmake
# cmake/ruy_cc_test.cmake
function(ruy_cc_test)
  cmake_parse_arguments(...)
  if(RUY_MINIMAL_BUILD)
    return()                # ← 第一句就返回：不 add_executable、不 add_test
  endif()
```

- **Conan Center 的 ruy 配方设 `RUY_MINIMAL_BUILD=True`** ⇒ 0 条 ctest、
  `enable_testing()` 也不被调用 ⇒ 上游测试完全为零。
- 本配方**不设该变量**（顶层默认 OFF）⇒ 33 条 ctest 全部注册并真实执行。

选择后者是因为 L1c 门禁要求"上游测试真实执行并留下痕迹"，而 PR 正文的
"上游测试用例通过率"也需要实测数据。代价是构建量显著变大（30 个库 + 33 个测试
可执行文件 + 2 个 example），详见 §7 的耗时记录。

### 3.2 第二个坑：googletest 目录是空的

GitHub archive 里 `third_party/googletest` **存在但是空目录**（子模块未 checkout）。
上游对它的引用带 `EXISTS` 保护 ⇒ 静默跳过 ⇒ `gtest` 目标从未被定义 ⇒
`ruy_gtest_wrapper`（`TESTONLY` 库，`DEPS gtest`）与 33 个测试目标在链接期全部失败。

处置：`source()` 阶段把 googletest v1.14.0 解压到该路径。

- **版本选择依据**：v1.14.0 的 CMakeLists 声明 `cmake_minimum_required(VERSION 3.13)`，
  在设备侧 CMake 4.x 上可正常 configure；而 1.11.0 声明 `< 3.5`，CMake 4.x 直接拒绝。
  （同仓库 `archives/c/cpuinfo` 使用同一份资源，本机已下载复核 sha256 一致。）
- **代价**：ARCHIVE 里 googletest 是 `config_options` 之外的**构建期**依赖，
  它与 ruy 的源码一起被 export；`conandata.yml` 用独立的 `googletest:` 段声明
  URL 与 sha256（结构同 `archives/c/cpuinfo`）。
- **不构建 gmock**：`BUILD_GMOCK=OFF`。已实测 ruy 全树无 `gmock` 引用。

### 3.3 33 条测试的构成

| 分组 | 条数 | 源文件 |
|---|---|---|
| 快路径内核数值对拍 | 11 | `ruy/test_fast.cc`（按 11 组 `<Lhs,Rhs,Accum,Dst>` 标量组合注册） |
| 慢路径（参考实现）对拍 | 8 | `ruy/test_slow.cc` |
| 核心组件单元测试 | 13 | `check_macros` / `wait` / `size_util` / `tune` / `prepacked_cache` / `allocator` / `block_map` / `matrix` / `mul_params` / `apply_multiplier` / `context` / `ctx` / `perchannel_buffers_reallocation` |
| 溢出专项 | 1 | `ruy/test_overflow_dst_zero_point.cc` |
| profiler 子目录 | 1 | `ruy/profiler/test.cc` |

计数口径见 `test_package/MANIFEST.yml`。

---

## 4. 消费者用例（test_package）

`test_package/test_ruy.cpp` 以"库的使用者"身份，只经 `ruy/ruy.h` 使用公开 API，
调用 `ruy::Mul` 完成 5 组矩阵乘法并逐元素校验：

| 组 | 内容 | 期望值来源 |
|---|---|---|
| T1 | float 2×2（row-major LHS × col-major RHS） | 手算：`[[5,11],[11,25]]` |
| T2 | float 3×2 × 2×4 非方阵 | **CPU 三重循环参考实现对拍**（12 次逐元素比较） |
| T3 | float bias 相加 + clamp | 手算：bias 沿 `channel_dimension`（**默认 kRow**）施加 —— 第 0 行 +100 被 clamp 到 50，第 1 行 −100 被 clamp 到 0 |
| T4 | int8 → int32 原始累加器 | 整数点积精确可预期：`{5,11,11,25}` |
| T5 | 1×1 退化形状 + 同一 Context 复用 3 次 | 手算：3×4=12 |

运行时断言共 **28** 条，程序结束自行打印 `checks=28 failures=0` 与
`HMBS_TEST_PACKAGE_RESULT={...}`，失败则以非零退出码结束。

### 4.1 为什么不用 `assert()`

CMake 的 Release 配置会定义 `NDEBUG`，而 `assert()` 在 `NDEBUG` 下被预处理成空语句 ——
用例会退化成"必然通过"的假测试。CI 的 **L1e 破坏性反向验证**正是针对这种情形
（移走包内产物后重跑必须失败）。因此改用自研 `CHECK_*` 宏：累计失败数、
打印具体不等值、最后以非零退出码上报。

### 4.2 为什么 T4 选 int8 → int32 原始累加器

量化路径的输出通常要经过 `multiplier_fixedpoint` / `exponent` 的定点缩放，
期望值依赖对定点格式的精确理解，容易写出"看起来对但实际错"的断言。
而 ruy 支持 `Dst = int32` 时**跳过全部后处理**（上游 example.cc 注释原文：
"When Dst is int32, mul_params is unused."），得到的就是纯整数点积 ——
期望值可完全手算，断言是硬的。这比抄一个定点乘法器的期望值更可靠。

---

## 5. 逐项过门禁

| 门禁 | 本包的满足方式 |
|---|---|
| **G0e 根目录白名单** | 本 PR 只新增 `archives/r/ruy/**`，不触碰仓库根目录 |
| **L0f patches 须 list 格式** | `conandata.yml` 的 `patches:` 是 list，每项含 `patch_file` / `patch_description` / `patch_type` |
| **L0j 版本是否已被占用** | 见 §7 第 1 行（真机回填） |
| **L0k commands.json** | **不适用**：`package_type = "library"`，无 `bindirs`、无 `RUNTIME DESTINATION bin`、无 `dst="bin"`；且上游 `ruy_cc_binary` 无 install 规则，包内确实不存在 `bin/`。`package()` 另加了一行防御性 `rmdir(package_folder/bin)` |
| **L0m 目录结构** | slug 全小写；`conanfile.py` 的 `name`/`version` 与目录 `archives/r/ruy/0.0.0-git20230215.21a85fe` 一致 |
| **L0o 禁 curl/wget** | 一律走 `conan.tools.files.get()` |
| **L0q export_sources 覆盖补丁** | `export_sources()` 调 `export_conandata_patches(self)` |
| **L1a test_package 被执行** | `test_package/conanfile.py` 有 `test_type = "explicit"` 与 `requirements()`，conan create 会进入 test 阶段 |
| **L1b 编译/运行痕迹** | `_run_bound_step()` 把 build 与 ctest 的输出回显进 conan 日志；test_package 同样回显其 `build.log` |
| **L1c 上游测试痕迹** | 日志中出现 `ctest` 及其 `N% tests passed` 汇总行（33 条） |
| **L1d test() 非假运行** | `test()` 内是 `self.run(<binary>, env="conanrun")`，非 `echo/print/true` |
| **L1e 破坏性反向验证** | 用例 `#include "ruy/ruy.h"` 并链接包内 30 个静态库；移走 `include/`、`lib/` 后必然编译/链接失败 |
| **L2** | 无 `bin/` ⇒ 预期 `skip: no bin/ dir` |
| **L4 补丁安全扫描** | 两个补丁只改 CMake 文件的语句位置与 `add_library` 参数，不含 `strcpy/sprintf/gets/strcat` |
| **L5** | 无外部资源下载（除 conandata 声明的两个 URL，均带 sha256 校验） |
| **R27 依赖命名** | 依赖写成**裸 ref** `cpuinfo/0.0-git20250905.877328f`。模板注释里的 R27 要求 `@ohpcd/stable`，但制品仓不带 channel，那样写会报 `Unable to find in remotes`（见 §6 第 9 条） |
| **R32 os 判断** | 全部写作 `in ("Linux", "OHOS")` |
| **JC 垃圾文件** | 工作产物一律写 `${TMPDIR:-$HOME/tmp}`，不落仓库；`reports/` 已被仓库 `.gitignore` 全局忽略，故不放可提交文件 |
| **W2 PR 原子性（JC6）** | 改动范围只有 `archives/r/ruy/`，涉及软件数 = 1 |

---

## 6. 踩坑记录

1. **archive 里的空子模块目录会"静默吃掉"测试**
   `third_party/googletest` 存在但为空，上游用 `EXISTS` 保护 ⇒ 不报错、直接跳过 ⇒
   测试目标链接期才炸。判断方法：`ls -A third_party/googletest | wc -l` 得到 0。
   同类：`third_party/cpuinfo`。

2. **`ruy_add_all_subdirs()` 的条件写错，反而"全收"**
   `NOT(subdir MATCHES third_party)` 里的 `subdir` 未定义（循环变量是 `_CHILD`），
   恒为真。看起来像"排除 third_party"，实际是"纳入所有子目录"。这解释了
   `ruy/profiler` 的测试为何在顶层 CMakeLists 里找不到 `add_subdirectory` 却仍被注册。

3. **`-DRUY_MINIMAL_BUILD=True` 是"看起来更省事"的陷阱**
   Conan Center 用它把构建量降下来，代价是上游测试归零。路径 A 的门禁要求证据，
   所以这里反过来做。

4. **`install(EXPORT ...)` 与 CMakeDeps 的 config 同名碰撞**
   上游写到 `lib/cmake/ruy/ruy-config.cmake`，CMakeDeps 也生成 `ruy-config.cmake`。
   必须在 `package()` 里删掉上游那份（`rmdir(lib/cmake)`）。

5. **`add_subdirectory` 引进来的第三方项目会污染 install 产物**
   googletest 自带 install 规则，`cmake.install()` 会把它的头文件与库一并装进
   ruy 的包。必须 `INSTALL_GTEST=OFF`。

6. **CMake 不认 HarmonyOS**
   `CMAKE_SYSTEM_NAME` 会退化成宿主值、`CMAKE_SYSTEM_PROCESSOR` 变成 `unknown`，
   所有架构分支走空。经 toolchain 变量强制 `Linux` / `aarch64`（同 `archives/c/cpuinfo`）。

7. **conan 输出流继承导致 OHOS 上 clang 静默失败**（沿用 reliable 的结论）
   `ConanFile.run()` 把 recipe 进程的输出流继承给子进程时，clang 在第一个真正编译的
   翻译单元上非 0 退出且零诊断，make 只报 `Error 1`。解法是把每步输出绑定到
   `build_folder/logs/<label>.log` 再回显（`_run_bound_step()`）。

8. **Bazel `BUILD` 文件与 `build` 目录在 HMDFS 上撞名 —— 直接阻断构建**（真机实测）
   上游仓库根有一个 Bazel 用的 `BUILD` 文件（283 字节；本包**没有改动它**，
   它只服务 Bazel，CMake 构建路径完全不引用）。而 **HMDFS 是大小写不敏感的**
   （官方知识库 E193：`BOO` 与 `boo` 共享同一 inode，行为同 macOS APFS/HFS+；
   本机直接实测：`echo x > ABC` 之后 `cat abc` 读到同一内容）。
   conan 会把源码树复制到构建根下 ⇒ `BUILD` 落在 `<build_root>/BUILD`；此时
   `cmake_layout` 默认要创建的 `<build_root>/build/Release` 中，`build` 解析到的
   正是那个 `BUILD` 文件（`ls -ld` 显示为 `-rw-rw---- ... 283 .../b/build`，与
   `.../b/BUILD` 同一 inode），于是 mkdir 直接失败：

   ```
   ERROR: [Errno 20] Not a directory: '/storage/.../.conan2/p/b/ruy.../b/build/Release'
   ```

   失败点在 **`generate()` 阶段**——真机实测 7 秒即退出，**尚未开始编译**，
   所以与编译器、源码、补丁都无关。

   ⇒ 处置用官方知识库的既定方案（`knowledge/doc/E470`，来源 PR !7190）：
   `cmake_layout(self, build_folder="build_dir")`。`reliable` 包没有 `BUILD`
   文件，因此这个坑只在 ruy 这类 Google/Bazel 仓库上才暴露。

9. **MSYS/Windows 侧工具链的两个坑**（本地准备阶段踩到）
   - 本机 `curl` 直连 `github.com` 返回 `http=000`，必须走 `ghfast.top` 前缀 ——
     这也是 `conandata.yml` 里镜像项写成"必需通路"而不仅是兜底的原因。
   - Git Bash 的 `/tmp` 与 Python 的 `/tmp` 解析不同（后者会变成 `C:\tmp`），
     跨语言传路径一律用 `C:/...` 形式。

10. **设备上 `patch` 是 toybox 版 —— 但与本包无关**（已实测确认，避免误判）
    真机 `/usr/bin/patch` 是 `toybox 0.8.12`，用法帮助里明确写着"只处理 unified diff"。
    但 `conan.tools.files.patch` **并不调用系统 patch**：实读设备上的
    `conan/tools/files/patches.py` 可见它用的是内置 Python 库：
    `patchset = patch_ng.fromfile(path)` → `patchset.apply(strip=strip, root=root, fuzz=fuzz)`。
    实测 `strip=0`（conan 默认值，`apply_conandata_patches` 不传 strip）与 `strip=1`
    **都能正确应用**本包两个带 `a/`+`b/` 前缀的补丁（返回 `True`、结果一致、
    不产生多余的 `a/` 目录）。另外 toybox patch 本身也能手工 `-p1` 干净应用，
    且无 `.orig`/`.rej` 残留。

11. **`bias` 不是"按列"施加的 —— 默认沿行（`channel_dimension = kRow`）**（真机实测暴露）
    写消费者用例时按"`Dst(i,j) += bias(j)`"的直觉断言 T3，真机跑出
    `checks=28 failures=2`，且两个失败值恰好**互换**：

    ```
    [FAIL] dst_data[1] line 194: got 0.000000, want 50.000000
    [FAIL] dst_data[2] line 195: got 50.000000, want 0.000000
    ```

    回查上游 `ruy/mul_params.h` 才看清：bias 施加的维度由
    `MulParams::channel_dimension()` 指定，而该字段**默认值是
    `ChannelDimension::kRow`**：

    ```cpp
    // Designates which dimension is the 'channels', for per-channel features
    // such as bias-addition and per-channel quantization multipliers.
    ChannelDimension channel_dimension() const { ... }
    ...
    ChannelDimension channel_dimension = ChannelDimension::kRow;   // 默认
    ```

    ⇒ 默认语义是 `Dst(i,j) += bias(i)`（按**行**），不是按列。
    对本案的 col-major 2×2 dst（`data[j*2+i]`），正确的期望是
    `{50, 0, 50, 0}`（第 0 行 +100→clamp 50，第 1 行 −100→clamp 0），
    与实测完全一致 —— **是测试的假设错了，不是包的问题**
    （同一轮 run 里上游 33/33 ctest 全通过）。
    若要按列施加需显式 `set_channel_dimension(ChannelDimension::kCol)`；
    置 `kCol` 时 bias 长度应等于 `dst.layout.cols()`。
    这条也解释了为什么"对称的 2×2 + 对称布局"最容易掩盖方向性错误。

---

## 7. 本地验证记录（在鸿蒙 PC 上实跑后回填）

> 本表是**证据记录**，不是待办清单。提 PR 前必须把下面每一行的结果列
> 换成实跑输出（原始日志节选见 §9「真机原始输出留档」）。
> PR 正文中不得出现任何"未验证"性质的表述。

> 占用真机之前已做的主机侧静态预验证（**不能替代本表**）：
> ① 两个补丁在干净源码上通过 `git apply --check`、`patch -p1 --dry-run` 与实际应用
> 三重验证，无 `.orig`/`.rej` 残留；
> ② `conandata.yml` 的两个 sha256 均已在本机下载并复核（ruy tarball 282524 B、
> googletest zip 1090859 B）；
> ③ 33 条 ctest 的注册点、30 个库目标的清单、`ruy_cc_binary` 无 install 规则、
> 全树无 gmock 引用，均已源码级核对。

| # | 验证项 | 命令 | 实测结果 |
|---|---|---|---|
| 1 | 制品仓是否已存在 `ruy/0.0.0-git20230215.21a85fe`（L0j） | `conan download ruy/0.0.0-git20230215.21a85fe -r=ohpcd --only-recipe` + 本地 CI 模拟的 L0j | ⚠️ 手工调用时平台返回 `error:system acceleration policy not enabled. [Remote: ohpcd]`（远程策略限流，**不是**"版本已占用"）；已改由 CI 的 L0j 环节判定，见 §7.1 |
| 2 | `conan create` 是否通过、补丁是否生效 | `conan create archives/r/ruy/0.0.0-git20230215.21a85fe -pr:h=... -pr:b=... --build=missing --build="ruy/*"`（**绝对路径** profile） | ✅ **退出码 0，耗时 254s**；两个补丁均干净应用（完整构建日志中 `Apply patch` ×2、无 `Failed to apply patch`）、`Built target` 78 个、零 `error:` |
| 3 | 上游 33 条 ctest 通过率 | `build_folder/logs/ctest.log` 的汇总行 + 配方自报的 `HMBS_UPSTREAM_TEST_RESULT` | ✅ **33/33 passed, 0 failed**，`Total Test time (real) = 44.40 sec`；配方自报 `{"total": 33, "passed": 33, "failed": 0, "percent": 100}` |
| 4 | 消费者用例 28 条断言通过率 | `./test_ruy` 输出（`checks=28 failures=0`） | ✅ **`checks=28 failures=0`** + `ALL CONSUMER CHECKS PASSED`（失败计数 0 时程序返回 0） |
| 5 | 包内是否出现 `bin/`（L0k 判据） | `ls <package_folder>/bin` | ✅ **0 条目**（`bin/` 不存在） |
| 6 | `cpp_info.libs` 的 30 项与包内实际库文件是否一致 | `ls <package_folder>/lib/*.a \| wc -l` 与逐一比对 | ✅ **恰 30 个 `.a`**，与 `cpp_info.libs` 一一对应（`libruy_allocator`、`apply_multiplier`、`block_map`、`blocking_counter`、`context`、`context_get_ctx`、`cpuinfo`、`ctx`、`denormal`、`frontend`、`have_built_path_for_avx{,2_fma,512}`、`kernel_arm`、`kernel_avx{,2_fma,512}`、`pack_arm`、`pack_avx{,2_fma,512}`、`prepacked_cache`、`prepare_packed_matrices`、`profiler_instrumentation`、`profiler_profiler`、`system_aligned_alloc`、`thread_pool`、`trmul`、`tune`、`wait`）；另 `include/ruy` 47 个头文件、`licenses/LICENSE` 齐备 |
| 7 | 消费者 ELF 的动态依赖 | `readelf -d test_ruy` 的 `NEEDED` | ✅ **`Class: ELF64` / `Machine: AArch64` / `Type: DYN (Position-Independent Executable)`**；`NEEDED` = `libc++_shared.so`、`libc.so`；`RUNPATH` 指向 conan 缓存中 ruy 与 cpuinfo 的 `p/lib`；二进制中解析出 **218 个 `ruy::` 符号** ⇒ 确实链接已安装包并真实调用被测 API（原文见 §9.4） |
| 8 | **构建耗时**（R1 风险项：30 库 + 33 测试且强制 `-j1`） | conan create 的 build 阶段计时 | ✅ **254s ≈ 4 分 14 秒**，占 CI 单包上限 `DEFAULT_BUILD_TIMEOUT=3600` 的 **7%** |
| 9 | 本地 CI 模拟整体结果 | `CI_PACKAGES="archives/r/ruy/0.0.0-git20230215.21a85fe" CI_BRANCH="feat/ruy-0.0.0-git20230215.21a85fe" JUNK_PR_DIFF=<pr.diff> zsh ci/conan/build_and_test.sh` | ✅ **全部门禁通过，整体退出码 0，耗时 379s**：`JC_RESULT=pass`（`JC_ERRORS=0`，JC6 单软件原子性合规）、`L0_RESULT=pass`、`L1_RESULT=pass`、`L2_RESULT=skip: no bin/ dir`、`L4_RESULT=pass`、`L5_RESULT=pass`；`L1e` 破坏性反向验证按预期触发；Build Summary `Pass rate: 100.0% (1/1)`。详见 §7.3 |
| 10 | 改动范围是否只有 `archives/r/ruy/` | `git add -N -- archives/r/ruy && git diff --binary -- archives/r/ruy` | ✅ 本 PR 只新增 `archives/r/ruy/**`（`git add archives/r/ruy` 后 `git diff --cached --name-only` 仅本目录文件）。**另需说明**：真机工作副本还有 `M archives/l/libXext/{README.md,manifest.yaml}` 两处脏改动，经实测**不是行尾差异**（`--ignore-cr-at-eol` 后差异仍在、两文件行尾均为 LF、`core.autocrlf` 未设置），是他人未提交的手工内容改动，与本 PR 无关，提交时以显式路径 `git add` 绕开 |
| 11 | 构建目录改名是否规避了 `BUILD`/`build` 撞名（§6.8 / E470） | 真机重跑 `conan create`，应越过 `generate()` 进入真正编译阶段（对照：未改名时 7s 即在 generate 阶段退出） | ✅ 已越过：完整跑到 78 个 `Built target` 与 33 条 ctest 结束 |

### 7.1 关于 L0j 平台报错的说明

`conan download ... -r=ohpcd --only-recipe` 返回
`ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`。
这是**远端策略/限流**层面的拒绝，与"版本号已被占用"是两回事（后者会明确提示
`already exists` 之类）。该判据以 CI 的 L0j 环节结论为准（见 §7.3）。

### 7.2 消费者 ELF

⏳ **待回填**（重跑 test_package 后用 `readelf -h/-d test_ruy` 采集；只回填实测输出，
不预先写结论）。

### 7.3 本地 CI 模拟

按 W3 规程在本机（鸿蒙 PC）复刻 CI：

```bash
# 只暂存本包，生成 PR diff（放仓库外，避免污染根目录触发 G0e）
git add archives/r/ruy
git diff --cached --binary -- archives/r/ruy > "$HOME/tmp/pr-ruy.diff"

# W0：依赖发布预检
bash ci/scripts/preflight_check.sh ruy/0.0.0-git20230215.21a85fe

# W3：junk_check 走 prdiff 模式（只检本 PR 文件；不传 JUNK_PR_DIFF 会回退全仓扫描而误报他人基线垃圾）
JUNK_PR_DIFF="$HOME/tmp/pr-ruy.diff" bash ci/scripts/junk_check.sh

# 主门禁 L0–L5
CI_PACKAGES="archives/r/ruy/0.0.0-git20230215.21a85fe" \
CI_BRANCH="feat/ruy-0.0.0-git20230215.21a85fe" \
JUNK_PR_DIFF="$HOME/tmp/pr-ruy.diff" \
zsh ci/conan/build_and_test.sh
```

结果：**全部门禁通过，整体退出码 0**（耗时 379s）：

```
JC_RESULT=pass                    （junk_check，prdiff 模式，JC_ERRORS=0；
                                   JC6 PR 单软件原子性：涉及软件数 1，合规）
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
L2_RESULT=skip: no bin/ dir
L4_RESULT=pass: patches clean
L5_RESULT=pass: lib/ has content
Build Summary → Total 1 / Success 1 / Failed 0 / Pass rate 100.0% (1/1)
```

其中 `L1e`（R34）破坏性反向验证**按预期触发**，证明消费者用例真的依赖被测包：

```
[step] L1e: Destructive negative test (R34)...
        [sabotage] lib/ moved away
        [sabotage] include/ moved away
[ok] L1e: Negative test confirmed — test genuinely depends on ruy
```

#### 关于日志中 `[fail] ... 'curl'` 的说明（避免误判）

`build_and_test.sh` 的 **pre-download** 环节会调用系统 `curl` 把源码 tarball
预拉进 conan download cache。本机（鸿蒙 PC）未安装 `curl`，于是该环节对每个
URL 打印：

```
[fail] [Errno 2] No such file or directory: 'curl'
[WARN] Failed to pre-download 21a85fe....tar.gz, will rely on conan's download
```

这是**非致命**的降级路径：随后由 conan 自带的下载器完成拉取，`conan create`
成功、33/33 ctest 与 28/28 消费者断言全部通过、全部门禁 pass（见上方结果行）。
该环节在装有 `curl` 的 CI 执行机上正常执行，**与包配方无关**。

---

## 8. 可沉淀为知识库素材的点（路径B 候选，本 PR 不提交）

1. **「archive 中的空子模块目录会让测试静默消失」是一类问题**
   判据明确（`ls -A <submodule_dir>` 为空 + 上游用 `EXISTS` 保护）、
   解法统一（在 `source()` 阶段 vendor 源码到该路径）。适用于所有带 submodule
   依赖的开源库。

2. **「上游构建开关的默认值是"顶层项目"相关」是一类问题**
   `RUY_MINIMAL_BUILD` / `RELIABLE_BUILD_TESTS` 这类变量的默认值随
   `*_IS_TOPLEVEL` 变化；照抄第三方配方（CCI）时若不核对这一点，极易把测试关掉。
   判据：搜 `option(...)` 的默认值表达式，再搜该变量在测试注册函数里的用法。

3. **「add_subdirectory 引入的第三方项目污染 install 产物」是一类问题**
   googletest / benchmark 这类项目自带 install 规则，`cmake.install()` 会把它们
   装进宿主包。解法：查它们的 `INSTALL_*` 开关并关掉。

> 本节按用户要求仅作记录，**不随本 PR 提交**（路径A 只允许改 `archives/`）。

---

## 9. 真机原始输出留档（节选）

> 环境：鸿蒙 PC（OpenHarmony 6.0 / aarch64 / clang 15.0.4 / cmake 4.1.2 /
> conan 2.29.1 / zsh / 仓库 `build_in_harmonyos`）。
> 本节在 M2（真机 `conan create`）完成后回填。

### 9.1 配方导出与补丁应用

```
======== Exporting recipe to the cache ========
ruy/0.0.0-git20230215.21a85fe: Exporting package recipe: .../archives/r/ruy/0.0.0-git20230215.21a85fe/conanfile.py
ruy/0.0.0-git20230215.21a85fe: exports: File 'conandata.yml' found. Exporting it...
ruy/0.0.0-git20230215.21a85fe: Calling export_sources()
ruy/0.0.0-git20230215.21a85fe: Copied 1 '.yml' file: conandata.yml
ruy/0.0.0-git20230215.21a85fe: Copied 1 '.py' file: conanfile.py
ruy/0.0.0-git20230215.21a85fe: Copied 2 '.patch' files: 0001-cmake-minimum-required-before-project.patch, 0002-ruy-cc-library-allow-shared.patch
ruy/0.0.0-git20230215.21a85fe: Exported to cache folder: /storage/Users/currentUser/.conan2/p/ruy6c06df909cb06/e
ruy/0.0.0-git20230215.21a85fe: Exported: ruy/0.0.0-git20230215.21a85fe#4356b64be39342b48373be6f3048dd2f (2026-09-29 09:34:58 UTC)
```

```
ruy/0.0.0-git20230215.21a85fe: Apply patch (portability): Move cmake_minimum_required() to the top of CMakeLists.txt (CMake requires it before project(); upstream issue #328)
ruy/0.0.0-git20230215.21a85fe: Apply patch (portability): Drop the hardcoded STATIC in ruy_cc_library so BUILD_SHARED_LIBS is honoured
```

`export_sources()` 把两个补丁一并导出（`Copied 2 '.patch' files`），
`source()` 阶段经 `patch_ng` 干净应用，**无 `Failed to apply patch`、无 `.orig`/`.rej` 残留**。

### 9.2 `build()` 与上游 33 条 ctest

```
28/33 Test #28: ruy_test_slow_u8_u8_i32_i16 ................   Passed    2.72 sec
29/33 Test #29: ruy_test_slow_i8_i8_i32_i32 ................   Passed    2.90 sec
30/33 Test #30: ruy_test_slow_i8_i16_i32_i16 ...............   Passed    5.75 sec
31/33 Test #31: ruy_test_slow_i16_i8_i32_i16 ...............   Passed    5.60 sec
32/33 Test #32: ruy_test_overflow_dst_zero_point ...........   Passed    0.07 sec
33/33 Test #33: ruy_profiler_test ..........................   Passed    0.27 sec

100% tests passed, 0 tests failed out of 33

Total Test time (real) =  44.40 sec
```

```
HMBS_UPSTREAM_TEST_RESULT={"status": "passed", "framework": "ctest", "command": "ctest --output-on-failure", "total": 33, "passed": 33, "failed": 0, "percent": 100}
```

同轮日志：`Built target` **78** 个，零 `error:` / `fatal error:`。

### 9.3 消费者用例（test_package）原文

```
ruy/0.0.0-git20230215.21a85fe (test package): Running test()
ruy/0.0.0-git20230215.21a85fe (test package): RUN: ./test_ruy
ruy consumer test — linking against the installed package
ruy::Mul API exercised through ruy/ruy.h only

T1 float 2x2 (row-major x col-major)
T2 float 3x2 * 2x4 (row-major x row-major, vs reference)
T3 float 2x2 with bias add and clamp
T4 int8 2x2 -> int32 raw accumulators
T5 1x1 degenerate case and repeatability

checks=28 failures=0
HMBS_TEST_PACKAGE_RESULT={"status":"passed","checks":28,"failures":0}
ALL CONSUMER CHECKS PASSED
```

首轮（修正前）的失败原文，留档以说明 §6.11 的定位过程：

```
T1 float 2x2 (row-major x col-major)
T2 float 3x2 * 2x4 (row-major x row-major, vs reference)
T3 float 2x2 with bias add and clamp
T4 int8 2x2 -> int32 raw accumulators
T5 1x1 degenerate case and repeatability

checks=28 failures=2
HMBS_TEST_PACKAGE_RESULT={"status":"failed","checks":28,"failures":2}

  [FAIL] dst_data[1] line 194: got 0.000000, want 50.000000
  [FAIL] dst_data[2] line 195: got 50.000000, want 0.000000

ERROR: ruy/0.0.0-git20230215.21a85fe (test package): Error in test() method, line 72
	self.run(binary, env="conanrun")
	ConanException: Error 1 while executing
```

### 9.4 `package()` 产物与 ELF / 动态依赖

```
包目录: /storage/Users/currentUser/.conan2/p/b/ruy764bad55aaee6/p
  lib/ 文件数: 30        （清单见 §7 第 6 行）
  bin/ 条目数: 0
  include/ruy 文件数: 47
  licenses 条目: LICENSE
```

消费者二进制：

```
-rwxrwx---  190976 bytes  .../test_package/build/clang-15-armv8-17-release/test_ruy

Class:                             ELF64
Data:                              2's complement, little endian
Type:                              DYN (Position-Independent Executable file)
Machine:                           AArch64

RUNPATH   /storage/Users/currentUser/.conan2/p/b/ruy705e372daf943/p/lib:/storage/Users/currentUser/.conan2/p/cpuin3d171859a4c14/p/lib
NEEDED    libc++_shared.so
NEEDED    libc.so

ruy:: 符号数: 218
```

`RUNPATH` 指向 conan 缓存中 ruy 与 cpuinfo 的 `p/lib`，且二进制中解析出
**218 个 `ruy::` 符号** —— 证明消费者确实是链接已安装包并真实调用了被测 API，
而非编译期把源码塞进来。

### 9.5 日志中需鉴别的输出（与失败无关的正常输出）

| 输出 | 性质 |
|---|---|
| `[fail] [Errno 2] No such file or directory: 'curl'` + `[WARN] Failed to pre-download ..., will rely on conan's download` | CI 脚本 pre-download 环节调用系统 `curl`，本机未装 ⇒ 降级为 conan 自带下载器。**非致命**，不参与门禁判定（详见 §7.3 说明） |
| `ruy_test_slow_*` 单条 2.7–5.8 秒 | 上游"慢路径参考实现"对拍，本身耗时较长，非卡死 |
| `[step] Pre-download: conandata.yml 已还原为官方 URL` | CI 脚本在预下载阶段临时改写 `conandata.yml` 的 URL 后**还原**，属正常收尾 |

### 9.6 本地 CI 模拟的门禁说明

见 §7.3 —— W0（`preflight_check.sh`）、W3（`junk_check.sh`，prdiff 模式）
与 L0–L5 主门禁（`build_and_test.sh`）全部通过，整体退出码 0。

> 提交前须删除 CI 产物 `archives/r/ruy/<ver>/ci-metadata.json`：
> 该文件由 `build_and_test.sh` 生成在包目录内，不在本 PR 的预期文件集合中
> （本 PR 只包含 12 个文件：软件级 2 + 版本级 4 + `patches/` 2 + `test_package/` 4）。
