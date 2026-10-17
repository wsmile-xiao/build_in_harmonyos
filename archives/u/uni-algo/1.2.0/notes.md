# uni-algo 1.2.0 适配笔记

## 编译环境
- 构建系统：cmake（根工程出库；`test/` 是上游自带的独立 CMake 工程）
- 编译器：clang 15.0.4（OHOS SDK 26.0.0.18 native llvm，target aarch64-linux-ohos）
- profile：`ohos-aarch64`（`compiler.cppstd=17`、`build_type=Release`）
- 任务：#11505（`taskBranch=feat/uni-algo-1.2.0`，无后缀）
- 路径：A（纯静态库，无 `bin/`，不需要 `commands.json`）

## 上游坐标

| 项 | 值 |
|---|---|
| tag | `v1.2.0` |
| codeload | `https://codeload.github.com/uni-algo/uni-algo/tar.gz/refs/tags/v1.2.0` |
| 大小 / SHA-256 | 437340 B / `f2a1539cd8635bc6088d05144a73ecfe7b4d74ee0361fabed6f87f9f19e74ca9` |
| 与 `github.com/archive` 对比 | 同大小同 SHA-256（本机 2026-09-20 双下对拍一致） |
| 许可证 | Public Domain (Unlicense) 或 MIT，二选一 |

## 上游官方测试怎么跑

上游 `.github/workflows/linux.yml` 的原样跑法（矩阵含 `clang++-15`，与本环境同版本 clang）：

```sh
cmake -S test -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
cd build && ctest --verbose --output-on-failure
```

`test/` 自带 `project(uni-algo-test)`，`add_test()` 只注册 **1 个** ctest 用例
`uni-algo-test`；真正的用例体在 `test/main.h` + 27 个 `test_*.h` 里，由自定义断言宏
`TESTX(x)` 展开成 `if (!(x)) { ...; exit(111); }`。因此：

| 口径 | 数量 | 取数命令 |
|---|---|---|
| 源码 `TESTX` 断言点 | 3447 | `grep -rhoE '\bTESTX\b' test --include=*.h --include=*.cpp \| wc -l` |
| 本配置实际编译进二进制的断言点 | 3328 | `g++ -std=c++17 -E -DTEST_MODE_WITHOUT_UNICODE_TEST_FILES test/main.cpp \| grep -c '"TEST FAILED: "'` |
| 同口径但 C++20（上游 CI） | 3368 | 同上改 `-std=c++20` |
| ctest 注册用例 | 1 | `grep -c '^add_test' test/CMakeLists.txt` |
| 二进制内 `DONE:` 分区 | 15 | `grep -c 'std::cout << "DONE' test/main.h` |
| 需要外部数据的 `SKIP:` 分区 | 2 | 见下 |

