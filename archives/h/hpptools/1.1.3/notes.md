# hpptools 1.1.3 适配笔记

## 编译环境
- 构建系统: header-only（无 configure/cmake/meson 顶层构建；examples/*.make 为样例/测试入口）
- 编译日期: 2026-09-21
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos）
- 状态: published

## 编译步骤

hpptools 为纯 header-only C++11 库（include/*.hpp），无 configure/make 主构建。
Conan 配方 package_type=header-library，build() 只应用补丁，package() 拷贝头文件。
样例与测试通过 examples/*.make 逐个编译（makefile 硬编码 SHELL=/bin/bash 与 g++，
OHOS 环境用 clang++ 直接编译，见下）。

```bash
# 样例（7 个，均为头文件自编译 -x c++）
clang++ -std=c++11 -O0 -g3 -Wall -Wextra -pedantic -D SAMPLE_ALG    -x c++ ../include/alg.hpp      -o sample-alg
clang++ -std=c++11 -O0 -g3 -Wall -Wextra -pedantic -DSAMPLE_LOGDIFF -x c++ ../include/logdiff.hpp  -o sample-logdiff
clang++ -std=c++11 -O0 -g3 -Wall -Wextra -pedantic -D SAMPLE_LOGGER -x c++ ../include/logger.hpp  -o sample-logger
clang++ -std=c++11 -O0 -g3 -Wall -Wextra -pedantic -DSAMPLE_p7LOGSUM -x c++ ../include/logsum.hpp -o sample-logsum
clang++ -std=c++11 -pthread -O0 -g3 -Wall -Wextra -pedantic -D SAMPLE_PFOR  -x c++ ../include/pfor.hpp  -o sample-pfor
clang++ -std=c++11 -pthread -O0 -g3 -Wall -Wextra -pedantic -D SAMPLE_TPOOL -x c++ ../include/tpool.hpp -o sample-tpool
clang++ -std=c++11 -O2 -Wall -Wextra -pedantic -DBENCHMARK_p7LOGSUM -x c++ ../include/logsum.hpp -o benchmark-logsum
# 测试（test-alg 需 boost 头；zstr 系需 zlib 头/库）
clang++ -std=c++11 -I../include -I<boost include> -o test-alg test-alg.cpp -lz -L<zlib lib>
clang++ -std=c++11 -I../include -I<boost include> -o test-strict_fstream test-strict_fstream.cpp -lz -L<zlib lib>
clang++ -std=c++11 -I../include -I<boost include> -o ztxtpipe ztxtpipe.cpp -lz -L<zlib lib>
clang++ -std=c++11 -I../include -I<boost include> -o zpipe zpipe.cpp -lz -L<zlib lib>
clang++ -std=c++11 -I../include -I<boost include> -o zc zc.cpp -lz -L<zlib lib>
# 鸿蒙专项测试
clang++ -std=c++11 -pthread -O2 -Wall -Wextra -pedantic -I<include> -o ohos_special_test ohos_test/ohos_special_test.cpp
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | examples/*.make 硬编码 `SHELL := /bin/bash` 与 `g++` | OHOS 无 /bin/bash、无 g++（仅有 clang） | 不依赖 .make，用 clang++ 直接按等价命令编译（记录于本笔记） |
| 2 | zc.cpp 使用 getopt/optarg/optind 未声明 | OHOS <iostream> 不隐式引入 getopt.h | 补丁 examples/zc.cpp 增加 `#include <getopt.h>`（patches/0001-zc-getopt-include.patch） |
| 3 | test-alg.cpp 需要 boost/preprocessor.hpp | 上游测试源码依赖 boost | 编译时指向 conan 缓存 boost 头路径（测试期依赖，配方无需 requires boost——公开头不引用 boost） |
| 4 | zstr 系目标需 zlib 头/库 | 公开头 zstr.hpp include <zlib.h> | 配方 requires zlib/1.3.1（registry 已发布）；本地编译指向 conan zlib 缓存 |
| 5 | /tmp 只读 | OHOS /tmp 为只读 | 临时产物放 $HOME/tmp（TMPDIR 已指向 ~/tmp） |

## 源码修改

- patches/0001-zc-getopt-include.patch：examples/zc.cpp 顶部增加 `#include <getopt.h>`（OHOS libc++ 不隐式声明 getopt）。

## 依赖版本

- zlib/1.3.1（conan 制品仓已发布；zstr.hpp 公开头依赖）
- boost（仅上游测试 test-alg.cpp 编译期引用 boost/preprocessor.hpp，非库依赖）

## 上游测试台账（完整枚举）

源码根：examples/（hpptools-1.1.3 官方 tag v1.1.3 内唯一测试/样例目录）

| 入口 | 类型 | 是否独立上游用例 | 分类理由 | 是否运行 | 结果 |
|------|------|------------------|----------|---------|------|
| examples/test-alg.cpp | 用户测试源（Catch） | ✅ 是（9 个 TEST_CASE） | 9 个独立 TEST_CASE：min_of / max_of / minmax_of / mean_stdv_of / equal_of / for_each_advance / for_each_it / for_each_it_advance / os_join | 已运行 | ✅ 通过（410 assertions in 9 test cases） |
| examples/test-strict_fstream.cpp | 用户测试源（main 直接断言） | ✅ 是（1 个独立用例） | 独立 main 测试，无 Catch TEST_CASE 宏，直接断言 fstream 模式/错误行为 | 已运行 | ✅ 通过 |
| examples/ztxtpipe.cpp | 用户测试源/工具 | ✅ 是（1 个独立用例） | zstr 无压缩与 gzip 输入管道往返一致性（make test 用例） | 已运行 | ✅ 通过 |
| examples/zpipe.cpp | 用户测试源/工具 | ✅ 是（1 个独立用例） | zstr 压缩/解压管道往返一致性（make test 用例） | 已运行 | ✅ 通过 |
| examples/zc.cpp | 用户测试源/工具 | ✅ 是（1 个独立用例） | zstr 命令行 -c/-o 往返一致性（make test 用例） | 已运行 | ✅ 通过（补 getopt.h 后） |
| examples/catch.hpp | 框架头/源码 | ❌ 否 | Catch2 测试框架头（单头文件），非用户用例 | 不运行 | 框架依赖 |
| examples/sample-alg.cpp（alg.hpp 内嵌 SAMPLE_ALG） | 样例 | ❌ 否 | 头文件内嵌样例程序，非测试用例 | 已运行 | ✅ 输出正常 |
| examples/sample-logdiff / sample-logsum / sample-logger / sample-pfor / sample-tpool（对应 .make） | 样例 | ❌ 否 | 样例程序（演示/冒烟），非断言测试 | 已运行 | ✅ 输出正常 |
| examples/benchmark-logsum.make | 基准 | ❌ 否 | 性能基准（计时），非正确性测试 | 已运行 | ✅ 两版本均运行 |
| examples/test-alg.make / test-strict_fstream.make / test-zstr.make / 各 sample-*.make | 测试脚本/构建目标 | ❌ 否 | make 包装脚本，非独立用例 | 等价命令已执行 | ✅ |
| examples/*.hpp（logger/logsum/strict_fstream 等内嵌样例段） | 头文件内嵌样例 | ❌ 否 | 头文件文档样例，非测试用例 | 不单独运行 | — |

**统计口径（双口径）**：
- source_declared_total（官方 tag 源码可复制枚举的独立上游用例数）= 9 + 1 + 1 + 1 + 1 = **13**
  （test-alg 9 个 Catch TEST_CASE + test-strict_fstream 1 + ztxtpipe 1 + zpipe 1 + zc 1）
- configured_executable_total（当前 OHOS 配置实际实例化/注册的独立可执行用例数）= **13**
  （全部编译为可执行并实际运行）
- executed_passed_total = **13**；failed = 0；uninstantiated/unrun = 0
- 通过率 = 13/13 = 100%（全量口径）；13/13 = 100%（当前配置可执行口径）
- 映射：TEST_CASE 宏（9）→ 无预处理互斥分支 → test-alg 可执行 → 实际运行 410 断言通过；
  其余 4 个 main/工具入口 → 无注册框架 → 可执行 → 实际运行通过

## 鸿蒙专项测试

- 文件：archives/h/hpptools/1.1.3/ohos_test/ohos_special_test.cpp
- 内容：独立编写的 OHOS 平台专项用例（非上游代码），覆盖 pfor 并行循环（4 线程平方 1000 项）、
  tpool 线程池（4 worker 完成 32 作业）、logger 设施级别过滤（debug 抑制/info 输出）
- 编译：clang++ -std=c++11 -pthread -O2 -I<include>（aarch64-unknown-linux-ohos）
- 运行：ALL PASSED（pfor/tpool/logger 三项断言全过）

## 消费者验证

- test_package/test_package.cpp：仅用公开头调用 alg::for_each_it_advance / min_of / os_join
  与 logsum::p7_FLogsum 并断言可观察结果；conan create 内 CTest 运行通过。

## 验证结果

```bash
# conan-verify 8 门禁（G0-G4 + L2/L4/L5）
python3 scripts/ohc-run.py conan-verify hpptools 1.1.3   # ✅ 全部 PASS
# 上游测试
./test-alg                 # ✅ All tests passed (410 assertions in 9 test cases)
./test-strict_fstream      # ✅ 通过
./ztxtpipe && ./zpipe && ./zc  # ✅ 往返一致性全过
# 鸿蒙专项
./ohos_special_test        # ✅ ALL PASSED
```
---

**编译结束**: 2026-09-21 00:37
**最终状态**: published
