# RapMap 0.15.0 适配笔记

- 上游：https://github.com/COMBINE-lab/RapMap ，tag `salmon-v0.15.0`（commit `de73d6841932`）
- 源码包：`https://github.com/COMBINE-lab/RapMap/archive/refs/tags/salmon-v0.15.0.tar.gz`
  - sha256 `cf0537c9cd4e8ce3b28ecca7eb78ee5c59e98a09f5390a5c548d0a5494bb54fc`，1161423 B
  - 取源取证：canonical URL 与 `codeload.github.com/.../tar.gz/refs/tags/salmon-v0.15.0` **同一 sha256**（B 机实测 200 / 1.16 MB）。
    注：对 `github.com/<o>/<r>/archive/...` 发 **HEAD** 请求会 30 s 超时（HTTP=000），**GET** 正常；
    对 `codeload.github.com` HEAD 亦超时。判定端点可用性必须用 GET + `-w '%{http_code} %{size_download}'`。
- 语言/构建系统：cpp / CMake（R47 语言预检匹配，非 env_unsupported）
- 设备：B 机（HarmonyOS aarch64，clang 15.0.4 `aarch64-unknown-linux-ohos`，CMake 4.1.2，Ninja 1.13.1）

---

## 1. 在线拉取雷清点（步骤 2）

对解包源码执行：`grep -rn "FetchContent|ExternalProject|ExternalSource|file(DOWNLOAD|execute_process.*(git clone|curl|wget)|include(External"`
命中范围 `--include=*.cmake --include=CMakeLists.txt --include=*.txt`。

| 模式 | 结果 |
|---|---|
| `FetchContent` | **0 命中** |
| `file(DOWNLOAD` / `ExternalDownload` | **0 命中** |
| `execute_process` + git clone/curl/wget | **0 命中** |
| `include(ExternalProject)` | 3 命中（CMakeLists.txt:187 / :220 / :241） |
| `ExternalProject_Add` | **3 处**，逐条如下 |

### 雷 1 —— `ExternalProject_Add(libdivsufsort)`（CMakeLists.txt:220-231）**不联网**

```cmake
include(ExternalProject)
ExternalProject_Add(libdivsufsort
    DOWNLOAD_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external
    URL ${CMAKE_CURRENT_SOURCE_DIR}/external/libdivsufsort.tar.gz
    SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/libdivsufsort-master
    INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/install
    UPDATE_COMMAND sh -c "mkdir -p <SOURCE_DIR>/build"
    BINARY_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/libdivsufsort-master/build
    CMAKE_ARGS -DCMAKE_INSTALL_PREFIX:PATH=<INSTALL_DIR> -DBUILD_DIVSUFSORT64=TRUE -DUSE_OPENMP=TRUE -DBUILD_SHARED_LIBS=FALSE
)
set(SUFFARRAY_INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/external/install/include)
```

- `URL` 指向**随源码包一起分发的本地 tarball**（`external/libdivsufsort.tar.gz`，26130 B，已确认在包内）⇒ **不需要网络**。
- 但 **无条件执行、无开关**，且子构建不继承 Conan 的 toolchain（`CMAKE_TOOLCHAIN_FILE` 不透传），
  并且 `-DUSE_OPENMP=TRUE` 要求子 CMake 自行找到 OpenMP ⇒ 交叉编译环境下不可靠。
- 制品仓已有 `libdivsufsort/2.0.1`（见 §2）⇒ **改为消费 Conan 依赖**，删除本 ExternalProject。

### 雷 2 —— `ExternalProject_Add(libcereal)`（CMakeLists.txt:241-257）**联网，但可关**

```cmake
find_package (Cereal 1.2.2)
if (NOT CEREAL_FOUND)
	message("Build system will fetch and build the Cereal serialization library")
	include(ExternalProject)
	ExternalProject_Add(libcereal
	    DOWNLOAD_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external
	    DOWNLOAD_COMMAND curl -k -L https://github.com/USCiLab/cereal/archive/v1.2.2.tar.gz -o cereal-v1.2.2.tar.gz &&
		tar -xzvf cereal-v1.2.2.tar.gz
	    ...
	)
	set(CEREAL_INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR}/external/install/include)
endif()
```

