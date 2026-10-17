# quickfix 1.15.1 适配笔记

## 版本与发行渠道实核

- 上游仓库：github.com/quickfix/quickfix，`git ls-remote --tags` 实核存在
  `refs/tags/v1.15.1`（peeled commit `6908dc8c1084eeb7af7f322d35216e9965684489`）。
- 官网 quickfixdev.org **已不可达**（http/https 连接均失败），历史下载站不复存在；
  v1.15.1 的官方发行物 = GitHub tag 归档
  `https://github.com/quickfix/quickfix/archive/refs/tags/v1.15.1.tar.gz`，
  sha256 = `1c4322a68704526ca3d1f213e7b0dcd30e067a8815be2a79b2ab1197ef70dcf7`。
- 上游版本号怪癖：**configure.ac 的 `AC_INIT` 仍是 1.14.3**（上游对 1.15.x tag 忘记
  bump），公开 C++ API 也无版本宏。本包版本取自 release tag，不以 AC_INIT 为准；
  test_package 断言行为而非版本串。

## 编译环境

- 构建系统：autotools（tag 归档无预生成 configure，构建期 autoreconf -fi 自举）
- 编译器：clang/clang++（OHOS SDK，aarch64-unknown-linux-ohos）
- 工具依赖：`automake/1.18` + `libtool/2.5.4`（tool_requires，构建上下文）；
  autoconf/m4/perl 用 SDK 自带（声明 conan autoconf 会拉入 perl/5.42.2，
  其 XS 模块与 SDK perl 5.42.0 冲突 → `Perl_my_cxt_init` 崩溃，不声明）
- 状态：built

## 编译步骤

1. `autoreconf -fi`（先 `touch ChangeLog INSTALL`，GNU strictness 要求；
   与上游 bootstrap 脚本行为一致）
2. `./configure --build=aarch64-unknown-linux-gnu --host=aarch64-unknown-linux-gnu
   --enable-static --disable-shared`
   - config.guess 无法识别 HongMeng 内核（`uname` 显示 "HongMeng Kernel"），
     必须显式传 --build/--host；两三元组相同 ⇒ native configure，AC_TRY_RUN
     探针真实执行（select/timeval 探针实测走 "no" 分支）
   - config.status 的 `(umask 077 && mktemp -d)` 在 HMDFS 产生 drwx--S---
     目录，构建用户不可写 → PATH 前置 build-only mktemp wrapper（E114 房规）
3. `make libUnitTest++.a CXX=clang++ CXXFLAGS='-O2 -std=c++11'`（UnitTest++ 自带
   独立 Makefile 硬编码 `CXX = g++`，OHOS 无 g++；其源码仍用 `throw()` 动态异常
   规格，C++17 已移除，必须 C++11 编译）
4. `make -j1`（顶层 SUBDIRS 已剪枝，构建 libquickfix.a + at/ut/pt）
5. `cd test && ./ut -p 54321 -f cfg/ut.cfg`（上游单元测试入口）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `AtomicCount.h:163` 报 `unrecognized instruction mnemonic: lock / xadd` | 默认分支（GCC/Clang 通用）内嵌 x86 专用 `lock; xadd` 内联汇编，aarch64 汇编器拒绝 | patches/0002：改为 `__atomic_fetch_add(pw, dv, __ATOMIC_SEQ_CST)` 内建函数（同为返回旧值 + 全屏障，语义等价，全架构可用） |
| 2 | config.guess 报 `cannot guess build type` | 内核字符串 "HongMeng Kernel" 不在 guess 表 | 显式 `--build/--host=aarch64-unknown-linux-gnu` |
| 3 | configure 阶段 `could not setup config files machinery` | config.status 的 `(umask 077 && mktemp -d)` 在 HMDFS 落成 drwx--S--- 目录（本工作区已知缺陷 E114） | build-only mktemp wrapper PATH 前置（accel-config 4.1.9 同款房规） |
| 4 | 静态构建下 `all-local` 的 `ln -s .libs/libquickfix.so` 失败 | R26 静态库构建不存在 .so/.dylib | patches/0003：`-ln -s` 容错 |
| 5 | `make` 在 examples/tradeclientgui/banzai 失败 | build.sh shebang `#!/bin/bash`（OHOS 无 /bin/bash）且依赖 java/ant；UnitTest++ 顶层 Makefile 硬编码 g++ | patches/0001：顶层 SUBDIRS 剪枝 UnitTest++/examples/doc，UnitTest++ 由配方显式驱动 |
| 6 | `--without-openssl` 会导致 configure 报错 | ax_lib_ssl.m4 把非 "yes" 且非空的值当用户路径（"no/include/openssl/ssl.h"）→ AC_MSG_ERROR | 不传任何可选依赖开关，全部走上游缺省（缺省即禁用） |

## 源码修改

- patches/0001-makefile-am-prune-nonessential-subdirs.patch：SUBDIRS 剪枝
- patches/0002-atomiccount-replace-x86-inline-asm.patch：原子计数移植（aarch64）
- patches/0003-src-cpp-makefile-static-symlink-tolerant.patch：静态构建容错

## 依赖版本

- 硬依赖：无外部包（libc/pthread 由 OHOS bionic 提供）
- 可选依赖（全部维持上游缺省禁用）：OpenSSL（README.SSL 的 native SSL）、
  MySQL、PostgreSQL、Boost、STLPort、TBB、python2/python3/ruby/java SWIG 绑定
- 构建工具：automake/1.18、libtool/2.5.4（conan tool_requires）；autoconf 2.7x、
  m4、perl、bash、ruby、clang 由 SDK/HNP 提供

## 验证结果

- 单元测试（上游入口 `./ut -p 54321 -f cfg/ut.cfg`，真机实跑）：
  `Success: 200 tests passed.`，0 失败，rc=0，11.4 秒
- 验收测试（上游入口 runat.sh 形态：`at` acceptor + `ruby Runner.rb`，真机实跑）：
  definitions/server/fix4* + fix50 + fix50sp1 + fix50sp2 共 467 个 .def 用例
  逐条 `<test ... result='success'/>`（证据转 reports/*.md）
- 消费者测试（test_package）：clang++ -std=c++11 编译链接安装产物，9 项公开 API
  行为断言全通过
- C++ 标准：configure 尾部追加 `-std=c++0x`（C++11）最终生效；quickfix 1.15.1
  头文件大量使用 `throw(...)` 动态异常规格（C++17 移除）——**消费方必须 ≤C++14
  编译**，test_package 已显式 `-std=c++11`

## 注意事项

- 版本号以 release tag 为准（AC_INIT 滞留在 1.14.3，是上游已知怪癖）
- quickfixdev.org 已死；后续版本升级直接看 GitHub tags
- 头文件 C++17 不兼容（动态异常规格），下游若用 cppstd=17 会编译失败
- conan `make install` 附带安装 spec/*.xml 到 `share/quickfix/`（FIX 各版本数据字典），
  供需要 DataDictionary 的消费方使用
