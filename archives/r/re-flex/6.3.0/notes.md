# re-flex 6.3.0 适配笔记

## 编译环境
- 构建系统: autotools（tag 归档自带预生成 bootstrap：configure / Makefile.in / config.h.in，
  无需 autoreconf，设备与 CI worker 均不需要 automake）
- 编译日期: 2026-09-22
- 编译器: clang/clang++ 15.0.4（OHOS），C++17（profile cppstd=17；上游头文件使用
  std::string_view，clang 15 起默认 gnu++17，配方中已显式 -std=gnu++17 固化）
- 状态: built

## 上游测试清点申报表（R51 / R51 详细说明）

- **清点对象**：上游 tag 归档 v6.3.0（sha256 c9e448b6…）`tests/` 目录。
- **候选数法**：
  1. `tests/*.cpp` 测试源文件全量：**13**；
  2. `tests/Make` 接线为可运行程序的：`all` 目标 9 个 + 独立 `lazytest` 目标 = **10**；
  3. 其中 3 个（test_lorem_filter/splitter/tokenizer.cpp）无 `main()`，是 `lorem.cpp`
     的 `#include` 组件，上游不作为独立程序运行。
- **N = 13**（候选数法最大值），差额逐项归因：10 个接线程序（9 个 `all` + lazytest）
  + 3 个 lorem `#include` 组件。
- **N′ = 6**：test_bits、test_ranges、streams、lazytest、stest、rtest
  （设备实跑，全部 exit 0、零 ERROR/FAIL，逐程序证据见 `reports/`）。
- **未运行 7 项及具体技术原因**：
  - `test`、`lorem`、`ptest`、`btest`（4 个程序）：编译期无条件
    `#include <boost/regex.hpp>`（boostmatcher.h）/ `<pcre2.h>`（pcre2matcher.h），
    属 re-flex 的**可选第三方正则后端对比测试**；re-flex 本体（reflex 工具与
    libreflex.a）不链接这两个库，Boost/PCRE2 未作为依赖启用（W0：可选依赖缺省
    禁用不算止损）。首错形态为 `<boost/regex.hpp>: No such file`（头文件缺失，
    非平台缺陷）。
  - 3 个 lorem `#include` 组件：无 `main()`，只能随 lorem.cpp 编译，同因不运行。
- **替代验证**：rtest（155 条用例表，re-flex 自有 DFA 引擎全语料）+ stest（117 条
  用例表，C++ std::regex 后端）已实跑通过，覆盖核心引擎与标准库后端两条路径；
  另以 test_package 做消费者契约验证（链接打包后的 libreflex.a）与端到端验证
  （打包后的 reflex 生成→编译→运行 scanner）。用例级数字（155/117/62/…）为
  **次级口径**，仅作内部断言量参考，不与程序级 N/N′ 混用申报。
- examples/（34 个 `.l`/`.y` 示例）是演示程序而非测试：无断言，上游也不将其接
  入任何 check/test 目标（`--enable-examples` 默认关闭，`calc.y` 需 bison），
  不计入 N，也不运行。

## 编译步骤

配方 `conanfile.py build()`（E011：在 /data/storage/el2/base 非 HMDFS 工作目录构建）：