- 真实网络拉取（`curl -k -L https://github.com/USCiLab/cereal/...`），且 `curl -k` 跳过证书校验。
- **可关掉**：整块在 `if (NOT CEREAL_FOUND)` 内。只要 `cmake/Modules/FindCereal.cmake` 的
  `find_path(CEREAL_INCLUDE_DIR cereal ...)` 能在 Conan 注入的 `CMAKE_PREFIX_PATH` 上命中即跳过。
- 注意前置代码把 `CEREAL_ROOT` 默认为 `${GAT_SOURCE_DIR}/external/install`（不存在的目录），
  HINTS 落空但仍会继续搜 `CMAKE_PREFIX_PATH` ⇒ 由 Conan 提供 cereal 时可命中。
- ⚠ 风险：即便跳过 `find_package`，`ExternalProject_Add(libcereal)` 不生成 ⇒ 但 `rapmap` 目标上没有
  `add_dependencies(... libdivsufsort)`（只对 jemalloc 有 `if (${FETCHED_JEMALLOC})`），
  所以 cereal/divsufsort 的 ExternalProject target 若存在也只是挂在 `all` 上被构建。删除整块最干净。

### 雷 3 —— `ExternalProject_Add(libjemalloc)`（CMakeLists.txt:283-297）**联网，但可关**

```cmake
set (FAST_MALLOC_LIB "")
set (HAVE_FAST_MALLOC FALSE)
find_package(Jemalloc)
if (Jemalloc_FOUND)
    message("Found Jemalloc library --- using this memory allocator")
    set (FAST_MALLOC_LIB ${JEMALLOC_LIBRARIES})
    set (HAVE_FAST_MALLOC TRUE)
endif()
...
if (NOT HAVE_FAST_MALLOC)
    ExternalProject_Add(libjemalloc
        DOWNLOAD_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external
        DOWNLOAD_COMMAND curl -k -L https://github.com/COMBINE-lab/jemalloc/archive/4.5.0.tar.gz -o jemalloc-4.5.0.tar.gz &&
                         tar -xzf jemalloc-4.5.0.tar.gz
        SOURCE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/jemalloc-4.5.0
        BUILD_IN_SOURCE TRUE
        INSTALL_DIR ${CMAKE_CURRENT_SOURCE_DIR}/external/install
        CONFIGURE_COMMAND sh -c "${JEMALLOC_FLAGS} ./autogen.sh --disable-debug --prefix=<INSTALL_DIR>"
        INSTALL_COMMAND cp -r lib <INSTALL_DIR>/ && cp -r include <INSTALL_DIR>/
        )
    set (FAST_MALLOC_LIB ${CMAKE_CURRENT_SOURCE_DIR}/external/install/lib/libjemalloc.a)
    set (HAVE_FAST_MALLOC TRUE)
endif ()
```

- 真实网络拉取（`curl -k -L` 拉 COMBINE-lab fork 的 jemalloc **4.5.0** 并跑 `autogen.sh`）。
- **可关掉**：`find_package(Jemalloc)`（走 `cmake/Modules/FindJemalloc.cmake`，
  `find_path(JEMALLOC_INCLUDE_DIR jemalloc/jemalloc.h)` + `find_library(JEMALLOC_LIBRARY NAMES jemalloc libjemalloc)`）
  一旦 FOUND 就置 `HAVE_FAST_MALLOC=TRUE`，整块 ExternalProject 不生成。
- 且 `add_dependencies(rapmap libjemalloc)` 由 `if (${FETCHED_JEMALLOC})` 控制；
  `FETCHED_JEMALLOC` 在 CMakeLists 中**从未 set**（grep 无定义）⇒ 该 if 在 Configure 期展开为
  `if (${})` 即 `if ()` ⇒ 假，不生成依赖。这点要在 notes 里留痕，别误判成"一定会拉 jemalloc"。
- 制品仓已有 `jemalloc/5.3.0` ⇒ 消费之，本块删除。

**雷清点结论**：3 处 `ExternalProject_Add`，其中 1 处走本地 tarball、2 处真联网；
2 处真联网均被 `find_package` 开关保护，1 处无条件。三者的被拉物（divsufsort / cereal / jemalloc）
**全部已在制品仓发布** ⇒ 可全部转成 Conan 依赖、彻底离线。**无需联网绕过，不触发停止条件。**

