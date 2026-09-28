# mtfmt 0.1.3 适配笔记

## 编译环境
- 构建系统: cmake（库）+ makefile（上游测试入口 `make test`）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4 / clang++ 15.0.4（`/data/service/hnp/bin`）
- 状态: built

## 版本与来源核对

- 上游仓库：https://github.com/MtFmT-Lib/mtfmt （tag `v0.1.3`，轻量标签指向 `0ae6a0589fd5d71d7bac389128c7245c7629c715`）
- 下载物：`https://github.com/MtFmT-Lib/mtfmt/archive/refs/tags/v0.1.3.tar.gz`，113215 字节
- `sha256sum` = `767a9b85b79d915ce7f1e43f0d24dc14942c07af24d6e96f7ff60ee522f1c1ce`，与 conan-center-index `recipes/mtfmt/all/conandata.yml` 的 `0.1.3` 条目**逐字一致**
- `git ls-remote --tags` 全量 5 条 tag 引用（`0.1.0`、`v0.1.1`、`v0.1.1^{}`、`v0.1.2`、`v0.1.3`）全部命中，`v0.1.3` 在列

## 编译步骤

1. **库**：conan `CMakeToolchain` 驱动上游 CMakeLists（`project(mtfmt)`，`aux_source_directory(src)`，
   静态库目标 `mtfmt`，`MTFMT_BUILD_SHARED=OFF`、`CMAKE_POSITION_INDEPENDENT_CODE=ON`、
   `CMAKE_BUILD_TYPE=Release`），产物 `target/lib/libmtfmt.a`。
2. **安装**：`cmake --install` 按上游 `install(TARGETS ...)`/`install(DIRECTORY inc/)` 落盘。
   上游把安装根写死成嵌套的 `mtfmt/` 前缀、静态库进 `mtfmt/lib/static/`，配方在 `package()`
   里把两层拍平成 conan 惯例的 `include/` + `lib/`（见下表「问题 1」）。
3. **上游测试**：`make -j<N> -C <source> test CC=<clang>`——上游 CMakeLists 的
   `enable_testing()`/`add_test()` 整段被注释，Makefile 是唯一注册的测试入口。
   `make test` 先编 `tests/*.c` + `tests/*.cpp` + `thirds/unity/src/*.c` 成
   `target/mtfmt_run.out`，随后原样执行，输出 `109 Tests 0 Failures 0 Ignored`。
4. **test_package**：`find_package(mtfmt CONFIG REQUIRED)` + `mtfmt::mtfmt` 链接消费者程序
   `mtfmt_consumer_test`，`test()` 用 `self.run(..., env="conanrun")` 真跑（69 项断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `install(TARGETS ...)` 把产物装进嵌套 `mtfmt/` 前缀（`mtfmt/include`、`mtfmt/lib/static/libmtfmt.a`、`mtfmt/lib/cmake/mtfmt/`），conan 消费者与产物检查都期待包根下直接是 `include/`、`lib/` | 上游按自身嵌套前缀布局写死 `DESTINATION`，不是可配置的 `GNUInstallDirs` | 配方 `package()` 在安装后把嵌套的 `mtfmt/` 一层与 `lib/static/` 一层分别拍平（`os.rename` + `rmdir`），**不改上游源码、无补丁**；同时删掉随行的 `lib/cmake/`（`install(EXPORT)` 写出的 `mtfmt-config.cmake` 内含拍平前的 `${_IMPORT_PREFIX}/lib/static/...` 绝对导入路径，拍平后必然失效；conan 消费者用 CMakeDeps 生成的配置） |
| 2 | Release tarball 不含 git 子模块 `thirds/unity`，而 `tests/*.c`/`tests/*.cpp` 全部 `#include "unity.h"`，缺它测试目标编不过 | 上游用 submodule 固定 Unity，GitHub archive 不展开 submodule | `conandata.yml` 的 `test_sources.unity` 记录 `v0.1.3` 树内指针 `1b9199ee380e203603b6649df9510db9cab147d9` 的归档 URL + sha256，`source()` 解到 `thirds/unity/`；**仅测试用**，不进打包产物、不进 `requires()` |
| 3 | 上游 Makefile 的 `CC = $(PREFIX)gcc`，设备与 CI worker 都没有 `gcc`（`command -v gcc` 为空），`make test` 必然 `gcc: not found` | Makefile 只认 `GCC_PATH`/`MTFMT_BUILD_GCC_PREFIX` 两个前缀变量，没有读 conan 工具链 | 配方从 `tools.build:compiler_executables`（profile 已给 `c`/`cpp`）取编译器，在 `make` 命令行显式 `CC=<clang>` 覆盖；不改上游 Makefile |
| 4 | Makefile 没有 `clean` 目标；同一 source 目录重复构建时旧目标文件的时间戳会让 `make test` 打出 `Nothing to be done` 而**一个用例都不跑**（假绿）。上游默认 `BUILD_DIR = build` 又恰与 conan `cmake_layout` 的构建根同名（首轮实测直接删它 → `package()` 报 `FileNotFoundError: …/b/build/Release`）；而把 `OUTPUT_DIR` 也改成绝对路径时，`test` 规则的 `"$(addprefix ./$(OUTPUT_DIR)/,…)"` 拼出 `.//abs/path` → `/bin/sh: … inaccessible or not found`、`make: *** [Makefile:265: test] Error 127` | 上游未提供清理目标；对象目录名与 conan 布局撞名；`test` 规则硬拼 `./` 前缀 | 配方用命令行变量把**对象**目录改到相对路径 `build-test`（保留 `OUTPUT_DIR` 默认相对值 `target`，避开 `./` 拼接），每轮先 `rmdir` `<source>/build-test` 与 `<source>/target` 两个**自己**的目录再重编；不碰 conan 的 `build/` 树，保证每次 `conan create` 都从零重编重跑，测试失败即非零退出 |
| 5 | `ldd` 在本设备不存在，无法用它确认共享库依赖 | OHOS 不带 ldd | 用 `readelf -d <bin> \| grep NEEDED` + 同环境真跑一次替代；本包为静态库，`package_info().libs=["mtfmt"]`，无系统库依赖（`src/` 未引用任何 libm/第三方符号，见下方依赖核对） |

