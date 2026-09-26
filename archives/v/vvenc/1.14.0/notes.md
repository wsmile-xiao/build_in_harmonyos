# vvenc 1.14.0 适配笔记

## 编译环境

| 项 | 值 |
|----|----|
| 构建系统 | CMake 4.1.2（上游原生 CMake，未做构建系统替换） |
| 编译日期 | 2026-09-21 |
| 编译器 | Clang 15.0.4（OHOS SDK 26.0.0.18，`aarch64-linux-ohos`） |
| Conan | 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64` |
| 目标平台 | HarmonyOS / OpenHarmony PC aarch64（musl libc，`aarch64-linux-ohos`） |
| 状态 | published |
| 上游源码 | `https://github.com/fraunhoferhhi/vvenc/archive/refs/tags/v1.14.0.tar.gz` |
| 源码 sha256 | `dd43d061d59dbc0d9b9ae5b99cb40672877dd811646228938f065798939ee174` |

## 编译步骤

1. 用 `conan download` 验证依赖可消费性（W0 门禁）：本包**零强制第三方 Conan 依赖**，无需下载任何依赖包。
   - `libc++_shared.so` 由设备默认搜索路径解析（实测 `/system/lib64/libc++_shared.so` 存在），无需 recipe 处理。
2. 语言预检（R47）：`cpp`；prescan 无高危项。
3. `conan create`（recipe 内 `build()` 全流程）：
   - `apply_conandata_patches()` 依序应用 6 个补丁；
   - `cmake.configure()` 注入 6 个关键 cache 变量；
   - `cmake.build()`；
   - `cmake.test()` 运行上游 ctest 全量用例。

关键 configure 参数（recipe 中经 `tc.cache_variables` 注入，落为 CMakePresets 的 `-D`）：

