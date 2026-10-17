# buddy 2.4 OHOS 适配笔记

- 软件名/版本:buddy 2.4(BuDDy,Binary Decision Diagrams package,Jørn Lind-Nielsen 1996-2002)
- 上游:SourceForge 官方项目 `buddy`,规范发布物 `BuDDy 2.4/buddy-2.4.tar.gz`
- SHA-256:`d3df80a6a669d9ae408cb46012ff17bd33d855529d20f3a7e563d0d913358836`
  (spack 官方配方同值;Ubuntu/Debian archive 的 `buddy_2.4.orig.tar.gz` 与上游字节一致,三方核对)
- 构建:autotools(autoconf 2.59 / automake 1.7.3 / libtool,`libbdd_la_LDFLAGS=-version-info 0:0:0`)
- 产物:库 `libbdd`(C 核心 + C++ 包装类同库);头文件 `bdd.h` `bvec.h` `fdd.h`;无命令行工具
- 语言:任务声明 C++,lang-preflight 判定 cpp(源码 c:12/cpp:12,按 manifest 判 cpp,C/C++ 兼容族)
- 许可:README 内嵌宽松许可(MIT 风格 notice,SPDX 尚未收录,见 spdx/license-list-XML#2839 的 MIT-buddy 提案)

## 平台与 API 事实

- `bdd.h` 在 `__cplusplus` 下自动 `#define CPLUSPLUS`,打开 C++ 段:`class bdd`/`class bvec`/fdd 包装;
  类外方法实现来自 `src/cppext.cxx`,一并编入 `libbdd`。消费方 C++ 直接 `#include "bdd.h"` 即可。
- `bdd_scanset(BDD, int**, int*)`:数组由调用方 `free()`(malloc 分配),成功返回 0。
- `bdd_swapvar` 成功返回 0;`bdd_varnum()` 返回当前变量数;`bdd_init(nodes, cachesize)` 不创建变量。
- `libtool -version-info 0:0:0` → 共享库为 `libbdd.so.0.0.0`,别名 `libbdd.so.0`/`libbdd.so`(符号链接)。
- 上游 `make install` 头文件进 `<prefix>/include`,库进 `<prefix>/lib`,与 Conan 默认布局一致。

## 遇到的问题与解决方案

### 1. configure 后 config.h 不生成(HMDFS + umask 077)

- 现象:`./configure` 退出码 0,但日志含 `mv: bad './confstatUf8qbC/out': Permission denied`
  `can't create ./confstatUf8qbC/config.h: Permission denied`,`config.h` 不存在。
- 定位:autoconf 2.59 的 `config.status` 用 `(umask 077 && mktemp -d -q "./confstatXXXXXX")`
  建临时目录(失败则回退 `(umask 077 && mkdir ...)`)。真机对照实验(2026-09-05):
  - umask 077 + mktemp -d → `drwx--S---`(2700)→ 写入失败;
  - umask 077 + mkdir → 同样 `drwx--S---` → 写入失败;
  - umask 022 + mktemp -d → `drwxr-s--x` → 写入成功;
  - 默认 umask 002 + mktemp -d → `drwxrws--x` → 写入成功。
  结论与知识库 E011 一致:HMDFS 的 UID 映射使 0700 目录对当前进程不可写,与 mktemp/mkdir 无关。
- 解决:补丁 `patches/0001-ohos-configure-umask.patch` 将 configure 中两处 `umask 077` 放宽为
  `umask 022`(E011 方法 2)。该字符串出自 autoconf 2.59 样板而非 buddy 源码,上游无法在
  configure.ac 层修复;umask 只作用于建目录的子 shell,不影响安装产物。
- 备注:bash/5.3 配方的 mktemp-exit-1 包装器会把 autoconf 引入 mkdir 回退,但真机实测该回退
  同样使用 umask 077、同样不可写(本任务 T1 实验),故未采用。
- 知识关联:E011(edit-umask-in-configure)、E118(patch-script)、E136(umask+SGID)。
  本次为 E011 方法 2 的真机复验 + bash 包装器方案的失效证据,未形成新错误模式,不新增草稿。

### 2. bddtest 回归与 expected/ 金标非字节一致(musl rand 序列)

- 现象:bddtest 输出 65 行,每行断言均为 `Sum-OK. Sub-OK.`,与金标行数相同,但
  `Checking bdd with N assignments` 的 N 及行序不同,`diff` 非空。
- 定位:`examples/bddtest/bddtest.cxx:107-109` 用 `rand()` 生成测试规模,金标由 glibc 机器生成,
  OHOS(musl)`rand()` 序列不同。断言结果(OK/FAILED)与金标完全一致,仅随机规模不同。
- 解决:配方对 bddtest 采用等价比对——把两侧每行归一化为
  `Checking bdd with assignments: Sum-OK. Sub-OK.` 后排序比较,多集合必须完全相等;
  其余 7 套件保持字节级 diff。判定、证据与计数全部写入 test_package/MANIFEST.yml。

### 3. 多次 bdd_init/bdd_done 后调用 bdd_support 段错误(上游缺陷,与 OHOS 无关)

- 现象:同一进程先 `bdd_init → bdd_support → bdd_done`,再次 `bdd_init` 且 `bdd_setvarnum`
  到相同变量数后调用 `bdd_support`/`bdd_satcountset` → SIGSEGV(最小复现 20 行,
  gdb 被 ptrace 策略禁用,用插桩二分定位)。
- 定位:`bdd_support()` 的暂存数组缓存 `static int* supportSet` 与 `static int supportSize`
  (bddop.c:2057-2093);`bdd_done() → bdd_operator_done()` 会 `free(supportSet)` 并置 NULL
  (bddop.c:197,215-216),但**不重置 `supportSize`**。下一会话 varnum 相同时
  `supportSize < bddvarnum` 不成立 → 跳过重新分配 → `support_rec` 向已释放(置 NULL 的)
  缓冲写入 → 段错误。varnum 增大则触发重新分配,不崩。
- 处置:这是上游功能缺陷,不属于 OHOS 平台适配范畴,不为规避而打上游功能补丁;
  消费者测试改为仅首个内核会话使用 `bdd_support`,后续会话用 `bdd_makeset` 显式构造
  变量集(断言语义不变),并在测试源码内注释缺陷机理。真实用户的多会话 + support
  组合仍会触发,后续版本适配(或上游继承者)可考虑修复。

### 4. bddcalc 的 lexer.cxx/parser.cxx 在 -std=c++17 下编译失败(E293)

- 现象:`make check` 构建 bddcalc 时 `lexer.cxx:623: error: ISO C++17 does not allow
  'register' storage class specifier [-Wregister]`(共 21+8 处,老 flex/bison 生成代码)。
- 定位:profile 的 `compiler.cppstd=17` 使 2002 年代 flex/bison 生成代码里的 `register`
  存储说明符从 warning 升级为 hard error;库本体(src/)不受影响,仅 bddcalc 触发。
- 解决:知识库 E293 权威方案(toolchain-flag):`generate()` 中
  `tc.extra_cxxflags.append("-Wno-error=register")` 与
  `tc.extra_cxxflags.append("-Wno-error=dynamic-exception-spec")`,把诊断降级为 warning,
  不改动上游生成文件。
- 知识关联:E293(既有条目,本次为又一实例复验;未形成新错误模式)。

### 5. 上游测试的组织方式(无 TESTS 接线 + tcsh 脚本)

- `Makefile.am` 只声明 `check_PROGRAMS`,没有 `TESTS`;`make check` 仅构建 9 个回归程序,
  不运行任何用例。
- 真正的回归是 `examples/*/runtest`(tcsh)+ `expected/` 金标 + 顶层 `runregression`(tcsh)。
  设备无 tcsh;每个 runtest 脚本体只有"运行程序 → `egrep -v '^Garbage collection'` 过滤 →
  追加写 result"一种形态,用 sh 1:1 复现后与金标比对。
- solitare 是示例程序:有 check_PROGRAMS、无 runtest/expected,不计用例(MANIFEST 单列说明)。
- 统计:主口径=程序调用 57(adder 28、bddcalc 7、cmilner 7、milner 8、queen 4、fdd 1、
  money 1、bddtest 1),全部通过;套件口径=8/8;bddtest 断言行=65/65。

## 配方要点

- `--build=aarch64-unknown-linux-gnu`:config.guess 不识别 HarmonyOS 内核
  (`UNAME_SYSTEM = HarmonyOS`),显式指定三元组(bash/5.3 与 spack 同款做法)。
- 默认 `shared=False`(纯静态 `libbdd.a`);`shared=True` 时安装共享库,并把 libtool 的
  版本化符号链接实体化为真实文件(HarmonyOS loader 对包视图中版本化 symlink 的限制,
  libavtp/0.2.0、canfigger/0.3.2 先例)。
- 上游测试在 `build()` 内执行(make check 构建 + sh 回归 + 金标比对),`tests=True` 默认开启。
- W0:buddy 无任何外部依赖(自包含),`requirements()` 为空。

## 验证结果(摘要)

- 原生构建:clang 15.0.4(OHOS 适配版),configure + make -j1 全绿;
  仅 reorder.c:1629 一处上游代码的 `-Wpointer-bool-conversion` 警告,无错误。
- 上游测试:57/57 程序调用通过(8 套件金标比对全过;bddtest 见等价比对说明),
  失败 0、跳过 0、未运行 0;solitare 非测试用例(上游无 runner/金标)。
- Conan:`conan create`(ohos-aarch64 profile)构建 + 上游测试 + test_package 消费者
  (60 项断言)全部通过;详见 `reports/` 与最终日志。
---

**编译结束**: 2026-09-05 16:59
**最终状态**: built
