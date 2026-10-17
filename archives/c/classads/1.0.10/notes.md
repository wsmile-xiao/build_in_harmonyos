# classads 1.0.10 适配笔记

## 软件信息
- 软件：classads 1.0.10（HTCondor ClassAd 语言 C++ 库）
- 任务号：6487（活动：开源鸿蒙PC专项积分赛）；分支 feat/classads-1.0.10；worktree ~/qzy/classads
- 构建系统：Autotools（tarball 自带 2011 年 configure）
- 编译日期：2026-09-09
- 编译器：clang/clang++ 15.0.4（OHOS SDK LLVM）
- 状态：published（conan-verify G0-G4/L2/L4/L5 全 PASS）
- 源码：https://ftp.cs.wisc.edu/condor/classad/c++/classads-1.0.10.tar.gz
  SHA256 cde2fe23962abb6bc99d8fc5a5cbf88f87e449b63c6bca991d783afb4691efb3
  （HTCondor 官网 https://research.cs.wisc.edu/htcondor/classad/ 链接的官方 tarball）

## W0/W0b
- W0：库零强制依赖。pcre 为上游可选探测项（--with-pcre=no 走 POSIX regex，musl
  自带）；dlopen 检测默认关闭。
- W0b：本仓库无 classads 历史归档；CI 能力矩阵 autotools/clang ✅。
- lang-preflight：PASS（task=cpp, detected=cpp）。

## 配方要点
- basic_layout + 手动 autotools 驱动（`cd src && CONFIG_SHELL=/bin/sh ./configure ... && make`），
  避免 conan 缓存 build-release 子目录在 HMDFS 上的 getcwd 失败风暴。
- `--build/--host=aarch64-unknown-linux-gnu` 显式三元组：2011 年 config.guess 不认识
  uname -s 返回的 HarmonyOS（E007/E160 同源；conan 在 host==build 时不传三元组）。
- `CONFIG_SHELL=/bin/sh` 内联覆盖：profile [buildenv] 的 CONFIG_SHELL=/data/service/hnp/bin/bash
  （OHOS 系统 bash）在 HMDFS 目录 getcwd 返回 Not supported，导致 configure 全程
  getcwd 风暴并死于 `cannot run bash ./config.sub`。
- 补丁 0001（E011 同源）：configure 内 config.status 临时目录 `(umask 077 && mktemp -d
  "./confstatXXXXXX")` 在 HMDFS setgid 目录上写文件 Permission denied，放宽为 umask 022
  （a52dec/0.7.4 先例 0002 同款）。
- 补丁 0002：OHOS SDK 26 的 libc++_shared.so / libc++_static.a 均不导出
  `operator<<(ostream&, basic_string)` 的显式实例化（llvm-nm 实证 0 命中），而 libc++
  头对 char 特化的 extern template 声明使 -O2 TU 对该符号发 U 引用；在库内
  （common.cpp/exprTree.cpp）以 asm 别名强定义提供符号（weak，可共存），库与全部
  上游测试程序及消费者链接通过。
- `LDFLAGS=-lc++`：2011 libtool 不为 clang++ 补 C++ 运行库。
- pcre 显式关闭（--with-pcre=no），POSIX regex 由 musl 提供。

## 上游测试统计与执行（R51）
- 静态清点：tests/Makefile.am TESTS 注册 **5 个测试程序**（namespace 默认关闭）：
  classad_functional_tester（驱动 functional_tests.txt 清单，345 行）、
  classad_unit_tester（内部计数 196 tests）、test_xml、sample（官方匹配示例断言）、
  extra_tests。
- 真机执行（签名后运行，LD_LIBRARY_PATH 指向 .libs）：
  - classad_unit_tester：196 tests，"Finished with no errors" ✅
  - classad_functional_tester：去除清单 XML 段（6 行）后 339 行全部通过
    "No errors" ✅；XML 段为上游清单与程序不匹配缺陷——清单中的
    writexml/readxml 命令 functional_tester 未实现（运行即挂起），XML 功能由
    独立 test_xml 程序覆盖验证 ✅
  - test_xml：✅；sample：✅（symmetricMatch=true 断言）；extra_tests：✅
- 上游测试程序 5/5 全部执行并通过（functional_tester 的 XML 段 6 行按上游缺陷
  如实剔除，剔除证据 ~/tmp/uc2/classads/ft*.log）。

## 消费者测试（test_package）
- test_package.cpp：ParseClassAd 解析 ClassAd → EvaluateAttrInt("memory")==4096
  断言 → Job/Machine ClassAd MatchClassAd symmetricMatch 断言 → PrettyPrint 输出。
- 源文件顶部定义 _LIBCPP_DISABLE_EXTERN_TEMPLATE（同库补丁 0002 机制）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cannot guess build type | 2011 config.guess 不识 HarmonyOS；conan 不传三元组 | 显式 --build/--host GNU 三元组 |
| 2 | getcwd 风暴 + cannot run bash ./config.sub | profile CONFIG_SHELL（OHOS bash）在 HMDFS getcwd 失败 | CONFIG_SHELL=/bin.sh 内联覆盖 + 源码目录内构建 |
| 3 | config.status confstat 写入 Permission denied | configure 内 umask 077 + HMDFS setgid | 补丁 0001 umask 022（E011/a52dec 先例） |
| 4 | functional_tester 等链接 undefined std::__n1 operator<< | SDK 26 libc++ 库无 ostream<<basic_string 显式实例化 | 补丁 0002 库内 asm 别名强定义 |
| 5 | make 全量后 No targets specified | config.status 失败导致 Makefile 未生成 | 由 3 修复后消失 |

## 依赖版本
- 无 conan 依赖（POSIX regex 由 musl 提供）

## 验证结果
- conan-verify：G0 PASS / G1 PASS / G2 PASS（conan create 干净构建 + 消费者实跑）/
  G3 PASS / G4 PASS / L2 PASS / L4 PASS / L5 PASS
- 上游测试：5/5 程序真机执行通过（functional_tester 清单 339/345 行覆盖，
  XML 6 行上游缺陷剔除并由 test_xml 程序覆盖）
- 消费者测试：1/1 通过

## 注意事项
- HMDFS 上 autotools 包 configure 必须 CONFIG_SHELL=/bin/sh（或非系统 bash），
  否则 getcwd 风暴（跨工具链通用，E007 家族新向量）。
- OHOS SDK 26 libc++ 无 ostream<<basic_string 导出符号：-O2 C++ TU 大量使用
  `cout << std::string` 的库需要类似 0002 的实例化提供（或 -O0 弱实例化）。
---

**编译结束**: 2026-09-09 23:19
**最终状态**: built