```
-DCMAKE_SYSTEM_NAME="Linux"              # E092：绕过缺失的 Platform/HarmonyOS.cmake
-DVVENC_ENABLE_VERSIONED_SONAME="OFF"    # E050：避免软链形式的 SONAME 链
-DVVENC_TOPLEVEL_OUTPUT_DIRS="OFF"       # 产物不污染源码树
-DBUILD_SHARED_LIBS="ON"
-DVVENC_ENABLE_INSTALL="ON"
-DVVENC_INSTALL_FULLFEATURE_APP="ON"
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 构建至 87% 失败（exit 2）：`CommonDefX86.cpp:264:1: error: bad option 'no-tree-vectorize' to attribute 'optimize'; attribute ignored [-Werror,-Wignored-attributes]` | clang 同样定义 `__GNUC__`，但 clang 不支持 GCC 专有的 `optimize("no-tree-vectorize")` 属性串；上游 `VVENC_ENABLE_WERROR=ON` 将警告升级为错误 | 补丁 0003：`#if __GNUC__` → `#if defined( __GNUC__ ) && !defined( __clang__ )`（与归档 `vvdec/3.1.0` 同修复） |
| 2 | 上游 ctest 38/38 全败（`CTEST_EXIT=8`，每项 0.01s）：`Error loading shared library ../../lib/libvvenc.so` | **E092**：构建机 `uname` 报 HarmonyOS，Conan 将 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，而 CMake 4.1.2 无 `Platform/HarmonyOS.cmake` → 未知平台 → 丢失 `CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG` → `libvvenc.so` **无 SONAME** → 依赖方被写入相对路径 `DT_NEEDED` | recipe 中 `tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"`。**必须用 `cache_variables`**：`GenericSystemBlock` 注入被 `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫，只有 `-D` 能预先 DEFINED；`tc.variables`（写工具链文件内部）无法阻止注入。**消费者侧同样受影响**：`test_package/conanfile.py` 须在显式 `generate()` 中设同一 `cache_variables`，否则 configure 期仍打印 `System is unknown to cmake` 且消费者可执行文件丢失 RUNPATH |
| 3 | 加上 SONAME 后 ctest 仍全败：`Error loading shared library libvvenc.so.1.14` | **E050**：HMDFS 无法可靠创建/跟随符号链接。CMake 的 `VERSION`/`SOVERSION` 会生成 `libvvenc.so -> libvvenc.so.1.14 -> libvvenc.so.1.14.0` 软链链，exec 期动态加载器无法经软链解析 `DT_NEEDED`（而进程内 `dlopen`/`ctypes.CDLL` 可以） | 补丁 0001+0004：新增 `VVENC_ENABLE_VERSIONED_SONAME` 选项，OHOS 置 OFF 时**整体省略** `VERSION`/`SOVERSION` → 单个真实 `libvvenc.so` + `SONAME=libvvenc.so` |
| 4 | CMake `VERSION`/`SOVERSION` 语义陷阱：置为**空字符串**会生成畸形 `libfoo.so.` 且 `SONAME=libfoo.so.` | 空串非「省略」，CMake 仍然拼接版本后缀 | 用 `if( VVENC_ENABLE_VERSIONED_SONAME )` 包裹整体赋值，**不赋值空串**。实测三变体：unset → `libfoo.so` + `SONAME=libfoo.so` ✓；empty → `libfoo.so.` ✗；set → 软链链 ✗ |
| 5 | `.orig` 基线被污染：`diff -rq .orig .work` 显示 CMake 文件「一致」，实际 `orig_ino == work_ino`、`links=2` | `init-build` 的 `.orig`/`.work` 双轨使用**硬链接**共享 inode，就地编辑会同步改写 `.orig` 基线 | Python `os.unlink(.orig/F)` 断开硬链接 → 从 tarball 重新解压原始文件写回 `.orig`（恢复 sha256 `4b7af1cd…`/`b36b1a4b…`/`a0d07bd8…`），`.work` 内容保留 |
| 6 | 源码树被构建产物污染：出现 `.work/lib/release-shared/`、`.work/bin/release-shared/` | 上游 `VVENC_TOPLEVEL_OUTPUT_DIRS` 默认 ON，把产物写入 `${CMAKE_SOURCE_DIR}` | 固定 `-DVVENC_TOPLEVEL_OUTPUT_DIRS=OFF`；清理既有产物 |
| 7 | `conan create` 的 test_package 失败（`Error 127`）：`Error loading shared library libvvenc.so: Permission denied`（`dlopen`/`ctypes` 报同一 EACCES），但构建阶段 ctest 39/39 全通过 | **E504**：OHOS 的 clang/lld 在链接时给产物植入代码签名（`.note.ohos.ident` + `.codesign` 段），而 CMake install 期会**就地重写 `DT_RUNPATH`**（`.dynstr` 中 21 字节），签名随即失效。OHOS 内核校验签名不匹配 → `mmap(PROT_EXEC)` 返回 EACCES。构建树副本未被改写，所以 ctest 通过；只有安装后的包内 `.so` 不可加载。上游 `CMakeLists.txt:441` 在 shared 构建下自行设置 `CMAKE_INSTALL_RPATH`（`$ORIGIN`、`$ORIGIN/../lib`），故改写必然发生 | `-DCMAKE_BUILD_WITH_INSTALL_RPATH=ON`：链接时即写入安装期 RPATH → install 阶段 CMake 检测到已正确 → **完全跳过改写** → 安装产物与链接产物逐字节一致 → 签名有效。优于 `CMAKE_SKIP_INSTALL_RPATH`（后者会丢失上游的可重定位 RPATH） |

> 排查方法学（问题 3）：用最小复现矩阵 T1–T9 把失败从「CMake 平台」逐层收窄到「HMDFS 不跟随软链」——T8（SONAME + 真实文件）`exit=0`；**T9（SONAME + 软链）`exit=127`**；硬链接对照 `exit=0`；`ctypes.CDLL` 走软链目录 OK。**关闭沙箱后复现结果一致**，据此排除沙箱因素、确认为设备/HMDFS 行为。与归档 `archives/c/cling/1.3/patches/0004-llvm-cmake-no-versioned-shared-symlinks-on-ohos.patch`（`Knowledge-Ref: E050`，原文 "HMDFS cannot reliably create or follow those symlinks"）互相佐证。

## 源码修改

共 6 个补丁，全部经「在纯净 tarball 解压树上按序应用 → 与 `.work` 逐字节比对」验证。

| 补丁 | 文件 | 行数 | 内容 |
|------|------|------|------|
| 0001 | `CMakeLists.txt` | +10/-0 | 新增 `VVENC_ENABLE_VERSIONED_SONAME` 选项（默认 ON，OHOS 下由 recipe 置 OFF） |
| 0002 | `cmake/modules/vvencTests.cmake` | +6/-0 | 注册新增的鸿蒙消费者用例 `Test_vvencohoscapptest` |
| 0003 | `source/Lib/CommonLib/x86/CommonDefX86.cpp` | +1/-1 | GCC 专有 `optimize` 属性串加 clang 守卫 |
| 0004 | `source/Lib/vvenc/CMakeLists.txt` | +14/-2 | 将 `VERSION`/`SOVERSION` 移入 `if( VVENC_ENABLE_VERSIONED_SONAME )`，OHOS 下整体省略 |
| 0005 | `test/vvencohoscapptest/CMakeLists.txt` | 新增 39 行 | 新用例构建文件（仿 `vvencinterfacetest` 结构） |
| 0006 | `test/vvencohoscapptest/vvencohoscapptest.c` | 新增 315 行 | 鸿蒙消费者用例（见下） |

### 新增鸿蒙测试用例

`test/vvencohoscapptest/vvencohoscapptest.c`（7 项检查）承担两类断言：

1. **运行时链接完整性**：用 `dladdr()` 取 `libvvenc` 的实际映射路径，断言其为**常规文件**（`stat`）、**非符号链接**（`lstat`）、运行时名为 `libvvenc.so*`。这直接固化本次 E050 修复的契约——OHOS 上不得出现版本化软链。
2. **消费者用例（测试可行性）**：`vvenc_encoder_create` → `vvenc_encoder_open` → `vvenc_encoder_get_config`，编码 176×144 合成 YUV420 共 8 帧并 flush，断言输出 AU 数 > 0、码流字节数 > 0。

OHOS 专属断言以 `#if defined( __OHOS__ )` 守卫，保证同一份用例在其它平台仍可编译。

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| 第三方 Conan 依赖 | 无 | W0 门禁 `preflight_check.sh vvenc/1.14.0` → `EXIT=0`（零强制依赖） |
| libc++ | OHOS SDK 26.0.0.18 自带 | 设备默认路径 `/system/lib64/libc++_shared.so` |
| pthread | musl libc 内置 | `Threads::Threads` |

