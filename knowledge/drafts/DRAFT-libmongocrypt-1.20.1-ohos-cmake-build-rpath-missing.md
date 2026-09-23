# 真机 `uname -s` 是 HarmonyOS 而 CMake 只有 `Platform/OHOS.cmake`：Conan 的 CMakeToolchain 不写 `CMAKE_SYSTEM_NAME`，平台语义整链不加载 → `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 为空 → build-tree 可执行文件没有 RPATH，上游 ctest 里链接本包 `.so` 的用例必失败

> Draft: DRAFT-LIBMONGOCRYPT-1201-OHOS-CMAKE-BUILD-RPATH-MISSING
> Stem: `libmongocrypt-1.20.1-ohos-cmake-build-rpath-missing` — 与同 stem 的 `.kv` 成对
> 交付载体：`archives/l/libmongocrypt/1.20.1/conanfile.py` 的 `generate()`（`CMAKE_SYSTEM_NAME`）+ `build()`（`ctest`）

## 基本信息

- **严重度**: 2（🟡 medium：把"测试没通过"伪装成"缺依赖/符号没导出"，极易误修）
- **类别**: cmake, ohos, testing, linking, platform
- **触发工具**: cmake | ctest | ld | make | test
- **阶段**: testing（现象）← linking（真正缺的是搜索路径）
- **贡献者**: `iKalous_OscarP`（`draft: true`，未进图谱）

## 错误特征（真机原文，可直接比对）

```
4/8 Test #4: mc-dec128 ........................***Failed    0.02 sec
Error loading shared library libmongocrypt.so: (needed by .../build/Release/mc-dec128.test)

6/8 Test #6: example-state-machine ............***Failed    0.02 sec
Error loading shared library libmongocrypt.so: (needed by .../build/Release/example-state-machine)
Error relocating .../build/Release/example-state-machine: mongocrypt_new: symbol not found
Error relocating .../build/Release/example-state-machine: mongocrypt_init: symbol not found
...
```

文件明明就在同一目录（`.../build/Release/libmongocrypt.so`，5.4 MB），却"加载不了"；
后面那串 `symbol not found` 很容易被读成"上游没导出符号"或"要再补一个依赖"。

## 触发条件

四者同时成立即触发，与具体库无关：

1. 在真机（或任何 `uname -s` 返回 `HarmonyOS` 的环境）上用 Conan 的 `ohos-aarch64` profile 配置 CMake 工程 ——
   **`conan_toolchain.cmake` 里根本没有 `CMAKE_SYSTEM_NAME` 这一行**（实测
   `grep -in 'system_name' generators/conan_toolchain.cmake` 无输出，`CMakeCache.txt` 里也查不到该变量），
   于是 CMake 自己按 `uname -s` 得到系统名 `HarmonyOS`；
2. 项目构建了 `SHARED` 目标；
3. 上游用 `add_test(...)` 注册了**链接该 SHARED 目标**的测试/示例可执行文件；
4. 通过 `ctest` 在构建树里直接跑它们。

关键不对称：CMake 的 `Modules/Platform/` **有** `OHOS.cmake`（全文就一句 `include(Platform/Linux)`），
**没有** `HarmonyOS.cmake`。所以拼法差一个字，整条 `Platform/Linux.cmake` 语义链（`UNIX`、
`CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG`、SONAME flag、`find_package(Threads)` …）都不加载。

configure 日志里那句就是信号（下面这条来自本条目第 5 节的最小复现，与 libmongocrypt 无关）：

```
System is unknown to cmake, create:
Platform/HarmonyOS to use this system, please post your config file on discourse.cmake.org
```

**注意它只是警告，退出码仍为 0**，配置/编译/打包全部"成功"，问题只在 `ctest` 运行期暴露。

## 根因分析（机制 + 实测数字）

CMake 对"已知平台"会给构建树内的可执行文件写入 build-tree RPATH（指向所链接 .so 所在目录），
`ctest` 因此无需任何环境变量。这一动作的前提是 `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 有值
（`Platform/Linux.cmake:2` 里 `set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")`）。
平台模块没加载 → 该变量为空 → CMake **发不出** `-Wl,-rpath`，并且——这是关键——
**连显式设置的 `CMAKE_BUILD_RPATH` 也不会被翻译成链接参数**（它只是被忽略，不是被覆盖）。

真机 `llvm-readelf -d` 实测（同一构建目录）：

