# hpptools-1.1.3-makefile-shell-gxx-and-getopt（草稿）

## 症状

OHOS aarch64 上编译上游手写 .make 测试文件与 POSIX CLI 源码时两组失败：

```
# 失败一：make 无法执行（SHELL := /bin/bash + g++ 均不存在）
g++ -std=c++11 -O0 -g3 -ggdb -fno-eliminate-unused-debug-types -Wall -Wextra -pedantic -D SAMPLE_ALG -x c++ ../include/alg.hpp -o sample-alg
make: /bin/bash: No such file or directory
make: *** [sample-alg.make:8: sample-alg] Error 127

# 失败二：getopt 未声明（OHOS libc++ <iostream> 不隐式暴露 POSIX 声明）
zc.cpp:95:17: error: use of undeclared identifier 'getopt'
zc.cpp:103:37: error: use of undeclared identifier 'optarg'
zc.cpp:121:45: error: use of undeclared identifier 'optind'
```

## 根因

1. 上游手写 Makefile/.make 首行 `SHELL := /bin/bash`：make 执行每条规则都用 /bin/bash
   启动子 shell，OHOS 无 /bin/bash（bash 实际在 /storage/Users/currentUser/usr/local/bin/bash
   或 /data/service/hnp/bin/bash）。规则直接调 `g++` 时，OHOS 工具链只有 clang/clang++
   无 g++。两个符号都不存在 → "/bin/bash: No such file or directory" + Error 127。
2. POSIX CLI 源码只 include <iostream>/<string> 等 C++ 头，依赖 glibc 头文件链隐式
   暴露 getopt/optarg/optind 声明；OHOS libc++（musl 系）不隐式引入 getopt.h，
   -std=c++11 下编译报 "use of undeclared identifier"。

## 修复

1. 不依赖硬编码 SHELL/g++ 的 .make：用 clang++ 按 makefile 等价命令直接编译
   （`-D SAMPLE_XXX -x c++ ../include/alg.hpp` 等；需要 -pthread 的补 -pthread，
   需要 zlib 的 -lz -L<zlib lib>）。实测 hpptools 7 个样例 + 5 个测试目标全部编译
   通过并实跑。
2. 对使用 getopt 的 POSIX CLI 源文件显式 `#include <getopt.h>`（patches/ 补丁）。
   实测 zc.cpp 补 include 后编译通过，全部往返用例 diff 一致。

## 验证

- 7 样例 + 5 测试目标 clang++ 编译通过；test-alg 410 assertions in 9 test cases 通过；
  ztxtpipe/zpipe/zc 全部往返一致性通过；鸿蒙专项 ohos_special_test ALL PASSED；
  conan-verify G2-W3 全绿。

## 适用边界 / 反例

- 适用：上游自带手写 .make/Makefile 且硬编码 `SHELL := /bin/bash` 或直调 g++ 的项目；
  任何在 OHOS 使用 getopt/optarg/optind 的 POSIX CLI 源码。
- 不适用/反例：CMake 生成的 Makefile（其 SHELL=/bin/sh 被 hmmac 沙盒拒绝是 E346 场景，
  用 Ninja generator 解决）；脚本 shebang 首行 /bin/bash（E165 场景，sed 改 shebang）；
  链接期缺 glibc 扩展符号（E493，用 __progname）。这些场景另有专条，勿混用本方案。

## 查重差异

- similar_to: E346（make SHELL 主题）、E165（/bin/bash 缺失主题）、E493（OHOS libc++
  符号缺失主题）、E503（CLI getopt 参数行为）
- 新增差异：手写 .make 的 `SHELL :=` 变量 + g++ 缺失 + clang++ 等价命令直编的组合
  （E346/E165 均不覆盖）；编译期 getopt 头文件显式 include（E493/E503 均不覆盖）。
- exact/causal duplicate: false；combination/boundary/test-migration novelty: true。
