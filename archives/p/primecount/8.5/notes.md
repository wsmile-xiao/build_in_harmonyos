# primecount 8.5 适配笔记

## ⚠️ 版本说明（重要）

任务派单要求 "primecount 12.6"，但 **primecount 上游不存在 12.6 版本**：

- 上游仓库 https://github.com/kimwalisch/primecount 最新 tag/release 为 **v8.5**（2026-05-11 发布），master `project(primecount VERSION 8.6)`（开发中，未发布）；
- primecount 的 tag 列表中无 9.x / 10.x / 11.x / 12.x 任何版本；
- "12.6" 实为同作者 **primesieve** 库的版本号（primesieve 有 v12.6，最新 v12.14），疑似派单系统误将依赖库版本植入了 primecount。

按 R37（版本号=上游版本）与 R39（源码 URL+sha256 必须是该版本官方真实源码）要求，不能用 8.5 源码冒充 12.6。故本 PR 适配**真实最新版 primecount 8.5**，版本号、源码 URL、sha256 全部如实对应 8.5。若派单系统确需 "12.6" 槽位，请提供 primecount 12.6 的官方源码 URL 与 sha256 后再适配。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-14
- 编译器: clang / clang++ (OHOS aarch64)
- Conan 版本: 2.29.1
- Python 版本: 3.12.9
- 状态: built（本地无鸿蒙环境，CI 在真实鸿蒙 worker 验证）

## 源码与依赖

| 项目 | 内容 |
|------|------|
| 源码 URL | https://github.com/kimwalisch/primecount/archive/refs/tags/v8.5.tar.gz |
| sha256 | a2dd9714e723388987183776d068d6845b82b2cf8ea44ecb6cea3fd9dde938ea |
| 解压根目录 | primecount-8.5 |
| 外部 Conan 依赖 | 无（libprimesieve 以 vendored 源码形式内置于 lib/primesieve，共 177 个文件） |

### 为何无外部依赖

primecount 的 CMakeLists.txt 默认 `BUILD_LIBPRIMESIEVE=ON`，通过 `add_subdirectory(lib/primesieve)` 从源码构建 libprimesieve。v8.5 的 GitHub tag archive 内已包含完整的 `lib/primesieve/` 源码（非 git submodule，无 .gitmodules），因此无需 primesieve 的 Conan 包，规避了 R36 依赖发布问题。CMakeLists 仅在 `BUILD_LIBPRIMESIEVE=OFF` 时才 `find_package(primesieve REQUIRED)`。

## 构建配置

```python
# conanfile.py generate() 关键配置
tc.variables["BUILD_SHARED_LIBS"] = False   # 静态库（上游默认），避免 .so 污染
tc.variables["BUILD_TESTS"] = False         # 不构建上游测试程序（L1 由 test_package 承担）
tc.variables["WITH_OPENMP"] = False         # 禁用 OpenMP（规避 libomp 缺失），退化为串行
tc.variables["WITH_MULTIARCH"] = False      # 关闭运行期 SVE/AVX512 CPU 分发
```

### 选项取舍依据

| 选项 | 取值 | 依据 |
|------|------|------|
| BUILD_SHARED_LIBS | False | 上游默认即静态；非系统同名库，静态避免 .so 污染 |
| BUILD_TESTS | False | 上游测试默认关闭；test_package 已覆盖 L1 |
| WITH_OPENMP | False | OHOS 可能不附带 libomp；禁用后退化为串行实现，功能完整（primecount parallel.h 在无 `_OPENMP` 时走串行分支） |
| WITH_MULTIARCH | False | 关闭运行期 SVE 等指令集分发，避免额外 `-march=...+sve` 编译标志带来的构建风险，使用基础 aarch64 代码 |

## 遇到的问题与解决方案

无编译期问题。primecount 为纯计算库，不涉及图形/HAL/系统底层接口，aarch64 + musl + libc++ 下无需平台适配补丁。OpenMP/Multiarch 的潜在风险通过上述 CMake 选项规避。

## test_package 验证