断言点里有一块被 `#ifndef TEST_MODE_WITHOUT_UNICODE_TEST_FILES` 门控，所以
源码口径（3447）> 编译入口径（3328）；PR 正文按 **3447** 声明（≥ 任何一种实测口径，
不存在少报），并在说明里把三个数都写清。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试工程只注册 1 个 ctest 用例，直接按 ctest 口径声明 N 会把 3000+ 条真实断言说成 1 条 | 上游用「单二进制 + 自研 `TESTX` 宏」，不是 gtest/cppunit 那种逐用例注册 | 声明口径取源码 `TESTX` 数（3447），同时给出**预处理后实际编译数**（3328）的取数式；两者都写进 PR 表格说明，避免「少报」与「虚报」两个方向都被挑 |
| 2 | `DOWNLOAD_UNICODE_TEST_FILES=ON` 会让 create 直接红 | 它不是运行期开关，而是在 configure 阶段 `file(DOWNLOAD)` 拉 unicode.org 的 `NormalizationTest.txt`/`GraphemeBreakTest.txt`/`WordBreakTest.txt`，上游 `func_download()` 对任何非 0 状态码 `FATAL_ERROR` | 保持上游默认 OFF（上游 CI 同默认），2 个依赖外部数据的分区如实记 SKIP 并在 `test_package/MANIFEST.yml` 写明原因 |
| 3 | 在 `build()` 里单独 configure 第二个 CMake 工程时，编出来的不是 OHOS 二进制 | `test/` 是独立 `project()`，不继承根工程的 toolchain；不显式传 `-DCMAKE_TOOLCHAIN_FILE` 就退回宿主机默认编译器 | 先按 `CMakeToolchain` 生成位置找到 `conan_toolchain.cmake`（`os.walk` 兜底，找不到直接 raise），再连同 `-DCMAKE_BUILD_TYPE=<build_type>` 传给第二个工程 |
| 4 | 上游测试工程对 GNU/Clang 无条件加 `-Werror`，且仅在 `NOT DEFINED CMAKE_CXX_STANDARD` 时才提 `cxx_std_20` | conan profile 写了 `compiler.cppstd=17` → CMAKE_CXX_STANDARD 已定义 → 走 C++17 | 实测 C++17 / C++20 两种口径下 15 个 `DONE` 分区与 `ALL TESTS PASSED!` 完全一致（本机 mingw g++ 13.2 预验），因此不改上游、不加 `-Wno-error`，保持 `-Werror` 严格性 |
| 5 | 消费者测试若只用 inline 部分，L1e（移走 `lib/`）会测不出依赖 | uni-algo 头文件大量 inline，但所有 Unicode 数据表都在 `src/data.cpp` → `libuni-algo.a` 里；非 header-only 模式下任何转换都要引外部符号 | 探针断言全部走**需要数据表**的路径（转换、大小写、归一化、属性、Script、断句），并额外用 `una::casesens::collate_utf8("а","А") < 0` 与二进制序相反的断言证明真的查了表 |
| 6 | `\x` 转义写窄字符串时把后续字母吞进十六进制（本机编译报错 `hex escape sequence out of range`） | `"stra\xC3\x9Fe"` 里 `e` 是十六进制字符，转义变成 `\x9Fe` | 断开字面量 `"stra\xC3\x9F" "e"`；探针里所有非 ASCII 只用 `\x`/`\U` 转义或整型码点，源码文件本身保持纯 ASCII |
| 7 | 真机上 `test_ohos.cpp` 报 `no member named 'nl_langinfo' in namespace 'std'` | musl 的 `<langinfo.h>` 只声明**全局** `nl_langinfo`，libc++ 的 C++ 包装头不会把它搬进 `std::`（`std::setlocale` 有、`std::nl_langinfo` 没有）；本机 mingw 因为没有 `langinfo.h` 而把这段编译剔除，所以本地预验看不到 | 改成全局调用 `nl_langinfo(CODESET)`。仓库 `knowledge/musl-glibc-full-comparison-iso-posix.md` 只记了「OHOS 有 `nl_langinfo`/`CODESET`」的**可用性**，没记 C++ 命名空间这一层 |
| 8 | `CHECK` 宏被 `library_v{1, 2, 0}` 的逗号撑破（本机 `macro "CHECK" passed 3 arguments`） | 初始化列表里的逗号是宏参数分隔符 | 宏改变参 `CHECK(...)` + `#__VA_ARGS__` |

## 源码修改

无。`conandata.yml` 的 `patches: {}`，OHOS clang 15 + musl 下上游源码零改动即可编译并跑过全部官方测试。

## 依赖版本

零外部依赖（只用 C++17 标准库；上游内置的 `sqlite/`、`gen/`、`perf/` 均不参与本配方构建）。

## 验证结果

### 本机预验（mingw g++ 13.2，用于把上游接法和期望值先跑对，不是交付证据）

- 上游套件：`-std=c++20` 与 `-std=c++17` 各编一次，均 `ALL TESTS PASSED!`、退出码 0、15 个 `DONE`、2 个 `SKIP`
- `consumer_probe`：**61/61** 断言通过（链接本机复现的 `libuni-algo.a`）
- `ohos_probe`：21/24，且 3 条失败恰好是 `__OHOS__`、`__aarch64__`、`sizeof(wchar_t)==4`
  —— 主机本就该失败，用以证明这些断言不是恒真；`langinfo` 那 2 条在 Windows 上编译剔除
- 预验价值：抓出 `\x9Fe` 转义越界、`CHECK` 宏被 `{1,2,0}` 逗号撑破、
  `word` 迭代器实际切 5 段（不是想当然的 2 段）与希腊语大小写样例误抄一个码点