---

## 2. 硬依赖核验（W0）

上游 `CMakeLists.txt` 的探测语句（原文）：

```cmake
95: set(GCCVERSION "5.2")
98: find_package(Threads REQUIRED)          # 硬失败
139:    if (APPLE AND NOT (GCC_VERSION VERSION_GREATER 5.2 OR ...)) → FATAL_ERROR（仅 GNU 分支）
142:    elseif (NOT (GCC_VERSION VERSION_GREATER 5.2 ...)) → "${PROJECT_NAME} requires g++ 5.2 or greater."
212: find_package (ZLIB REQUIRED)             # 硬失败
236: find_package (Cereal 1.2.2)             # 可选（未找到 → 联网拉取）
264: find_package(Jemalloc)                  # 可选（未找到 → 联网拉取 4.5.0）
```

`cmake/Modules/` 另含 `FindJellyfish.cmake` / `FindTcmalloc.cmake` / `FindSSE.cmake`，
但 **CMakeLists 中无任何 `find_package(Jellyfish|Tcmalloc|SSE)` 调用**（grep 已核）⇒ 死代码，不构成依赖。
`src/CMakeLists.txt` 里 jellyfish 的链接行也是注释状态（`#${GAT_SOURCE_DIR}/external/install/lib/libjellyfish-2.0.a`）。

分类表 + 制品仓对照探测原始输出（`conan download <ref> -r=ohpcd --only-recipe`；R35 禁用通配 `conan list`）：

| 依赖 | 上游用法 | 硬/软 | 制品仓结论 |
|---|---|---|---|
| `Threads` | `find_package(Threads REQUIRED)`，链接 `${CMAKE_THREAD_LIBS_INIT}`；另有 `-pthread` | **硬** | 系统线程库，由配方 `cpp_info.system_libs=["pthread"]` 声明，非 conan require |
| `zlib` | `find_package(ZLIB REQUIRED)` + `${ZLIB_LIBRARY}`/`${ZLIB_INCLUDE_DIR}` | **硬** | `zlib/1.3.1` **已发布** |
| `cereal` | `#include <cereal/...>`（8 个源文件 + 6 个头文件用），`find_package(Cereal 1.2.2)` | **硬**（缺则联网自拉） | `cereal/1.3.2` **已发布**；`cereal/1.2.2`、`cereal/1.3.0` **未发布** |
| `libdivsufsort` | `SUFFARRAY_LIB=<src>/external/install/lib/libdivsufsort.a`、`SUFFARRAY64_LIB=...divsufsort64.a` | **硬** | `libdivsufsort/2.0.1` **已发布**；`2.0.2` 未发布 |
| `jemalloc` | `${FAST_MALLOC_LIB}` 链进 `rapmap` | **软**（找不到就退化成自拉；真正的 fast-malloc 可选） | `jemalloc/5.3.0` **已发布** |
| `rt` / `m` / `gomp` | `${LIBRT}`（UNIX 非 APPLE）、`m`、`NON_APPLECLANG_LIBS=gomp` | 硬（`gomp` 见 §4） | 系统库，走 `system_libs` |

探测原始输出（同一次串行执行，含**已发布对照包**，用以区分"未发布"与"通道故障"）：

```
########## zlib/1.3.1 ##########            ← 对照（主代理已证已发布）
Connecting to remote 'ohpcd' anonymously   (仅前若干条打印此行)
Local Cache
  zlib
    zlib/1.3.1
      revisions
        2ee7c0eeb8f4dfef8982d0c5c1551a61 (2026-07-06 22:58:08 UTC)
########## cereal/1.3.2 ##########
  cereal/1.3.2  revisions  b1443a66f3ddf81fe9c79fa1b488b6ba (2026-07-28 07:06:27 UTC)
########## cereal/1.2.2 ##########
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]     ← 未发布形态
########## cereal/1.3.0 ##########
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]     ← 未发布形态
########## libdivsufsort/2.0.2 ##########
ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]     ← 未发布形态
########## libdivsufsort/2.0.1 ##########
  libdivsufsort/2.0.1  revisions  d3011db9217a2fff48647977f06d58c0 (2026-08-26 02:02:04 UTC)
########## jemalloc/5.3.0 ##########
  jemalloc/5.3.0  revisions  f3143c2dcb1911a6198e2542ce88b4b8 (2026-08-11 10:41:33 UTC)
```

