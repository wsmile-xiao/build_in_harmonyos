# cln 1.3.7 适配笔记

## 软件信息
- 软件：cln 1.3.7（CLN - Class Library for Numbers，GiNaC 依赖的任意精度算术库）
- 任务号：6507（活动：开源鸿蒙PC专项积分赛）；分支 feat/cln-1.3.7；worktree ~/qzy/cln
- 构建系统：Autotools（autoconf 2.71 生成，configure 自带）
- 编译日期：2026-09-12
- 编译器：clang/clang++ 15.0.4（OHOS SDK LLVM）
- 状态：published（conan-verify G0-G4/L2/L4/L5 全 PASS）
- 源码：https://www.ginac.de/CLN/cln-1.3.7.tar.bz2
  SHA256 7c7ed8474958337e4df5bb57ea5176ad0365004cbb98b621765bc4606a10d86b

## W0/W0b
- W0：唯一依赖 gmp 已发布（制品仓 gmp/6.3.0 与 gmp/6.3.0.1，download 实测可取）；
  配方引用 gmp/6.3.0.1（适配修复版），--with-gmp=<依赖包前缀> 传入。
- W0b：本仓库无 cln 历史归档；CI 能力矩阵 autotools/clang ✅。
- lang-preflight：PASS（task=cpp, detected=cpp）。

## 配方要点
- basic_layout + 手动 autotools 驱动（源码目录内原地 configure/make，规避 conan
  缓存 build-release 子目录的 HMDFS getcwd 风暴）：
  `cd <src> && umask 000 && CONFIG_SHELL=/bin/sh TMPDIR=$HOME/tmp CC=... CXX=...
  ./configure --build/--host=aarch64-unknown-linux-gnu --with-gmp=<gmp_prefix>
  && make -j$(tools.build:jobs)`（jobs=2 与设备准入 conf 同源）。
- 三元组显式 GNU（build-aux/config.sub 实测不识 ohos）。
- CONFIG_SHELL=/bin/sh 覆盖：profile 注入的 OHOS bash 在 HMDFS getcwd 失败。
- 补丁 0001：mktemp -d 创建后补 chmod 0777（保留 mktemp 唯一命名与 stdout 回显）。**关键认知：mktemp -d 恒 0700、不经 umask，E011 的 umask 放宽处方对 mktemp 型无效**（r3/r4 实证）；mkdir -m 0777 替换为失败方案（mkdir 无 stdout 使 autoconf 主分支死代码，AI 检视实证后废弃），mktemp+chmod 为正确解。

## 上游测试统计与执行（R51）
- 静态清点：automake TESTS 注册 2 个测试程序。
  - exam：test_all() = test_elementary（6 数型 integer/rational/sfloat/ffloat/
    dfloat/lfloat × 5 运算 plus/minus/mul/floor/div = 30 个数据表测试函数）+
    test_gcd/test_xgcd/test_sqrtp/test_factorial/test_doublefactorial（5 个特殊）
    = 35 个叶子测试函数（每个遍历编译期数据表）。
  - tests：test_all(iterations) = test_I + test_MI + test_nt 3 个随机化属性测试组，
    默认各 10000 轮。
- 真机执行（签名后，rpath 指向包内 libcln.so）：exam RC=0 "Tests passed."；
  tests RC=0 "Tests passed."（各 1 次，日志 ~/tmp/uc2/cln/exam.log、tests.log）。
  随机化轮次 3×10000 = 30000 轮全部通过。
- CI 边界：上游套件可由 conan build() 内 make 复现，但为保持 CI 时长可控，
  配方 build() 不含 tests 构建（test_package 消费者验证包可用性）；上游套件
  在设备真机执行留证。

## 消费者测试（test_package）
- test_package.cpp：乘法循环构造 2^100 与移位路径 cl_I(1)<<100 交叉核对（两条独立
  代码路径）→ integer_length==101 位长断言 → exquo(2^100,2^50)==2^50 精确除 →
  mod(2^100,5)==1 → sqrt(2) 回乘精度断言（5 处断言）。
- conan-verify 实跑输出：`cln consumer test passed (2^100 mul==shift, bitlen 101,
  exquo/mod ok, sqrt ok)`。
- test() 显式前插被测包 lib 目录到 LD_LIBRARY_PATH（VirtualRunEnv 聚合在本环境
  缺被测包自身 libdir，动态加载会命中旧库致符号缺失）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status: could not setup config files machinery | mktemp -d 恒 0700 + HMDFS setgid 父目录 uid 错位写拒绝 | 补丁 0001：mktemp -d → mkdir -m 0777 |
| 2 | 无法 guess build type | 2022 config.guess 不识 HarmonyOS | 显式 --build/--host GNU 三元组 |
| 3 | getcwd 风暴 | profile CONFIG_SHELL（OHOS bash）在 HMDFS 失效 | CONFIG_SHELL=/bin/sh + 源码目录内构建 |
| 4 | 消费者运行符号缺失 | VirtualRunEnv 缺被测包 libdir | test() 显式前插 LD_LIBRARY_PATH |
| 5 | 验证器 3600s 超时杀 create | -j1 全量编译超默认预算 | timeout set cln 1.3.7 10800 + make 遵循 jobs=2 conf |

## 依赖版本
- gmp/6.3.0.1（制品仓）

## 验证结果
- conan-verify：G0-G4/L2/L4/L5 全 PASS（conan create 干净构建 + 消费者实跑）
- 上游套件：2/2 程序通过（exam 35 函数、tests 30000 随机轮）
- 消费者测试：1/1 通过

## 注意事项
- cln 无流输出算子（operator<< ostream），打印需 cln/io.h 的 fprint 系或自行格式化；
  消费者断言用比较/位长 API 替代打印。