### 真机（OHOS aarch64，2026-09-20 23:55–23:58 CST）

- `conan create archives/u/uni-algo/1.2.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`
  → **`CREATE_EXIT:0`**，`CONAN_HOME=~/work/psj/ch-ual11505`（私有缓存，未写共享 `~/.conan2`），
  日志 `~/work/psj/ual11505-ch1.log`
- 上游官方测试（配方 `build()` 内 `cmake -S test` + `ctest --verbose --output-on-failure`）：
  `1/1 Test #1: uni-algo-test ... Passed 5.70 sec` / `100% tests passed out of 1` /
  `ALL TESTS PASSED!`，**15 个 `DONE` 分区**、2 个 `SKIP` 分区（见「上游官方测试怎么跑」）
- test_package：`CONSUMER: 61/61 passed`、`OHOS-SPECIAL: 28/28 passed`，两个探针均退出码 0
- 真机实测的平台事实（由 `ohos_probe` 断言固化）：`__OHOS__`、`__aarch64__` 成立；
  LP64（`sizeof(void*)==8`）、`sizeof(wchar_t)==4`；musl `nl_langinfo(CODESET)` = **`UTF-8`**；
  `una::locale::system()` 在真机上解析为 **`en-US`**；
  含 CJK 与组合尖音符（NFD 形式）的文件名可创建、可被 `readdir` 逐字节原样枚举、内容可读回
- 产物：`lib/libuni-algo.a`（674738 B，SHA-256 `9fa7bb61baf42db3d520d47e8b669482b9e617bb6bf87a89e6591cfd0dcd347a`）
  + `include/uni_algo/**.h`（53 个）+ `licenses/LICENSE.md` + `share/uni-algo/cmake/*`（上游自带的 config）
- 归档内目标文件核对：成员 `data.cpp.o` 是 ELF64，`e_machine = b7 00`（EM_AARCH64），
  `llvm-nm --defined-only` 可见 `_ZN3una6detail11stage1_foldE` 等 Unicode 数据表符号
  → 头文件 inline 实现所需的数据确实来自本包，`lib/` 被移走时消费者必然链不上（L1e 依据）
- 包 ID `f23d5a9b1d537641c03c7814478a2fadb727650a`，包 revision `c889517af7f4adcd0a4216066731a5ba`
- **L1e/R34 破坏性反向验证已在真机自测**（`tools/probes/ual11505_neg.sh`，同一私有缓存内移走产物目录后
  `conan test ... -pr:h -pr:b=ohos-aarch64`）：
  | 轮次 | 动作 | 退出码 | 首条失败 |
  |---|---|---|---|
  | POS | 原样 | `POS_EXIT:0` | — （`CONSUMER: 61/61`、`OHOS-SPECIAL: 28/28`） |
  | NEG-1 | 移走 `include/` | `NEG_INC_EXIT:1` | `Imported target "uni-algo::uni-algo" includes non-existent path ".../p/include"` |
  | NEG-2 | 移走 `lib/` | `NEG_LIB_EXIT:1` | `CMake Error at cmakedeps_macros.cmake:81: Library 'uni-algo' not found in package.` |
  | RESTORED | 还原 | `RESTORED_EXIT:0` | — （再次 61/61 + 28/28） |
  日志 `~/work/psj/ual11505-neg.log`；`.a` 的 SHA-256 在四轮前后保持 `9fa7bb61…347a` 未变
- 第一轮 create 的 `CREATE_EXIT:1` 不是配方问题：`test_ohos.cpp` 里写了 `std::nl_langinfo`
  （musl 只声明全局符号，见坑 7），修成 `nl_langinfo()` 后一次通过；
  库与上游测试在两轮里都一模一样地通过（同一 `ALL TESTS PASSED!`）

## 注意事项

- `package_type = static-library`：只出 `lib/libuni-algo.a`，无 `bin/`（R38/L0k 不适用）
- 消费者必须链接本包：非 header-only 模式下不定义 `UNI_ALGO_STATIC_DATA`，数据表来自 `.a`
- 上游只 install 库与头，不 install 许可证 → `package()` 手工 `copy` `LICENSE.md` 到 `licenses/`
- Windows 本机大小写不敏感导致的 `libXext` 噪音与本任务无关，未触碰
