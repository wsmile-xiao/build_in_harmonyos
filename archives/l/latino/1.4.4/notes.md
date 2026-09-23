# latino 1.4.4 Conan 配方适配笔记

- **日期**: 2026-09-15
- **上游**: https://github.com/lenguaje-latino/latino (v1.4.4 tag) + latino-core 子模块（pin commit 3a6ecd4）
- **构建系统**: CMake (>= 3.5)
- **许可证**: MIT（latino / latino-core 均 MIT）

## 上游结构

- 双仓结构：主仓（CLI、ejemplos、man、gnu-utilities）+ `latino-core` 子模块（解释器本体：bison/flex 解析器、VM、stdlib）。
- GitHub tag tarball **不含子模块内容**，配方 `source()` 用 conandata 的第二个源把 latino-core 解压还原到 `latino-core/`（等价于 `git submodule update --init`）。
- 产物：`bin/latino`（CLI）、`lib/liblatino.so`（shared target `liblatino`）、`lib/libliblatino_static.a`（static target 名为 `liblatino_static`，CMake 再加 lib 前缀）。上游总是同时构建两者，`shared` 选项只选择打包哪个。

## OHOS 适配要点（按发现顺序）

1. **E092 — CMake 无 HarmonyOS 平台模块**：上游所有 install 规则都在 `if(UNIX)` 里，HarmonyOS 下 `UNIX=NO`（CMake 4.1.2 实测）→ 全部 install 规则失效。映射 `CMAKE_SYSTEM_NAME=Linux`（ableton-link/3.1.2 先例）。OHOS clang 定义 `__linux__`，上游 latcompat.h 的 Linux 分支（readline 头、`_GNU_SOURCE`）全部生效，语义等价。

2. **musl 空壳 libintl.h + bison `YY_`→`dgettext`（新根因，草稿 DRAFT-latino-1.4.4-musl-empty-libintl-bison-dgettext）**：预生成的 `latparse.c` 序言在 `#ifdef __linux` 下 `#define YY_(Msgid) dgettext("bison-runtime", Msgid)`。OHOS musl 的 `libintl.h` 是空壳（零函数声明），libc 也无 dgettext 符号 → `call to undeclared function 'dgettext'` + int→指针转换编译错误。补丁把守卫改为 `#if defined(__linux) && defined(__GLIBC__)`，bison 默认恒等回退生效，消息按原文输出，无功能损失。
   - 与 E015（链接期缺 `-lintl`）、E027（configure NLS 探测）、E531（musl 缺 glibc 符号）均不同——这是**编译期、头文件存在但空壳**。

3. **裸 `link_libraries(readline)`**：上游不 find_package，直接 `-lreadline`。注入方式：`generate()` 里用 `Environment()` 设 `CPATH`（readline 头）与 `LIBRARY_PATH`（readline 库路径）——它们对编译/链接命令均生效且不改上游 CMakeLists。
   - readline 静态库的 terminfo 符号（tputs/UP/tgetflag）在 ncursesw：用 `CMAKE_C_STANDARD_LIBRARIES=-lncursesw`（CMake 追加到每条链接行**末尾**，在 -lreadline 之后，保持静态归档符号顺序）。

4. **公共头传染 readline**：`latcompat.h` 在 `__linux__` 分支 include readline/readline.h、readline/history.h → 消费者编译 latino 头必须能看到 readline 头。`self.requires("readline/8.3", transitive_headers=True)` + `package_info` 显式组件（`components["latino"].requires = ["readline::readline"]`），CMakeDeps 才会给消费者生成 readline-config 并通过 `latino::latino` 传播 include 路径。**坑**：shared 包默认把传递依赖折算为 headers=False——没有 transitive_headers=True 时 test_package 报 `readline/history.h not found`。

5. **上游静态库含 main()（全平台缺陷，非 OHOS 特有）**：`SRC_LIB` 包含 `latino.c`（`int main`），stock 静态库链入任何自带 main 的消费者必报 duplicate symbol。latino.o 还定义两个被 latast.c/latlex.c/latparse.c 引用的公共全局（`char *filename`、`int parse_silent`，`latino.h` extern 声明）。最小修复在 `package()`：`llvm-ar d` 剥离 latino.o，编译 stub（只含这两个全局）`llvm-ar r` 回填。已验证消费者静态链接+运行通过。

6. **上游 VM 双 bug（真机复现，与适配无关）**：
   - 同一表达式内二元递归 `f(n-1)+f(n-2)` 挂死（上游自带 `ejemplos/11-fibonacci.lat` 真机挂死）；
   - 曾观察到特定 `desde` 循环/函数调用组合会触发上游 VM 挂死；该现象并非所有 `desde` 循环内函数调用都会发生，本次 `embed_script.lat` 覆盖的相关路径已通过。
   - test_script.lat 与 embed_script.lat 刻意避开这两种模式（test_script.lat 的 fibonacci 为迭代实现，embed_script.lat 不含 fibonacci 与任何递归），覆盖顺序调用+迭代形式。

## 测试

- **上游官方**：ctest 仅 1 个 target `coverage`（`latino ejemplos/coverage.lat`，223 行语言覆盖脚本）。构建后以绝对路径运行，exit=0。build() 里运行并在日志输出 `HMBS_UPSTREAM_TEST_RESULT`。ejemplos/ 共 64 个示例脚本，其中 11-fibonacci.lat 因上游 VM bug 挂死（记录于 manifest known_upstream_bugs），不做全量 ejemplos 扫描。
- **消费者测试**（test_package，3 项）：
  1. `latino_embed_test embed_script.lat`：公共嵌入 API 全链（latC_crear_mv → latA_analizar_arch → latC_analizar → latC_llamar_funcion → latA_destruir → latC_destruir_mv）跑 embed_script.lat（全部循环有界、无递归），subprocess 超时 120s 防上游 VM 挂死，逐行断言程序真实计算的 6 行输出（latino 4 / si_ok / 55 / 4 / valor / EMBED_TEST_OK），断言退出码 0，且 EMBED_TEST_OK 仅在全部检查通过后作为最后一行打印；
  2. `bin/latino test_script.lat`：10 行精确输出断言（fibo_iter(10)=55、sumatoria(100)=5050、elegir、字符串拼接、列表求和、字典成员、lista.invertir、imprimirf）；
  3. `bin/latino --version` = "Latino 1.4.4"。
- **双包验证**：`-o shared=True`（liblatino.so）与 `-o shared=False`（liblatino.a，main 剥离版）均 conan create 通过，test_package 全过。
- **本机即 OHOS aarch64 PC**：ohos-aarch64 产物直接真机运行验证。

## 风险与遗留

- SONAME：上游 SHARED 未设版本 → `liblatino.so` 无版本后缀（可接受，上游原样）。
- `--rdynamic`（上游 CFLAGS）在模块加载（`importar`）时需要：dlopen 扩展模块可引用主程序符号。musl/lld 下按需生效，未验证 importar 动态扩展场景。
- 上游 VM 双 bug（见上）属于上游质量问题，已写入 manifest，未做修复（超出适配范围）。