## 验证结果

### 上游测试（真实执行，独立统计）

```bash
ctest -N                                   # 枚举
ctest --output-on-failure                  # 全量执行
```

共享库构建（`BUILD_SHARED_LIBS=ON`），由 `conan create` 的 `build()` → `cmake.test()` 真实触发：

- 用例总数：**39**
- 通过：**39**
- 失败：**0**
- 跳过：**0**
- 结果：`100% tests passed, 0 tests failed out of 39`
- 耗时：`Total Test time (real) = 26.16 sec`（独立复跑 26.52 / 26.74 / 26.16 sec）
- 新增用例：`2/39 Test #2: Test_vvencohoscapptest ... Passed 0.13 sec`
- 日志：`logs/vvenc-ctest-list4.log`、`logs/vvenc-ctest-run4.log`、`logs/vvenc-conan-create3.log`

> 说明：本包为**库 + CLI** 形态，上游 ctest 覆盖库接口（`vvencinterfacetest`、`vvenclibtest` 6 项）与 CLI 工具（`vvencapp`/`vvencFFapp` 的 31 项参数化编码 + 输出比对），末项 `Cleanup_remove_temp_files` 收尾。

### test_package（消费者用例，独立于上游测试）

```bash
conan create <recipe> -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

```
vvenc test_package (consumer use case)
PASS vvenc_get_version() matches the VVENC_VERSION build macro
     mapped from: <package>/lib/libvvenc.so
PASS libvvenc maps to a regular file
PASS libvvenc is a real file, not a symlink (HMDFS cannot follow symlinks, E050)
     176x144, 8 frames -> 8 access units, 625 bitstream bytes