⇒ **全部精确依赖已发布，无需 block 转手**。

制品仓侧 cpp_info 事实（决定 patch 写法，取自本地缓存配方原文）：

| 包 | 导出 |
|---|---|
| `cereal/1.3.2` | `libs=[]`（header-only）、`cmake_file_name=cereal`、`cmake_target_name=cereal::cereal`、`system_libs+=pthread` |
| `libdivsufsort/2.0.1` | components：`divsufsort`→`libs=["divsufsort"]`、target `divsufsort::divsufsort`；`divsufsort64`→`libs=["divsufsort64"]`、target `divsufsort64::divsufsort64`；`system_libs+=m` |
| `jemalloc/5.3.0` | `libs=["jemalloc"]`、`includedirs=["include","include/jemalloc"]`、`pkg_config_name=jemalloc`、`system_libs+=pthread,rt` |
| `zlib/1.3.1` | `libs=["z"]` |

> ⚠ `jemalloc` 的 `includedirs` 含 `include/jemalloc`，而 `FindJemalloc.cmake` 找的是 `jemalloc/jemalloc.h`
> 相对 `CMAKE_PREFIX_PATH` 根目录 ⇒ 头文件在 `<pkg>/include/jemalloc/jemalloc.h` 时可命中。
> 需实测确认 `find_package(Jemalloc)` 真的 FOUND（若未 FOUND 会退回联网拉取 ⇒ 必须拦掉）。

---

## 3. aarch64/OHOS 主要技术障碍（本包难点）

### 3.1 `x86 cpuid` 内联汇编（编译期硬失败）

`src/ksw2pp/KSW2Aligner.cpp:22-36` 定义了 `__cpuidex()`，两个分支都是 x86 汇编
（`cpuid` / `xchgl %%ebx`），仅被 `#ifndef _MSC_VER` 包住；`x86_simd()`（:45-59）调用它。
两个 `KSW2Aligner` 构造函数（:76-77、:101-102）**无条件**调用 `x86_simd()`。
⇒ aarch64 上 `cpuid` 指令无法汇编 ⇒ **必须按架构屏蔽**。
（`include/ksw2pp/KSW2Aligner.hpp:130-131` 中 `haveSSE41{false}` / `haveSSE2{false}` 默认 false，
非 x86 上 simd 检测返回 0 即可保持 false。）

### 3.2 SSE2/SSE4.1 函数符号在链接期缺失

- 所有 `src/ksw2pp/ksw2_*2_sse.c` 的函数体都在 `#ifdef __SSE2__ ... #endif` 内
  （实测 `ksw2_gg2_sse.c:4`、`ksw2_extz2_sse.c:4`、`ksw2_extd2_sse.c`、`ksw2_extf2_sse.c` 同构）
  ⇒ aarch64 上 `__SSE2__` 未定义（B 机 clang 实测探针 RC=0 且未触发 `#error SSE2_ON`），
  **不会有任何 intrinsic 被编译**，也就**不会定义** `ksw_extz2_sse2/_sse41/_sse`、`ksw_extd2_sse*`、`ksw_gg2_sse`。
- 但 `KSW2Aligner.cpp` 仍**无条件引用**这些符号（:221 `ksw_extz2_sse41`、:225 `ksw_extz2_sse2`、
  :285/:314 `ksw_gg2_sse`、:356/:360），且 `RapMapSAMapper.cpp` 真实使用 `ksw2pp::KSW2Aligner`
  （:83 include、:194-207、:421-434 构造并使用）⇒ 目标文件会被拉入 ⇒ **链接期 undefined symbol**。
- `-msse2` / `-msse4.1` 本身**不是**错误源：B 机 clang 15 实测仅
  `warning: argument unused during compilation: '-msse2' [-Wunused-command-line-argument]`，RC=0。
  （别把"看起来该报错"当结论。）