| 二进制 | DT_NEEDED | RPATH / RUNPATH | 结果 |
|---|---|---|---|
| `mc-dec128.test` | `libmongocrypt.so`, `libc++_shared.so`, `libc.so` | **无**（设置 `CMAKE_BUILD_RPATH` 之后复测仍然是"无"） | Failed |
| `mc-mlib.int128.test` | 同上 | 无 | Failed |
| `example-state-machine` | `libmongocrypt.so` 等 | 无（`link.txt` 里 `-Wl,-rpath` 出现 0 次） | Failed |
| `example-state-machine-static` | 只有 `libc.so`（静态版） | 不需要 | Passed |
| `test-mongocrypt` | 只有 `libc.so`（全静态） | 不需要 | Passed |

`CMakeCache.txt` 里 `CMAKE_SKIP_RPATH:BOOL=NO`、`CMAKE_SKIP_INSTALL_RPATH:BOOL=NO` ——
即**不是**谁把 RPATH 关了，而是根本没这个能力可用。

对照实验（唯一变量是搜索路径）：

```sh
cd <build/Release>
ctest -R '^mc-dec128$' --output-on-failure        # → Failed（Error loading shared library）
LD_LIBRARY_PATH="$PWD" ctest -R '^mc-dec128$' \
    --output-on-failure                            # → 立刻能跑
./mc-dec128.test                                   # 输出 @@ctest-skip@@ / "Decimal128 support is not enabled"，返回 0
```

也就是说这三条失败**不是**用例本身的问题、不是缺依赖、不是符号没导出，纯粹是加载器找不到
就在同目录下的那个 .so。同时 `static` 版本全通过，进一步反证了这一点。

## 最小复现（8 行 CMakeLists，把机制从任何具体库里剥出来）

同一台真机、同一个 clang、同一份 `CMakeLists.txt`，**唯一变量是 `-DCMAKE_SYSTEM_NAME`**：

```cmake
cmake_minimum_required(VERSION 3.15)
project(rpdemo C)
message(STATUS "PROBE SYS=[${CMAKE_SYSTEM_NAME}] RTF=[${CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG}] ...")
add_library(foo SHARED foo.c)
add_executable(bar bar.c)
target_link_libraries(bar foo)
enable_testing()
add_test(NAME bar COMMAND bar)
```

| 变体 | 配置参数 | configure 输出 | `bar.dir/link.txt` 里 `-Wl,-rpath` | `llvm-readelf --dynamic bar` | `ctest`（不给任何环境变量） |
|---|---|---|---|---|---|
| A | 无（模拟 Conan 现状：工具链不写 `CMAKE_SYSTEM_NAME`） | `System is unknown to cmake, create:` ×2，`SYS=[HarmonyOS] RTF=[] UNIX=[] CROSS=[FALSE]` | **0 次** | 只有 `NEEDED libfoo.so`/`libc.so`，**无 RPATH/RUNPATH** | **Failed** |
| B | `-DCMAKE_SYSTEM_NAME=OHOS` | `SYS=[OHOS] RTF=[-Wl,-rpath,] UNIX=[1] CROSS=[TRUE]`，无警告 | **1 次** | `(RUNPATH) Library runpath: [.../pt3/bB]` | **100% tests passed out of 1** |

复现脚本：`tools/probes/lmc_rpath2.sh`；诊断脚本：`tools/probes/lmc_plat.sh`、
`tools/probes/lmc_plat2.sh`、`tools/probes/lmc_plat3.sh`（`uname -s` → `HarmonyOS`、
`conan_toolchain.cmake` 无 `CMAKE_SYSTEM_NAME`、`Platform/OHOS.cmake` 内容 = `include(Platform/Linux)`、
`Platform/Linux.cmake:2` 定义 `-Wl,-rpath,`，四条均在其中打印）。

## 解决方案

**根因修法（一行，实测有效）**：在 `CMakeToolchain` 里显式给出 CMake 认得的那个拼法。

```python
tc.cache_variables["CMAKE_SYSTEM_NAME"] = "OHOS"   # 走 Platform/OHOS.cmake → Platform/Linux
```

副作用要知情：`CMAKE_CROSSCOMPILING` 由 `FALSE` 变 `TRUE`，`UNIX` 由未定义变 `1`，
上游凡按这两个开关路由的分支都会改变（本包实测 8 个 ctest 条目仍全部注册并执行，
`100% tests passed out of 8`，没有因交叉编译标记而静默少建用例）。

**兜底修法（本包同时保留）**：`build()` 里跑 ctest 时把构建目录交给动态链接器
（路径由 Python 侧拼成字面量）：

