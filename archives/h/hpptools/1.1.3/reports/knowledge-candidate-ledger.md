# 知识候选台账 — hpptools 1.1.3

任务类型：知识库扩展（task_type: 知识库扩展）。本台账记录适配过程中发现的
可跨库复用知识候选，逐项做四范围查重（knowledge/doc/、knowledge/graph/、
knowledge/drafts/、index.tsv）+ 引擎检索，并完成七轴查重与路径判断。

## 候选 #1：上游手写 .make 测试文件硬编码 `SHELL := /bin/bash` + `g++`，OHOS 两者皆无

- 真实错误（编译证据，cwd=$BUILD_SRC_DIR/examples）：
  ```
  g++ -std=c++11 ... -x c++ ../include/alg.hpp -o sample-alg
  make: /bin/bash: No such file or directory
  make: *** [sample-alg.make:8: sample-alg] Error 127
  ```
- 根因：hpptools examples/*.make 首行 `SHELL := /bin/bash`（make 执行每条规则用
  /bin/bash 启动 shell，OHOS 无 /bin/bash，bash 在 /storage/Users/currentUser/usr/local/bin/bash
  或 /data/service/hnp/bin/bash），且规则直接调用 `g++`（OHOS 工具链只有 clang/clang++，
  无 g++）。两个符号都不存在 → make 报 "/bin/bash: No such file or directory" 后 Error 127。
- 修复（已实测通过）：不依赖 .make，用 clang++ 按 makefile 等价命令直接编译
  （`-D SAMPLE_XXX -x c++ ../include/alg.hpp` 等），需要 -pthread 的补 -pthread；
  需要 zlib 的 -lz -L<zlib lib>。全部样例 + 测试目标编译通过并实跑。
- 验证：7 个样例 + 5 个测试目标全部 clang++ 编译通过；test-alg 410 assertions 通过；
  ztxtpipe/zpipe/zc 往返一致性通过。
- 适用范围：任何上游项目自带手写 Makefile/.make 且硬编码 `SHELL := /bin/bash`
  或直接调 g++ 的场景；OHOS 适配时需用 clang++ 等价命令或覆盖 SHELL 变量。
- 四范围查重：
  - index.tsv：E346（make 硬编码 SHELL，CMake 生成 Makefile + hmmac 沙盒拒绝 /bin/sh）、
    E165（脚本 shebang /bin/bash 不存在，configure 场景）命中关键词，但均非本模式。
  - knowledge/graph/E346.kv：CMake 生成 Makefile 的 SHELL=/bin/sh 被沙盒拒（Permission
    denied），与本模式（手写 .make + SHELL:=/bin/bash 路径不存在 + g++ 缺失）触发面不同。
  - knowledge/graph/E165.kv：脚本 shebang 首行 /bin/bash 不存在（sed 改 shebang），
    不覆盖 Makefile 内 `SHELL :=` 变量与 g++ 缺失。
  - knowledge/doc/：无对应条目。
  - knowledge/drafts/：无对应条目。
  - engine "make: /bin/bash: No such file or directory SHELL g++" → 命中 E165（shebang），
    非本模式。

## 候选 #2：OHOS libc++ 的 <iostream> 不隐式声明 getopt/optarg/optind，需显式 #include <getopt.h>

- 真实错误（编译证据，cwd=$BUILD_SRC_DIR/examples，zc.cpp）：
  ```
  zc.cpp:95:17: error: use of undeclared identifier 'getopt'
  zc.cpp:103:37: error: use of undeclared identifier 'optarg'
  zc.cpp:121:45: error: use of undeclared identifier 'optind'
  ```
- 根因：zc.cpp 只 include <iostream>/<string>/<vector>/<memory>/"zstr.hpp"，依赖 glibc
  头文件链隐式暴露 getopt 声明；OHOS libc++（musl 系）<iostream> 不隐式引入 getopt.h，
  且 -std=c++11 下 POSIX 函数不再由 C++ 标准库头隐式暴露。
- 修复（已实测通过）：源文件顶部显式 `#include <getopt.h>`（补丁
  patches/0001-zc-getopt-include.patch）。OHOS sysroot 存在
  /data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot/usr/include/getopt.h，
  显式 include 即可。
- 验证：补丁后 zc.cpp 编译通过；zc 全部往返用例（stdin/文件/-c/-o）diff 一致通过。
- 适用范围：任何 OHOS 上使用 getopt/optarg/optind 的 POSIX CLI 源码；glibc 隐式
  暴露 → OHOS libc++ 需显式 include。
- 四范围查重：
  - index.tsv：E493（program_invocation_name 未声明/链接缺失，musl 无 glibc 扩展符号）、
    E503（CLI getopt 短选项 --version/--help 行为）、E152（CLOCK_* 未声明）为不同符号。
  - knowledge/graph/*.kv：无 "getopt 未声明" 条目。
  - knowledge/doc/：E503 是 CLI 参数解析行为，E493 是 program_invocation_name，均不同。
  - knowledge/drafts/：DRAFT-13410 涉及 getopt.c/libintl（trueprint），不同场景。
  - engine "use of undeclared identifier 'getopt'" → 命中 E493（program_invocation_name，
    链接符号），非本模式；"getopt.h file not found undeclared identifier optarg" → E493，非本模式。

## 七轴查重结论

| 轴 | 候选 #1 | 候选 #2 |
|----|---------|---------|
| exact_duplicate | false（无相同条目） | false（无相同条目） |
| causal_duplicate | false（E346/E165 是 CMake 生成 Makefile / 脚本 shebang，本模式是手写 .make + SHELL:=/bin/bash + g++ 缺失） | false（E493 是链接符号，本模式是编译期头文件未声明） |
| trigger_overlap | partial（与 E346/E165 共享 "OHOS 无 /bin/bash" 主题，但触发面/工具/阶段不同） | partial（与 E493 共享 "OHOS libc++ 隐式符号缺失" 主题，但符号/阶段不同） |
| solution_overlap | partial（E346 fallback 提 SHELL 覆盖；本模式用 clang++ 等价命令直编，未见于任何条目） | none（显式 #include <getopt.h> 未见于任何条目） |
| combination_novelty | true（手写 .make + SHELL:=/bin/bash + g++ 缺失 + clang++ 直编组合为新差异） | true（iostream 不隐式暴露 getopt → 显式 include 为新差异） |
| boundary_novelty | true（边界 = 手写 makefile 内 SHELL 变量与 shebang 首行的差异） | true（边界 = 编译期头文件 vs 链接期符号） |
| test_migration_novelty | true（上游测试 .make 目标迁移到 OHOS 的 clang++ 直编法） | true（上游测试源码 zc.cpp 迁移需补 getopt.h） |

## 路径判断

- 两条候选均已实测验证（真实编译错误 + 修复后全部用例通过），可跨库复用
  （任何带手写 .make 测试文件 / 用 getopt 的 POSIX CLI 库），查重为未命中或部分覆盖
  且存在组合/边界/测试迁移新增差异。
- **决定：new_draft（路径 B，知识库扩展）**——建立同 stem 的 .md/.kv 草稿对。
- reuse_existing: false；path_a_no_knowledge: false。

## 草稿

- knowledge/drafts/hpptools-1.1.3-makefile-shell-gxx-and-getopt.kv / .md
  （两条候选合并为一个 stem 的草稿对，随本库归档进入同一 PR）