## 源码修改

无。上游源码零补丁（`patches/` 不创建，`patches_applied: []`）——所有差异都在配方层
（安装布局拍平、测试入口的编译器与清理），不产生源码 delta。

## 依赖版本

- 包依赖（`requires()`）：**0 个**。`src/`、`inc/` 的全部 `#include` 都是 C/C++ 标准头
  （`assert/stdarg/stddef/stdint/stdio/stdlib/string` + C++ 包装的 `array/exception/functional/
  iterator/limits/string/tuple/type_traits/utility`）；`grep` 未命中任何 `pow/log/sqrt/floor` 等
  libm 符号，也未命中 `iconv/pthread/dlopen` 等系统库符号，故不声明 `system_libs`。
- 构建依赖：CMake 4.1.2、GNU Make 4.4.1、clang/clang++ 15.0.4。
- 测试依赖（仅测试）：Unity，子模块 `1b9199ee380e203603b6649df9510db9cab147d9`。

## W0 生死关核对

| 项 | 结论 | 读数 |
|---|---|---|
| 版本可得性 | 通过 | `git ls-remote --tags` 命中 `v0.1.3`；tag 归档 URL 可下载且 sha256 与 CCI 一致 |
| 硬依赖 | 通过 | 0 依赖，无 `conan list -r=ohpcd` 需要实查的对象 |
| 平台可移植性（ISA / glibc printf 钩子） | 通过 | `grep -rniE 'altivec\|<mmx\|3dnow\|emmintrin\|immintrin\|xmmintrin\|arm_neon\|sse2?\.h\|nmmintrin'` 在 `src/ inc/` **0 命中**；`grep -rniE 'register_printf\|printf\.h\|__printfchk'` **0 命中**；`<emscripten.h>` 仅在 `inc/mm_cfg.h:428` 的 `#elif MSTR_BUILD_CC == MSTR_BUILD_CC_EMSCRIPTEN` 分支内，不在构建面 |

## 验证结果

### 上游原生（适配前）——沙箱 HOME `HOME=$TASK_DIR/test-home`

```bash
tar xzf v0.1.3.tar.gz -C $TASK_DIR/native            # 另将 Unity 解到 thirds/unity
HOME=$TASK_DIR/test-home make -j4 -C $TASK_DIR/native/mtfmt-0.1.3 test CC=clang AR=ar
# 日志: $TASK_DIR/logs/native-make-test.log
```

| 指标 | 读数 |
|---|---|
| `109 Tests 0 Failures 0 Ignored` | 命中（Unity 汇总行） |
| `grep -cE ':PASS$'` | 109 |
| `grep -cE ':FAIL'` | 0 |
| 退出码 | 0 |

（适配后的 conan 轮读数在采信轮结束后回填到本节末尾。）

## 交付物

| 文件 | 说明 |
|------|------|
| `lib/libmtfmt.a` | 静态库（`MTFMT_BUILD_SHARED=OFF`） |
| `include/*.h` `include/*.hpp` | 公共头 14 个（`mtfmt.h`/`mtfmt.hpp` 聚合头 + 12 个 `mm_*.h`/`mm_*.hpp`，与安装树 `ls include \| wc -l` = 14 一致） |
| `licenses/LICENSE` | LGPL-3.0 全文 |

## 注意事项

- 本包为纯库，产物无 `bin/`，按 R38 **不创建** `commands.json`。
- `package_type="library"`，`options={"shared","fPIC"}`，默认 `shared=False`、`fPIC=True`。
- 上游默认关闭 `MTFMT_RT_USE_FP32/FP64`（浮点格式化）、`MTFMT_RT_USE_STDOUT`、
  `MTFMT_RT_USE_MALLOC`、`MTFMT_RT_USE_DIV`——配方保持上游默认，未改行为。