- 标量替身**签名完全一致**，可安全退化：
  - `src/ksw2pp/ksw2_gg2.c:4` `int ksw_gg2(km,qlen,query,tlen,target,m,mat,q,e,w,m_cigar_,n_cigar_,cigar_)`
    ≡ `ksw2.h:96` 的 `ksw_gg2_sse(...)` 形参表 ⇒ 一一对应。
  - `src/ksw2pp/ksw2_extz.c:5` `void ksw_extz(km,...,mat,gapo,gape,w,zdrop,flag,ez)`；
    上游自己在 `:228-231` 的非 SSE else 分支里就是拿 `ksw_extz(..., q, e, w, z, config_.flag, ez)`
    替换 `ksw_extz2_sse*`（丢弃 `end_bonus`）⇒ 本适配沿用**上游自身的**降级映射，不自创语义。
- ⇒ 方案：非 x86 时让 `ksw_extz2_sse*` / `ksw_gg2_sse` 调用点直接走标量 `ksw_extz` / `ksw_gg2`，
  并让 `ksw2pp_sse2` / `ksw2pp_sse4` 两个 OBJECT 库（唯一带 x86 flag 的目标）在非 x86 不生成。
  SIMD 内核（`ksw2_extd2_sse.c` / `ksw2_extf2_sse.c` / `ksw2_extz2_sse.c`）在非 x86 不进源列表。

### 3.3 `-march=native`（CMakeLists.txt:79，`if (NO_NATIVE_ARCH)` 可关）

制品要分发到别的 HarmonyOS aarch64 机器 ⇒ 保留 native 会把指令集钉死在构建机。
上游已提供 `NO_NATIVE_ARCH` 开关 ⇒ 配方传 `-DNO_NATIVE_ARCH=ON`（不新增平台判断，用上游自己的开关）。

### 3.4 GCC 版本闸门（CMakeLists.txt:137-144）

`if ("${CMAKE_CXX_COMPILER_ID}" MATCHES "GNU")` 分支里才检查 `g++ >= 5.2`；
OHOS 用 clang ⇒ 走 `elseif (MATCHES "Clang")` 分支（`set(CLANG TRUE)`、
`check_cxx_compiler_flag(-stdlib=libc++ HAVE_LIBCPP)`）。**不触发 g++ 5.2 FATAL_ERROR**。

### 3.5 RPATH / 安装前缀

- `src/CMakeLists.txt:44` `set(CMAKE_BUILD_WITH_INSTALL_RPATH TRUE)` +
  `CMAKE_INSTALL_RPATH "$ORIGIN/../lib:...:.../external/install/lib"` ⇒ 引用不存在的
  `external/install`，无害；Conan 会重定位 RPATH，需复核 L4 检查。
- `src/CMakeLists.txt:135-139`：`IF(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)` 会把前缀改成本身源码目录
  ⇒ Conan 总是显式传 `CMAKE_INSTALL_PREFIX`，不触发。**留痕防误判。**
- `install(FILES scripts/RunRapMap.sh ...)` 会把 bash 脚本装进 `bin/`（依赖 `samtools` 才走 BAM 分支）
  ⇒ 影响 L2 smoke 与 `bin/` 产物清单，需在 G4 前确认。

### 3.6 上游内部版本串与任务版本不一致（**如实申报，不改**）

`include/RapMapConfig.hpp:31` `constexpr char version[] = "0.6.0";`，
`current_version.txt` 也是 `VERSION_MAJOR 0 / MINOR 6 / PATCH 0` ⇒
`rapmap --version` 实际输出 `rapmap 0.6.0`，**不是** 0.15.0。
- 任务/Conan/归档目录/分支版本仍按硬要求取 **0.15.0**（= tag `salmon-v0.15.0`）。
- 不 patch 上游版本串（会污染 `RapMapSAIndex` 写出的索引头版本字段比对逻辑），
  改为在 notes / 验证报告里如实写明"二进制自报版本 0.6.0 是上游内部串"。

---

## 4. 已知待验证项（不预判结论）

- `gomp`：`CMakeLists.txt:122` `set(NON_APPLECLANG_LIBS gomp)`（非 APPLE 恒为 `gomp`），
  且 `rapmap` 链接 `${NON_APPLECLANG_LIBS}`。OHOS clang 用 libc++ + OpenMP 是 `libomp`（`-fopenmp=libomp`），
  **`-lgomp` 很可能找不到** ⇒ 首错候选。待 `conan create` 实测；若确为缺失需按证据处理
  （`-fopenmp=libomp` 或去 OpenMP 化），不得凭猜改框架。