test_package 链接 `libprimecount.a` 并调用其 C API（`<primecount.h>`）：

- `primecount_pi(100) == 25`（≤100 的素数共 25 个）
- `primecount_pi(1000) == 168`（≤1000 的素数共 168 个）
- `primecount_nth_prime(1) == 2`（第 1 个素数为 2）
- `primecount_version() == "8.5"`

三者全部命中即返回 0，否则返回 1。这些值取值小、计算瞬时完成，且为公认的素数计数真值，便于在 CI 上稳定验证。

## 交付物

| 文件 | 说明 |
|------|------|
| libprimecount.a | 静态库（素数计数核心） |
| primecount | 命令行可执行文件 |
| primecount.pc | pkg-config 文件 |
| primecount-config.cmake | CMake 配置文件 |
| primecount.h | 公共头文件（C/C++ API） |

## CI 验证

### 首次构建 #1851（commit 290e6476）— 失败，已修复

CI build #1851（Worker CI-026）的 `conan-build-test` 步骤在 test_package 链接阶段失败。构建本身全部成功（libprimesieve.a、libprimecount.a、primecount 二进制均正常生成并安装）。

**根因（配方 bug，非环境问题）**：

`libprimecount.a` 对 vendored `libprimesieve.a` 是 **PRIVATE 依赖**（CMake `target_link_libraries(libprimecount-static PRIVATE primesieve::primesieve)`）。静态库不会解析自身私有交叉引用，因此消费方必须在最终可执行文件链接时同时链接 `libprimesieve.a`，否则出现：

```
ld.lld: error: undefined symbol: primesieve::set_num_threads(int)
ld.lld: error: undefined symbol: primesieve::iterator::iterator(unsigned long, unsigned long)
ld.lld: error: undefined symbol: primesieve::iterator::generate_next_primes()
ld.lld: error: undefined symbol: primesieve::iterator::~iterator()
ld.lld: error: undefined symbol: primesieve::iterator::generate_prev_primes()
... (全部为 primesieve::* 符号，来自 libprimecount.a 的 api.cpp/PiTable.cpp/P2.cpp/AC.cpp 等)
```

首次配方 `cpp_info.libs = ["primecount"]` 只让 test_package 链接了 `libprimecount.a`，缺少 `libprimesieve.a` → 链接失败。`primecount` 二进制本身能链接成功，是因为 primecount 的 CMakeLists 在构建树内显式 `target_link_libraries(primecount PRIVATE primecount::primecount primesieve::primesieve)`，两个静态库同时链接；而 conan 的 CMakeDeps 只依据 `cpp_info` 生成消费方配置，不知道 primesieve 依赖。

**修复**：`package_info()` 中将两个静态库一并声明，顺序 primecount 在前、primesieve 在后（链接器从左到右解析 primecount 未定义的 primesieve 符号）：

```python
self.cpp_info.libs = ["primecount", "primesieve"]
self.cpp_info.bindirs = ["bin"]   # 安装 primecount CLI 二进制，消除 L0k 误报
```

包产物确认（来自 #1851 install 日志，二者均在 `lib/`）：

```
.../p/lib/libprimesieve.a
.../p/lib/libprimecount.a
.../p/bin/primecount
.../p/include/primecount.h
```

另：#1851 出现 `L0k warn: commands.json exists but package looks like a library (no bindirs)`，系 `cpp_info` 未显式声明 `bindirs` 所致；本次显式设置 `bindirs=["bin"]` 后消除。

### 修复后预期（待 CI 重跑）

| 门禁 | 预期 | 说明 |
|------|------|------|
| L0 | PASS | 结构完整、无外部依赖、首次发布、commands.json + bindirs 一致 |
| L1 | PASS | test_primecount 通过：pi(100)=25 pi(1000)=168 nth_prime(1)=2 |
| L1e | PASS | 破坏性反向验证通过 |
| L2 | PASS | primecount --version |
| L4 | PASS | 无补丁 |
| L5 | PASS | bin/lib 有产物 |

---

**编译日期**: 2026-07-14
**Conan 引用**: `primecount/8.5`
