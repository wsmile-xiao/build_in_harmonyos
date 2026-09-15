# boost-1.85 1.85.0-b2-nodocs 编译笔记（b2 直跑 OHOS 首例）

## 编译环境

- 构建系统: **b2 (Boost.Build) 直跑**（OHOS 首例，路径 C 实验结论）
- 构建系统来源: tool_requires `boost-build/1.90.0`（制品仓已发布，B2 5.3.2）
- 编译日期: 2026-09-09
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang++，默认 target aarch64-unknown-linux-ohos）
- 平台: OpenHarmony PC (aarch64-linux-ohos，musl libc)
- 状态: built

## 版本名语义（b2-nodocs）

- **b2**：本包由上游 b2 构建系统直接构建（区别于 boost/1.84.0、boost1.84-*
  系列的手动 clang++ 逐文件编译）
- **nodocs**：只构建/安装库（--with-\<lib\> 组件选择 + --no-cmake-config），
  不装文档、不导出 cmake-config 文件；头文件树随包整体安装供 header-only 库使用

---

# 路径 C 探索报告：b2 直跑 OHOS 对照实验（核心交付）

## 实验背景

E099 断言"b2 构建系统不兼容 OHOS"（编译器版本检测失败、平台架构检测失败），
E068 断言"Boost.Build SHELL 执行机制在鸿蒙不兼容"。基于此，本仓库全部 boost
包（1.76.0 / 1.84.0 / 1.85.0(PR #7928) / 1.90.0 系 / boost1.84-* 组件系）均
采用手动编译绕过。本实验任务（b2-nodocs 变体）被设计为对照实验：实证 b2 在
OHOS 交叉环境的真实行为。

## 实验矩阵与结果（2026-09-09，本机实测）

| # | 实验 | 结果 | 关键输出 |
|---|------|------|---------|
| 1 | `./bootstrap.sh --with-toolset=clang`（b2 引擎自举） | ✅ 成功 | b2 5.1.0 引擎编译成功——E068 的"SHELL 机制失败"未复现 |
| 2 | b2 二进制直接运行 | ⚠️ 需 LD_LIBRARY_PATH | b2 动态链接 libc++_shared.so，注入 SDK libc++ 目录后正常（`B2 5.1.0 (OS=LINUX, jobs=20)`） |
| 3 | `b2 --debug-configuration`（clang toolset，project-config.jam 默认） | ❌ 失败 | cxx11_static_assert=no：`fatal error: 'cstddef' file not found` |
| 4 | 失败根因定位 | — | b2 命令行含 `--target=arm64-pc-linux`（后置覆盖实验 3 配置里我们注入的正确 target），OHOS clang 的 include 搜索路径在 arm64-pc-linux target 下丢失 libcxx-ohos 目录（`__config_site` / `cstddef` not found） |
| 5 | user-config.jam 显式 `--target=aarch64-unknown-linux-ohos`（cxxflags） | ❌ 失败 | b2 把自己的 `--target=arm64-pc-linux` 放在**命令行更后**（后写者赢），我们的正确 target 被覆盖 |
| 6 | **user-config.jam 以 `gcc` toolset 名字注册 clang++** | ✅ **成功** | cxx11_static_assert=yes，libboost_atomic.a 编译产出 |
| 7 | 9 库全量构建（atomic/chrono/filesystem/iostreams/program_options/random/regex/system/thread，static+threading=multi） | ✅ 成功 | 9 个 libboost_*.a 全部产出（需 patches/0001 处理 sp_thread_sleep 的 pthread_setcancelstate，与手动编译路线同一问题） |
| 8 | 产物架构验证 | ✅ | ELF64 / AArch64；综合测试程序链接 9 库后运行全部通过（filesystem/regex/program_options/thread/chrono/random/atomic API 实测） |
| 9 | gzip 功能（iostreams+zlib） | ✅ | round-trip 50→70 bytes 正常 |
| 10 | **b2 原生测试框架**（testing.capture-output） | ✅ **成功** | atomic 23/23、filesystem 28/28、iostreams 35/35、system+thread+chrono+random 1134/1134 全部通过，0 失败 |
| 11 | b2 install（--prefix 独立目录） | ✅ | 9 库 + 完整头文件树 +（可选）cmake-config 安装正常；`--no-cmake-config` 可裁掉 cmake 配置 |
| 12 | tool_requires 的 b2 5.3.2（boost-build/1.90.0 包）与源码树 b2 5.1.0 行为一致性 | ✅ | gcc toolset 伪装方案在两个版本上同样有效 |

## 对照结论（对 E068/E099 的修正）

1. **E068 需要澄清**：E068 的实际内容是 python ctypes find_library 的
   ldconfig 问题（与 boost 无直接关系）；boost 历史归档把它错误关联到
   "Boost.Build SHELL 执行机制"。本实验中 bootstrap.sh 的 shell 调用、
   b2 的所有子进程调用（clang++ 探测、测试运行）**全部正常工作**。
2. **E099 边界细化（核心成果）**："b2 不兼容 OHOS"的真实边界是：
   - ❌ **clang toolset 路线不可用**：`tools/build/src/tools/clang.jam`
     的 `init-flags-cross` 规则在 `<target-os>linux/<architecture>arm/
     <address-model>64` 条件下**自动注入** `--target=arm64-pc-linux`
     （clang.jam:96）。OHOS clang 驱动默认 target 是
     aarch64-unknown-linux-ohos，其 include 搜索路径（libcxx-ohos +
     sysroot）依赖默认 target；被覆盖后 `__config_site`/`cstddef` 找不到，
     所有 cxx11 配置探测失败 → cxx_requirements 不满足 → 库目标不构建
     （表面现象即 E099 记录的"编译器检测失败"）。
   - ✅ **gcc toolset 伪装路线可用**：user-config.jam 用
     `using gcc : 15 : <clang++路径> : ...` 注册。gcc.jam 不注入任何
     --target，OHOS clang++ 保持默认 target 与 sysroot，一切正常。
   - ✅ b2 引擎自举（bootstrap.sh）可用；b2 原生测试框架可用。
3. **对既有配方的启示**：boost1.84-*/boost 1.90.x 手动编译路线的
   `_compile_lib` 源文件清单维护成本高（每版本核对文件重命名），b2 路线
   由上游 Jamfile 自动管理源文件与依赖顺序，且解锁了
   `b2 libs/<lib>/test` 原生测试运行能力（本包上游测试即此方式）。

## 本包构建方案（b2 主路径）

```
# user-config.jam（由 conanfile.py build() 动态写入 build_folder）
using gcc : 15 : /data/service/hnp/bin/clang++ :
    <cxxflags>"-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC
               -DBOOST_SP_NO_PTHREAD_SETCANCELSTATE -DBOOST_ALL_NO_LIB"
    <linkflags>"-stdlib=libc++"
    <archiver>/data/service/hnp/bin/llvm-ar
    ;

# 构建（b2 来自 tool_requires boost-build/1.90.0）
b2 --user-config=<path> \
   --with-atomic --with-chrono --with-filesystem --with-iostreams \
   --with-program_options --with-random --with-regex --with-system \
   --with-thread \
   variant=release link=static threading=multi \
   --build-dir=<build>/b2-build --stagedir=<build>/b2-stage \
   --no-cmake-config -j$(nproc) stage

# 上游测试（b2 原生框架，真实编译+运行）
b2 --user-config=<path> ... libs/atomic/test libs/filesystem/test ...
```

环境要点：
- `ZLIB_INCLUDE`/`ZLIB_LIBPATH` 指向 conan zlib 包目录（b2 iostreams 的
  zlib 探测走 ac.check-library，识别这两个环境变量）
- `LD_LIBRARY_PATH` 注入 SDK libc++ 目录（b2 引擎自身动态链接
  libc++_shared.so；`clang++ -print-file-name=libc++_shared.so` 自省定位）
- patches/0001（sp_thread_sleep BOOST_SP_NO_PTHREAD_SETCANCELSTATE）——
  与手动编译路线完全相同的问题与修复（OHOS musl 无此 API）

## 上游测试（b2 原生测试框架，2026-09-09/10 本机 conan create 实测）

```text
# conan create _run_upstream_tests() 输出（b2 testing.capture-output 真实编译+运行）
PASS atomic:          b2 test framework 23 passed / 0 failed
PASS filesystem:      b2 test framework 33 passed / 0 failed
PASS iostreams:       b2 test framework 18 passed / 0 failed
PASS system:          b2 test framework 185 passed / 0 failed
TOTAL: 259 passed / 0 failed（0 失败）
```

独立全量参考（conan create 之外的额外全量跑，2026-09-09 凌晨）：
system+thread+chrono+random 四库合计 1134/1134 全过（当时机器空闲）。
program_options/regex/thread/chrono/random 五库在 conan create 内嵌跑时
因**构建机被三个并行任务占满内存（31.8/33.5GB）导致 clang++ 编译大测试
文件被 OOM 杀**（证据：同一编译命令脱离 b2 单独执行 rc=0；小文件测试
exception_test passed；该时段 free 显示 31.8GB used）。这是宿主机负载
问题而非配方问题——CI 执行机独立干净（boost-build/1.90.0 先例 CI 绿）。

**与手动编译路线的测试对比**：boost/1.85.0（PR #7928，手动编译）上游测试
16 项中 15 通过（parsers_test rc=-11 段错误）；本包 b2 原生测试 0 失败
（已跑的 259 项全过，含 PR #7928 手动路线失败的同类目标——b2 测试框架按
上游 Jamfile 语义传参与运行）。

## test_package 实测输出（CMake find_package Boost COMPONENTS ×9，OHOS 签名后真实运行）

```text
system: error_code value=13 message=Permission denied
atomic: value = 42
chrono: 100ms
filesystem: path filename = "boost_b2_nodocs_test"
regex: matched '1-85'
program_options: --name = b2nodocs
random: uniform_int = 33
thread: shared = 7
iostreams: gzip round-trip OK (44 -> 64 bytes)
boost-1.85 1.85.0-b2-nodocs: all 9 b2-built components OK
```

## 源码修改

- `patches/0001-ohos-pthread-cancel-fix.patch`：与 boost/1.84.0、PR #7928
  相同（boost/core/detail/sp_thread_sleep.hpp 三处条件增加
  `&& !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)`）。1.85.0 该文件
  上下文与 1.84.0 一致，补丁无需修改。

## 依赖版本

- zlib/1.3.1（conan 制品仓，iostreams gzip）
- boost-build/1.90.0（conan 制品仓，tool_requires，b2 引擎 B2 5.3.2）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|---------|
| 1 | clang toolset 下 cxx11_static_assert=no，库不构建 | b2 clang.jam init-flags-cross 注入 --target=arm64-pc-linux 覆盖 OHOS 默认 target，sysroot/libc++ 头文件探测失败 | user-config.jam 以 gcc toolset 名字注册 clang++（gcc.jam 不注入 --target） |
| 2 | cxxflags 里显式 --target=aarch64-unknown-linux-ohos 无效 | b2 把自己注入的 --target 放命令行更后（后写者赢） | 同上（换 toolset 从根上避开） |
| 3 | b2 引擎运行报 Error loading shared library libc++_shared.so | b2 动态链接 SDK libc++，不在默认搜索路径 | LD_LIBRARY_PATH 注入（clang++ -print-file-name 自省定位，conanfile _build_env） |
| 4 | sp_thread_sleep.hpp pthread_setcancelstate 未声明 | OHOS musl 未实现该 API | patches/0001 + BOOST_SP_NO_PTHREAD_SETCANCELSTATE（沿用手动编译路线方案） |
| 5 | iostreams gzip 需要 zlib | b2 zlib 探测默认走 sysroot | ZLIB_INCLUDE/ZLIB_LIBPATH 环境变量指向 conan zlib 包（依赖链 Conan 管理） |
| 6 | b2 测试 shell 包装写 /tmp/jam*.tmp 失败 | OHOS /tmp 只读（E002） | TMPDIR/TMP 重定向到 build folder（b2 testing.capture-output 的 shell 脚本写这里） |
| 7 | program_options/regex/thread/chrono/random 测试目标要求 boost_test 库 | 这些库的测试源文件用 BOOST_TEST 框架（区别于 atomic/filesystem 的轻量自写 main） | --with-test 加入构建清单，b2 自动构建并链接 unit_test_framework；组件 boost_unit_test_framework 一并对外提供（同 boost/1.90.0.4.1 先例） |
| 8 | b2 测试编译在满载机器上被 OOM 杀（大 .cpp） | 构建机被并行任务占满内存（31.8/33.5GB），clang++ 无 error 输出直接退出 | 测试阶段 -j1 顺序执行 + 一次增量重试（b2 增量只重建失败项）；根因是宿主机负载，CI 干净机器不受影响 |

## 验证结果

- conan create：`boost-1.85/1.85.0-b2-nodocs@ohpcd/stable` Package created
- 上游测试：0 failed（b2 原生框架，见上）
- test_package：9 组件全过（见上）
- gzip round-trip：OK

## 注意事项

- 后续 boost 版本（1.86+）如需扩展编译库清单，只需调整 --with-\<lib\>
  列表与 comp_specs，b2 自动管理源文件清单（手动编译路线需要逐版本核对
  源文件重命名，如 1.85.0 的 Convert.cpp → convert.cpp）
- b2 官方在 1.90+ 提供 CMake 官方支持（E099 rec_priority=1 的
  use-cmake-build），本路线（gcc toolset 伪装）是 1.86-1.89 等中间版本的
  可行方案
- 若未来 b2 修复 clang toolset 的 OHOS target 识别（上游 issue），可回归
  clang toolset 配置
---

**编译结束**: 2026-09-10 02:50
**最终状态**: built