- `zstr` / `spdlog` / `sparsepp` / `tsl` / `nonstd` / `tclap` / `picosha2` / `kseq.h` / `xxhash` / `edlib`
  全部**随包 vendor 在 `include/`**（已核对目录清单）⇒ 不需外部依赖。
- `include/digestpp` 存在但顶层 `digestpp/` 目录不存在（`include_directories(${GAT_SOURCE_DIR}/digestpp)` 落空）
  ⇒ 只要没有 `#include <digestpp/...>` 就无害，需实测确认。
- `check_ipo_supported(RESULT HAS_IPOHAS_IPO)`（`src/CMakeLists.txt:87`）拼写错误（少一个下划线），
  ⇒ `HAS_IPO` 永远未被设置，`if(HAS_IPO)` 恒假 ⇒ IPO 实际未开。**不改**（上游行为），留痕。

---

## 5. 上游测试清点（R51 第 1 步）

- `CMakeLists.txt:16` `enable_testing()`（在 `project()` 之前，但 CMake 允许）。
- `src/CMakeLists.txt:172-173` 注册 **2** 个 CTest 用例：

| 用例名 | 命令 | 内容 |
|---|---|---|
| `quasi_map_test` | `cmake -DTOPLEVEL_DIR=<src> -P cmake/TestQuasiMap.cmake` | `rapmap quasiindex -t transcripts.fasta -i sample_quasi_index` → `rapmap quasimap -t 2 -i sample_quasi_index -1 reads_1.fastq -2 reads_2.fastq -o sample_quasi_map.sam` → 断言 `.sam` 存在 |
| `quasi_map_test_ph` | 同上，`cmake/TestQuasiMapPerfectHash.cmake` | `quasiindex --perfectHash` + `quasimap` → 断言 `sample_quasi_map_ph.sam` 存在 |

- **语料已在包内**（`sample_data/`：`transcripts.fasta` 29213 B、`reads_1.fastq` / `reads_2.fastq` 各 1283063 B）
  ⇒ **测试不需要联网**，是真实的端到端功能测试（建索引 + 比对）。
- 无 `tests/` 目录、无 gtest/catch2；`TestingScripts/` 是人写的脚本目录（下一步核对是否可执行）。
- ⚠ 两个脚本用 `${CMAKE_BINARY_DIR}/rapmap` 定位二进制；`cmake -P` 脚本模式下
  `CMAKE_BINARY_DIR` 取当前工作目录，而 CTest 默认 WORKING_DIRECTORY = `add_test` 所在目录的
  binary dir（`<build>/src`），`rapmap` 恰好由 `src/CMakeLists.txt` 的 `add_executable` 产出到
  `<build>/src/rapmap` ⇒ 需在真机 ctest 实测确认，不凭推理下结论。
- 申报表（静态总数 / 可执行数 / 实测通过 / 跳过 / 失败）在实测后回填 §7，**不得预填**。

---

## 6. 适配路径

路径 A（配方适配，conan create 消费已发布的 zlib/cereal/libdivsufsort；
jemalloc 5.3.0 因 OHOS 包运行期 SIGSEGV 移出依赖，退化系统分配器——证据见 §8）。

---

## 7. 门禁与实测结果（2026-09-28 收尾-1B 回填）

- **conan-verify**：G0 PASS / G1 PASS / G2 PASS / G3 PASS，**Verdict: PASS**
  （生成物 `reports/conan-verify-report.md` 按 §19 **不随 PR、磁盘留档**；2026-09-28T00:41:56，"可标记 status: published"）。
  G4 产物完整性（L2 smoke / L4 checksec / L5 基线）随轮执行。
- **W3 本地 CI 模拟**：setup.sh 通过 + build_and_test.sh 通过
  （生成物 `reports/w3-local-ci.log` 按 §19 **不随 PR、磁盘留档**；即此前 FAIL 的 3600s 预算门，本轮绿）。