```python
libdir = _u(self.build_folder)
self.run('LD_LIBRARY_PATH="%s" ctest --output-on-failure' % libdir,
         cwd=self.build_folder, env="conanbuild")
```

- 不改上游 `CMakeLists.txt`、不加补丁、不改测试语义；
- 不是 `${CC}`/`${LDFLAGS}` 这类裸 shell 变量引用，因此不触发 CI 的 L0h/R33（该检查的
  正则是 `self\.run\(.*\$\{(CC|CXX|CFLAGS|CXXFLAGS|LDFLAGS|AR|RANLIB)\}`）；
- 上游 libmongocrypt 自己没有设置任何 RPATH（`grep -rn "RPATH" CMakeLists.txt cmake/` 无输出），
  在 Linux 上靠 CMake 的自动 build-tree RPATH 蒙对，到 OHOS 就暴露了——所以这属于**一类**上游
  未定义行为，不是本包特有。

打完这一步：`100% tests passed out of 8`（含 `test-mongocrypt` 294 个用例）。

## 通用性证据（不是"我写个 test_package 就算"）

- 同一轮里 **3 个不同上游目标**（C 示例 `example-state-machine`、C++ 测试 `mc-dec128.test`、
  C++ 测试 `mc-mlib.int128`）症状完全一致，且**只加环境变量**这一处改动就同时修好；
- 静态版 `example-state-machine-static` 与全静态 `test-mongocrypt` 在改动前后都通过 →
  排除"测试逻辑/依赖缺失"解释，唯一变量是 SHARED + 搜索路径；
- 机制证据来自 CMake 自己的日志（`System is unknown to cmake`）与 ELF 动态段，与 libmongocrypt 无关，
  任何"链接自身 .so 的上游 ctest"（如 `BUILD_TESTING=ON` 的 CMake 库）都会撞上；
- 反向验证：先设 `CMAKE_BUILD_RPATH=<构建目录>` 再 `readelf -d` → 依旧没有 RPATH/RUNPATH，
  证明该变量在此平台链路上是死路（这正是最容易踩的"看起来已经处理了"）。

## 查重反证（统计基线 = main tip `dfbc6f31b`，2026-09-19）

```sh
cd knowledge
ls -1 graph/E[0-9][0-9][0-9].kv | wc -l                       # 540（graph 目录 .kv 共 542 个）
ls -1 doc/*.md | wc -l                                        # 540
ls -1 drafts | wc -l                                          # 2378
grep -rli "CMAKE_BUILD_RPATH" graph/ doc/ drafts/ | wc -l     # 0
grep -rliE "BUILD_RPATH" graph/ doc/ | wc -l                  # 0（drafts/ 里 2 处是别的语境）
grep -ril 'RUNPATH' graph/*.kv | wc -l                        # >0，全部是"已安装产物缺 RUNPATH"类
```

**必须承认的相邻内容**：「CMake 平台模块按 `CMAKE_SYSTEM_NAME` 查找、HarmonyOS 拼法没有对应文件」
这一根因链条，知识库已有两条草稿写过 —— 所以本条目**不**声称发明了它；本条目的增量是
**断掉的具体语义（build-tree RPATH）+ 一套可执行的定位命令 + 一行根因修法 + 对 conan 侧归因的勘误**。