PASS public encoder API round trip produces a non-empty VVC bitstream
RESULT PASS: 0 of 4 check(s) failed
```

### 新增鸿蒙用例独立执行

用例 `Test_vvencohoscapptest` 已由补丁 0002 注册进上游 ctest 套件（`ctest -R Test_vvencohoscapptest -V`，退出码 0）：

```
vvenc HarmonyOS/OHOS consumer test
     vvenc_get_version() = 1.14.0, VVENC_VERSION = 1.14.0
PASS vvenc_get_version() matches the VVENC_VERSION build macro
--- runtime linkage integrity ---
     mapped from: .../build/Release/lib/libvvenc.so
PASS libvvenc maps to a regular file
PASS libvvenc is a real file, not a symlink (HMDFS cannot follow symlinks, E050)
PASS libvvenc is reachable under its unversioned runtime name
--- consumer use case: public encoder API round trip ---
     176x144, 8 frames, preset VVENC_FASTER, qp 32
     access units produced = 8, bitstream bytes = 667
PASS encoder API round trip returns 0
PASS at least one access unit was produced
PASS the produced VVC bitstream is non-empty
RESULT PASS: 0 of 7 check(s) failed
```

日志：`archives/v/vvenc/1.14.0/reports/ohos-testcase.log`（7/7 PASS）；套件内运行时序见 `reports/w3-local-ci.log:402-403`。整条上游套件（39 项）逐项输出见 `reports/w3-local-ci.log:400-481`。

### 安装树与 ELF 核验

```bash
readelf -d <prefix>/lib/libvvenc.so | grep SONAME   # SONAME=libvvenc.so
find <prefix> -type l | wc -l                        # 0
```

- `SONAME=libvvenc.so`、`DT_NEEDED=libvvenc.so`（无版本后缀、无相对路径）
- 安装树软链数 = **0**（`find <install-prefix> -type l | wc -l`）
- `CMAKE_INSTALL_RPATH=$ORIGIN;$ORIGIN/../lib`

### E504 修复验证（install 不改写、签名保持有效）

```bash
cmake -S <src> -B <build> -DCMAKE_BUILD_WITH_INSTALL_RPATH=ON
cmake --build <build>
cmake --install <build> --prefix <prefix>
```

| 检查项 | 结果 |
|--------|------|
| 构建树 `libvvenc.so` RUNPATH | `[$ORIGIN:$ORIGIN/../lib]`（链接期即写入） |
| 构建树 sha256 | `b4d153be858ab59f41469ebd23c92e4cea4b1027b39d40e5c2011ac7324f0b54` |
| 安装后 sha256 | `b4d153be858ab59f41469ebd23c92e4cea4b1027b39d40e5c2011ac7324f0b54`（**逐字节一致**） |
| 安装后 `ctypes.CDLL` | `LOAD OK` |
| 安装后 `vvencapp --help` | `EXIT=0` |

对照（未加该参数的旧行为）：构建树与安装产物**仅差 21 字节**（RPATH 改写），安装后加载报 `Permission denied`。对该 .so 追加 `binary-sign-tool sign -selfSign 1` 后立即恢复可加载，反向证明根因是签名失效。

日志：`logs/vvenc-wbir-probe2.log`、`logs/vvenc-tp-dlopen.log`、`logs/vvenc-tp-sign.log`、`logs/vvenc-tp-buildtree.log`

### 补丁可应用性

在纯净 tarball 解压树上按 0001→0006 顺序应用，6 个补丁全部 `apply=0`，且结果与 `.work` **逐字节一致**。

## 发现与知识

> 本节每条均已沉淀为知识图谱条目；条目 ID 见行尾 `ref`（`E063`/`E092`/`E050`/`E504` 为既有官方条目，`E429` 为本次新增草稿 `knowledge/drafts/E429-draft-7B94`）。

- ✅ **E063 族（clang 的 `__GNUC__` 假象）**：clang 同样定义 `__GNUC__`，却不支持 GCC 专有的 `optimize("no-tree-vectorize")` 属性串；上游 `VVENC_ENABLE_WERROR=ON` 会把 `-Wignored-attributes` 升级为 error。补丁 0003 以 `#if defined( __GNUC__ ) && !defined( __clang__ )` 守卫，与归档 `vvdec/3.1.0` 同一修复。（ref: E063）
- ✅ **E092（CMake 无 `Platform/HarmonyOS`）**：CMake 4.1.2 只有 `Platform/OHOS.cmake`（内容即 `include(Platform/Linux)`），没有 `Platform/HarmonyOS.cmake`；而 OHOS 适配版 Conan 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`，构建机自身 `uname` 也报 HarmonyOS，于是落到未知平台，丢失 Linux 平台语义（无 `-Wl,-soname`、无 rpath 基址），可执行文件的 `DT_NEEDED` 记录相对路径。（ref: E092）
- ✅ **E092 落地要点**：必须走 `tc.cache_variables`（→ `CMakePresets.json` 的 `-D`）。`GenericSystemBlock` 的注入被 `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫，只有预置 cache 才能阻止 HarmonyOS 注入；`tc.variables` 写入工具链文件内部、不阻止注入。消费者侧同样受影响。（ref: E092）
- ✅ **E050（HMDFS 不跟随软链）**：HMDFS 无法可靠创建/跟随符号链接；exec 期动态加载器无法经软链解析 `DT_NEEDED`（进程内 `dlopen` 却可以，最小复现 T9 `exit=127` vs T8 `exit=0`）。CMake 的 `VERSION`/`SOVERSION` 会产生软链链，导致上游用例全败。（ref: E050）
- ✅ **`VERSION`/`SOVERSION` 语义陷阱**：必须在 CMake 中**整体省略**，不可置空字符串——置空生成畸形 `libvvenc.so.` 与 `SONAME=libvvenc.so.`；省略后得到单个真实文件与 `SONAME=libvvenc.so`。（ref: E050）
- ✅ **E504（install 期 RPATH 改写破坏 OHOS 代码签名）**：OHOS clang/lld 在链接期植入 `.note.ohos.ident` + `.codesign`；CMake install 期对 `DT_RUNPATH` 做就地改写（本例 `.dynstr` 仅 21 字节），签名随即失效，内核拒绝 `mmap(PROT_EXEC)`，报 `Error loading shared library <lib>: Permission denied`。判据：构建树副本可加载而安装副本不可加载，且二者仅有 RPATH 差异。（ref: E504）
- ✅ **E504 落地**：设 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON`，链接期即写入安装期 RPATH → install 检测到已正确 → 完全跳过改写 → 安装产物与链接产物逐字节一致、签名有效、无需 `binary-sign-tool`。相比 `CMAKE_SKIP_INSTALL_RPATH`（会丢弃上游可重定位 RPATH）语义偏差更小。（ref: E504）
- ✅ **上游 RPATH 来源**：上游 `CMakeLists.txt:436-442` 在 `BUILD_SHARED_LIBS AND NOT WIN32` 时自行设置 `CMAKE_INSTALL_RPATH`（`$ORIGIN`、`$ORIGIN/../lib`），故 shared 构建下 install 期改写必然发生。（ref: E504）
- ✅ **C++ 运行时与源码树工程约定**：`libc++_shared.so` 由设备默认搜索路径解析（`/system/lib64/libc++_shared.so`），无需 `LD_LIBRARY_PATH`；上游 `VVENC_TOPLEVEL_OUTPUT_DIRS` 默认 ON 会污染源码树，必须置 OFF；上游测试入口为 `cmake/modules/vvencTests.cmake` 的 `add_test`，shared 构建基线为 39 项。（ref: E429）

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `lib/libvvenc.so` | 3,590,656 B | 单一真实（非软链）共享库，`SONAME=libvvenc.so` |
| `bin/vvencapp` | 772,608 B | 上游标准 CLI 编码器 |
| `bin/vvencFFapp` | 821,760 B | 上游全功能 CLI 编码器 |
| `lib/pkgconfig/libvvenc.pc` | — | pkg-config 导出 |
| `include/vvenc/` | — | 公共头文件 |

Conan 包导出目标：`vvenc::vvenc`（库）、`vvenc::vvencapp`（CLI）。

## 注意事项

1. **不要把 `VERSION`/`SOVERSION` 置为空字符串**——必须整体省略，否则生成畸形 `libvvenc.so.` 及同名 SONAME。
2. **`CMAKE_SYSTEM_NAME` 必须走 `tc.cache_variables`**。写进 `tc.variables` 会被 `GenericSystemBlock` 的 `if(NOT DEFINED CMAKE_SYSTEM_NAME)` 守卫绕过，HarmonyOS 平台名照样注入。
3. **HMDFS 环境下禁止任何版本化软链形式的运行时依赖**。若后续上游引入新的 `VERSION`/`SOVERSION` 或 `install` 软链，需一并纳入 `VVENC_ENABLE_VERSIONED_SONAME` 守卫。
4. 本包为「库 + CLI」混合形态：`package_type = "library"`，`cpp_info.bindirs = ["bin"]`，`default_options = {"shared": True, "fPIC": True}`。
5. 上游 `VVENC_ENABLE_WERROR` 默认 ON，新增代码必须零警告，否则 `-Werror` 直接失败（本次新增用例即因未使用函数 `msgApp` 触发 `-Werror,-Wunused-function`，已删除）。

## 对话记录

### 对话 #1 — 任务下发、Git 分支与工作树建立

- **用户要求**：先加载编译 SKILL；任务第一步「远程 fork 与上游同步 → 本地 main 与远程 fork 同步 → 从 main 新建分支 `feat/vvenc-1.14.0` → 在该分支建立 worktree → 在 worktree 内工作」；所有依赖须经 `conan download` 验证可消费，任一不可消费立即 STOP 并报 R36，不得用本地缓存或 `--build=missing` 绕过；只处理目标库自身文件；并声明工作区可能存有其他库的未提交修改，无需处理、只要最终不提交相关文件。
- **结果**：SKILL 加载完成，分支与 worktree 就绪；W0 门禁确认本包**零强制第三方 Conan 依赖**，无 R36 阻塞。

### 对话 #2 — OHOS 平台适配与三条平台修复

- **用户要求**：每一步展示真实命令、原始输出、退出码、日志路径、首个错误、根因、修复与重新验证结果。
- **结果**：完成源码与上游测试入口核验，并落地三条平台修复——E063 族（clang 属性守卫）、E092（`CMAKE_SYSTEM_NAME=Linux` 经 `tc.cache_variables`，含消费者侧）、E050（关闭版本化 SONAME）。

### 对话 #3 — 上游测试独立汇报与新增鸿蒙用例

- **用户要求**：上游测试必须实际执行并单独汇报（测试命令、用例总数、通过数、失败数、跳过数、每项用例名称与日志路径），且 test_package 不得替代上游测试统计；适配后必须至少新增一个鸿蒙消费者用例以验证测试可行性。
- **结果**：上游 ctest 以 shared 构建真实执行 **39/39 通过**（0 失败 / 0 跳过），`reports/test-report.md` 记录每项用例名称与耗时；新增 `Test_vvencohoscapptest` 用例独立执行 **7/7 通过**。

### 对话 #4 — E504 根因定位与编译收尾（finish / W3 / W2）

- **用户要求**：完成 `conan create`、`conan-verify`、`finish`、W2/W3 与 PR 文件原子性检查；在 commit、push、Issue、PR、上传制品或远端 Review 前停止并等待确认。
- **结果**：以「包内 `.so` 与构建树 `.so` 仅差 21 字节 → `ctypes.CDLL` 报 EACCES → 自行签名后立即 LOAD OK」三段证据链确证 E504，并采用 `CMAKE_BUILD_WITH_INSTALL_RPATH=ON` 修复；`conan create`（上游 39/39 + test_package 4/4）、`conan-verify`（G0–G4 全 PASS）、W3 本地 CI（L0/L1/L2/L4/L5 全 pass）相继通过。W3 曾一度被本机 safe-delete 守卫误拦（Conan 清理 `test_package/build` 64 条目 > 阈值 50），经确认采用**环境侧放行**后通过。提交动作按约定保持等待，未执行任何远端操作。
---

**编译结束**: 2026-09-21 20:11
**最终状态**: published