- **graph validate**：通过（540 条目 doc↔kv 配套完整，pending=0 failed=0）。
- **finish**：档案已关闭 → built（.build-closed 已建）；finalize 残留警告：
  debug tar.gz 未打包（单 Release profile，本地 packaging/ 仅 release tar.gz）。
- **测试五维数（上游 CTest）**：总数 2 / 执行 2 / 通过 2 / 失败 0 / 跳过 0
  （`100% tests passed, 0 tests failed out of 2`，conan-verify G2 轮
  生成物 `conan-create.log` 按 §19 不随 PR、磁盘留档，**本地留档行号 476**，W3 轮同口径复现）。
- **test_package 消费者断言**：27 通过 / 0 失败（生成物 `conan-create.log` 按 §19 不随 PR、磁盘留档，**本地留档行号 569**）。
- **补丁登记对账**：patches/ 实物 10 枚 = conandata.yml 登记 10 枚
  （0010 原漏登记，本次补齐并重写；manifest.yaml patches_applied 同步为 10）。

---

## 8. 收尾-1B 复绿记录（2026-09-28）

### 8.1 G2 首错链（两次）

1. **2026-09-26 轮（主窗）**：链接期 `ld.lld: error: undefined symbol:
   deflateInit2_`（继 deflateReset/inflateEnd/deflateEnd）——0010 补丁已生成但
   **未登记进 conandata.yml**，export 只带 9 枚补丁，`${ZLIB_LIBRARY}` 空变量
   未被替换为 `zlib::zlib` imported target ⇒ zlib 七符号未定义。
2. **2026-09-28 轮（补登记 0010 后）**：编译链接全过，ctest 阶段 2/2 Failed，
   手动复现 `rapmap quasiindex` **SIGSEGV（RC=139, core dumped）**；
   `rapmap --version` 同样 RC=139 ⇒ 崩溃在 main 之前的启动期，与业务逻辑无关。

### 8.2 启动 SIGSEGV 归因（二分实验，不碰 worktree）

- 设备 ptrace 被禁（gdb "ptrace: Permission denied"、lldb "'A' packet returned
  an error: 8"），core_pattern 指向 /（无权限落地）⇒ 调试器路线不可用，
  改 controlled-build 二分。
- 实验1（~/tmp/uc2/rapmap-nojem，去 jemalloc require）：configure 期被 0001 的
  FATAL_ERROR 防线拦下（jemalloc 必须找到）⇒ 证明 0001 语义是"jemalloc 强制"。
- 实验2（~/tmp/uc2/rapmap-nojem2，去 require + 0001 FATAL_ERROR→STATUS +
  0010 去掉 jemalloc::jemalloc 行）：**conan create 全绿**——
  `100% tests passed, 0 tests failed out of 2`、
  `rapmap consumer test: 27 passed, 0 failed`；二进制直测
  `rapmap --version` → `rapmap 0.6.0`（RC=0）、quasiindex RC=0 且索引产出。
- **结论**：OHOS jemalloc/5.3.0 包二进制可链接不可运行（allocator 初始化期
  崩溃）；zlib::zlib 无罪（实验保留它全绿）。HarmonyOS PC 保持系统分配器。

### 8.3 正式修复（全部入库，同步三处）

- 0010 重写：只链 `zlib::zlib`；jemalloc 位留注释说明实测证据。
- 0001：FATAL_ERROR → STATUS（无 jemalloc 时按系统分配器继续，防联网语义不变）。
- conanfile.py：删 `self.requires("jemalloc/5.3.0")`；docstring 补丁清单补全
  0004-0010；require 区注释记录决策。
- conandata.yml：0001/0010 描述同步改写；**0010 登记补齐（本任务起点欠账）**。

### 8.4 复绿证据

- 修复后 conan-verify 全绿（判决行见 §7）；W3 绿；finish 关档 built；
  packaging/rapmap-0.15.0-ohos-aarch64.tar.gz 打包（本地交付件，JC3 不入库）。
- 实验脚本留档：~/tmp/uc2/rapmap-nojem-exp.sh、rapmap-nojem2-exp.sh；
  实验日志：~/tmp/uc2/nojem-create.log、nojem2-create.log。

---

**编译结束**: 2026-09-28 00:46（收尾-1B 复绿并关档：2026-09-28 01:01）
**最终状态**: built