| 相邻条目 | 它讲什么 | 与本条目的边界 | 可执行反证 |
|---|---|---|---|
| `knowledge/drafts/DRAFT-E577-cmake-ohos-unix-guard-silent-drop.*` | 同一根因链，后果是 `if(UNIX)` 守卫的**整份实现被静默剔除**（链接期才暴露）+ 丢 `DT_SONAME` | 本条目后果在**运行期**：编译链接全对、符号也导出了，只是 `ctest` 起不来；断掉的变量是 `CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 而不是 `UNIX`/SONAME flag | 它的全文 `grep -c 'RUNTIME_C_FLAG\|rpath'` → 0；本条目 `grep -c 'if(UNIX)'` → 0 |
| `knowledge/drafts/DRAFT-cmake-harmonyos-platform-soname-flag.*` | 同一根因链，讲 `DT_SONAME` 缺失导致 `DT_NEEDED` 记成路径，主张链接期显式给 `-Wl,-soname` | 本条目 `DT_NEEDED` 干净（`readelf` 实测就是 `libmongocrypt.so`），缺的是**搜索路径**；修法是让平台模块加载（或给 `LD_LIBRARY_PATH`），与 patchelf/soname 无关 | 它 `grep -c 'ctest\|RUNPATH'` → 0；本条目 `readelf --dynamic` 显示 `NEEDED` 与文件名完全一致 |
| `knowledge/DRAFT-libharu-2.3.0-missing-dt-soname.{kv,md}`（在 `knowledge/` 根，不在 `drafts/`） | 缺 `DT_SONAME` → NEEDED 记成路径 | 同上：不同 ELF 字段、不同阶段 | `readelf --dynamic` 两条对照即可 |
| `E088`（ImportError / Error loading shared library / RUNPATH / patchelf） | **安装后**的 Python 扩展模块找不到依赖 .so，需要 patchelf 补 RUNPATH | 本条目发生在**构建树内跑上游 ctest**，产物尚未安装、不涉及 patchelf，也不是 Python；修法是一次环境变量或一行 CMake 变量而非改写 ELF | `grep -c "python\|patchelf" graph/E088.kv` = 9 > 0，而本条目场景里既无 python 也无 patchelf |
| `E267`（`CMAKE_SYSTEM_NAME=OHOS/HarmonyOS` 拼写导致项目侧平台判断漏掉） | **项目源码/模块层**按 `CMAKE_SYSTEM_NAME` 路由时少认一种拼法 | 本条目即使上游两种拼法都认也照样失败：缺的是 CMake 自身 `Modules/Platform/HarmonyOS.cmake`，与项目判断无关 | `grep -c "CMAKE_SYSTEM_NAME" CMakeLists.txt` 在上游 libmongocrypt 为 0，说明该库根本不做平台判断，失败依然发生 |

**对相邻两条草稿的一处勘误**（本条目实测）：`DRAFT-E577` 与 `DRAFT-cmake-harmonyos-platform-soname-flag`
的因果链第 ① 环都写成「Conan 的 OHOS profile 把 `os=OHOS` **映射为** `CMAKE_SYSTEM_NAME=HarmonyOS`」。
真机实测（conan 2.29.1 + `profiles/ohos-aarch64`）是：`conan_toolchain.cmake` 里
**没有任何 `CMAKE_SYSTEM_NAME` 赋值**，`CMakeCache.txt` 里也查不到；`HarmonyOS` 是 CMake
自己 `uname -s` 推出来的。归因差别会影响修法（改 conan 的映射 vs 在配方里补 `tc.cache_variables`），
建议主编把这一环改写为「Conan 不写 → CMake 回落到 host uname」。

结论：`CMAKE_BUILD_RPATH` / `BUILD_RPATH` 在 540 条正式条目 + 540 篇 doc 中 **0 命中**；
本条目独有的三段（`CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG` 为空 → build-tree 无 RPATH、
`ctest` 报 `Error loading shared library`/`symbol not found` 误导性错误、
8 行 CMakeLists 的 A/B 最小复现）在既有 540 条 + 2378 个草稿文件里都没有对应记录。

## 禁止做法

| 做法 | 为什么错 | 实测后果 |
|---|---|---|
| 设 `CMAKE_BUILD_RPATH` / `CMAKE_INSTALL_RPATH` 就当解决了 | 未知平台不启用该机制 | 设置后 `readelf -d` 依旧没有 RPATH/RUNPATH，ctest 仍 3 条失败 |
| 用 `ctest -E` 排除失败条目、或把测试改成只跑静态版换 CI 绿 | 掩盖真实执行数 | 声明数 > 实跑数，按 rule4/R51 判"少报"不通过 |
| 把 `Error relocating ... symbol not found` 当成"上游没导出符号"去改导出/加依赖 | 那只是 .so 没加载的连带报错 | 白改配方；实际只需给出搜索路径 |

## 证据

- 分支 `feat/libmongocrypt-1.20.1`，配方 `archives/l/libmongocrypt/1.20.1/conanfile.py`（`build()`）；
- 真机同一次 `conan create` 日志：`CREATE_EXIT:0` + `100% tests passed out of 8`；
- 失败态与通过态的差异只有 `LD_LIBRARY_PATH` 一项（上文对照实验）；
- 逐条 `readelf -d` 输出与失败日志见 `archives/l/libmongocrypt/1.20.1/notes.md` 问题表 #4。

## 元信息

- `draft: true`，`contributor_id: iKalous_OscarP`，`authors: iKalous_OscarP`
- 配套 `.kv`：`DRAFT-libmongocrypt-1.20.1-ohos-cmake-build-rpath-missing.kv`
- 姊妹条目（机制稿）：`DRAFT-LIBMONGOCRYPT-1201-OHOS-DLINFO-MISSING-DLADDR-PATH`
  （OHOS 上如何取"已加载库的路径"）