```bash
bash configure --prefix=/usr/local --build=aarch64-linux-ohos --host=aarch64-linux-ohos \
    CC=clang CXX=clang++ \
    CXXFLAGS='-O2 -Wall -Wextra -Wunused -std=gnu++17' \
    LDFLAGS='-Wl,-z,relro,-z,now'
make -j2
# 上游自包含测试：编译 5 个附加程序（rtest 由默认 target 构建）后统一实跑
make install DESTDIR=<stage>
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `configure: error: cannot guess build type; you must specify one` | 上游 config.guess 无法识别 HongMeng 内核（UNAME_SYSTEM="HarmonyOS"） | 显式传 `--build=aarch64-linux-ohos --host=aarch64-linux-ohos`（设备原生构建 build==host） |
| 2 | `./config.status: ./confXXXX/subs1.awk: Permission denied`（E011） | HMDFS 无法承载 autotools config.status 的受限权限临时目录语义 | 整个构建在 /data/storage/el2/base 下非 HMDFS 工作目录进行 |
| 3 | `aclocal-1.18: command not found`（maintainer-mode 重生成被触发） | 用 `cp -r` 物化源码丢 mtime，aclocal.m4 比 configure.ac 旧 → automake 版本化重生成规则生效；设备与 CI worker 均无 aclocal | 物化必须保 mtime：tar 解包或 `shutil.copytree`（copy2），重生成规则因 mtime 不早于 prerequisites 而休眠，无需 automake |
| 4 | 测试可执行文件无法运行（E077） | OHOS 拒绝执行无 .codesign 段的 ELF | 每个要执行的 ELF（6 个测试程序、打包的 bin/reflex、test_package 消费者）先 binary-sign-tool 自签名 |

## 源码修改

无补丁（conandata.yml `patches: {}`）：上游源码零修改即可在 OHOS 上构建。
SIMD 分派为条件编译：aarch64 下 configure 判定 `-DHAVE_NEON`，AVX2/AVX512BW
专属 .cpp 因 `#if defined(HAVE_AVX2…)` 守卫编为空翻译单元，无强制 ISA 路径。

## 依赖版本

无运行期/构建期外部依赖（编译器 clang 15.0.4、GNU Make 4.4.1、bash 5.x 用于
驱动 configure；可选 Boost.Regex / PCRE2 未启用）。

## 验证结果

```bash
# 原生探索构建（同一 SHA 源码）
$ ./configure --prefix=/usr/local --build=aarch64-linux-ohos --host=aarch64-linux-ohos …
configure-rc:0   # checking whether clang++ supports NEON/AArch64 intrinsics... yes
$ make -j2
make-rc:0        # lib/libreflex.a 900988B, lib/libreflexmin.a 415508B, src/reflex 862720B
$ ./src/reflex --version
reflex 6.3.0 aarch64-unknown-linux-ohos
# 端到端：reflex 生成 scanner → clang++ 编译 → 运行
$ printf '42 hello world 7x\n' | ./smoke_bin
NUM:42
WORD:hello
WORD:world
NUM:7
WORD:x
```

上游自包含测试（6/6 exit 0、零 ERROR/FAIL；逐程序 stdout 留档 reports/）：
test_bits（断言组）、test_ranges（断言组）、streams（UTF-16→UTF-8 转换输出）、
lazytest（62 OK）、stest（35 OK 行/117 用例表）、rtest（163 OK 行/155 用例表）。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/reflex | 862720 B（未 strip） | 词法分析器生成器（已 OHOS 自签名） |
| lib/libreflex.a | 900988 B | 完整正则匹配库（静态） |
| lib/libreflexmin.a | 415508 B | 精简变体（静态，消费者显式链接） |
| include/reflex/*.h | 20 个头 | 公共头文件 |
| lib/pkgconfig/reflex.pc, reflexmin.pc | — | pkg-config 描述文件 |
| share/man/man1/reflex.1 | — | 手册页 |
| licenses/LICENSE.txt | — | BSD-3-Clause |

## 注意事项

- `make check` 只构建 tests/rtest（无 automake `TESTS`），可运行的上游测试在
  `tests/Make`；本配方在 `build()` 里显式编译+运行 6 个自包含程序（证据打印
  `UPSTREAM_TEST <name> exit=… OK=… ERRORFAIL=…` 行）。
- 未启用 `--enable-examples`（默认关）：examples 需 bison 且是演示程序。
- 上游 `AC_PROG_YACC` 为残留探测，默认构建无 .y 源，不触发 bison/byacc 依赖。
- 双库语义：`cpp_info.libs = ["reflex"]`；libreflexmin 是 reflex 的子集，
  同时链接两者会符号重复，需要精简运行时的消费者显式换链 reflexmin。
