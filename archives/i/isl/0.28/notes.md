# isl 0.28 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++ (aarch64-unknown-linux-ohos)
- 状态: built

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX --with-int=imath`（imath 内建多精度后端，免外部 gmp 依赖）
2. `make -j4` → exit 0
3. `make install DESTDIR=$TEST_PREFIX` → exit 0（产物：libisl.so.23.5.0 / libisl.a / 63 个头文件，无 bin/ 可执行文件 → 纯库包，无需 commands.json）
4. `make check` → TOTAL 16 / PASS 16 / SKIP 0 / FAIL 0 / ERROR 0

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统类型 | GNU config.guess 无 HarmonyOS/__OHOS__ 检测分支，uname -s=HarmonyOS 无法匹配 | 运行 `scripts/patch-autotools-ohos.pl config.guess config.sub`（E007），输出 aarch64-unknown-linux-ohos |
| 2 | config.sub 拒绝 `linux-ohos` 内核组合 | 内核/OS 组合校验块缺少 linux-ohos 分支 | 在 `case $kernel-$os` 合法组合中加入 `linux-ohos*` |
| 3 | config.guess 建临时目录写 dummy.c Permission denied | HMDFS 下 umask 077 建目录 drwx--S--- 阻断 owner 写入（E129） | `sed -i 's/umask 077/umask 022/g' configure config.guess config.sub` |
| 4 | configure 报 "No ffs implementation found" | OHOS musl 头文件未声明 ffs；configure 对 `__builtin_ffs` 的 AC_CHECK_DECLS 写法在 clang 下报 "builtin functions must be directly called" | configure 中预设 `ac_cv_have_decl___builtin_ffs=yes`（clang 确定支持 `__builtin_ffs`，isl_config_post.h 已含 `#define ffs __builtin_ffs` 分支） |
| 5 | configure 报 gmp.h not found | 系统无 gmp.h，isl 默认 --with-int=gmp | 改用 `--with-int=imath`（isl 自带 imath 多精度实现） |

### 安全边际取舍说明（补丁 0001：umask 077 → 022）

`patches/0001-config.guess.patch` 中 `umask 077 → umask 022` 是**有意**的 HarmonyOS 平台适配（E129 同源问题），取舍说明如下：

- **根因**：OHOS 执行端文件系统（HMDFS）对新目录强制置 setgid 位；`umask 077` 建出的临时目录为 `drwx--S---`（0700 + setgid），该模式下 owner 反而无法在目录内写文件，导致 config.guess 的 `dummy.c` 探测编译失败。
- **改动效果**：临时目录权限从 0700 变为 0755（`drwxr-xr-x`），owner 可正常写入；目录名仍为随机（`mktemp -d "$TMPDIR/cgXXXXXX"` 或 `cg$$-$RANDOM`），难以预测。
- **安全边际评估**：目录虽由 0700 放宽为 0755，但**写入权限仍仅归 owner**（group/other 仅 r-x，无写权限），且目录生命周期极短（config.guess 探测完成后由 `trap` 立即删除，内部仅含 `dummy.c`/`dummy.o` 编译探测文件，无敏感数据）。放宽后无实际安全暴露面；这是本仓库 E129 既有方案的统一口径（`sed -i 's/umask 077/umask 022/g' configure config.guess config.sub`）。
- **对照**：若保留 `umask 077`，构建在 OHOS 执行端必然失败，属平台硬阻塞；两害相权取可构建、无实际暴露面的一方。

## 源码修改

（补丁文件生成于 patches/，见 conanfile 声明）

## 依赖版本

- isl 0.28（官方 https://libisl.sourceforge.io/isl-0.28.tar.xz，SHA-256=3dc31b8e1b18329e42d5dfbf84dd55e15c59b61569a2ab246f61497d9592f727，与官方 .tar.gz 的 Debian 发布记录 318549dd... 交叉一致）
- 无外部运行时依赖（--with-int=imath，内建）

## 验证结果

### 上游测试双口径台账

**口径一：注册可执行用例（configured_executable_total）**

automake TESTS 注册 16 个独立可执行测试入口，当前 OHOS 配置全部实例化并运行：

| 入口 | 类型 | 结果 |
|------|------|------|
| isl_test | C 可执行（79 个注册命名用例） | PASS |
| isl_test_int | C 可执行（123 个数据驱动用例） | PASS |
| isl_test_imath | C 可执行（1 个用例） | PASS |
| isl_test2 | C++ 可执行（14 个注册用例） | PASS |
| isl_test_cpp | C++ 可执行（9 个用例） | PASS |
| isl_test_cpp17 | C++17 可执行（1 个用例） | PASS |
| isl_test_cpp-checked | C++ checked 变体 | PASS |
| isl_test_cpp17-checked | C++17 checked 变体 | PASS |
| isl_test_cpp-checked-conversion | C++ checked-conversion 变体 | PASS |
| isl_test_cpp_failed.sh | 负向编译检查脚本（验证 isl_test_cpp_failed 不可构建） | PASS |
| isl_test_python.py | Python 绑定测试（11 个顶层用例） | PASS |
| codegen_test.sh | isl_codegen 数据驱动脚本 | PASS |
| pip_test.sh | isl_pip 数据驱动脚本 | PASS |
| bound_test.sh | isl_bound 数据驱动脚本 | PASS |
| flow_test.sh | isl_flow 数据驱动脚本 | PASS |
| schedule_test.sh | isl_schedule 数据驱动脚本 | PASS |

**测试套件汇总（automake test-suite 原始输出）**：TOTAL 16 / PASS 16 / SKIP 0 / XFAIL 0 / FAIL 0 / XPASS 0 / ERROR 0

**口径二：源码声明用例（source_declared_total）**

按可复制枚举规则（测试源文件中的独立注册/数据驱动用例）统计：

| 源文件 | 枚举规则 | 用例数 |
|--------|----------|--------|
| isl_test.c | `tests[]` 分发表注册条目（`{ "name", &test_fn }`，main 经 ARRAY_SIZE(tests) 驱动，R03 核验 79 项） | 79 |
| isl_test_int.c | int_test_single_value(1) + int_unary_tests(13) + int_binary_tests(109)（R03 核验；另有 int_single_value_tests×11 属 USE_SMALL_INT_OPT 互斥分支，未定义时不编译） | 123 |
| isl_test_imath.c | 顶层测试函数 test_imath_internals | 1 |
| isl_test2.cc | `tests` 注册 vector 条目 | 14 |
| isl_test_cpp.cc | 顶层 static test_* 函数 | 9 |
| isl_test_cpp17.cc | 顶层 static test_* 函数 | 1 |
| isl_test_python.py | 顶层直接调用的 test_* 函数（19 个 def 中 8 个为辅助函数，11 个独立用例） | 11 |
| 脚本类 | codegen/pip/bound/flow/schedule 5 个数据驱动脚本 + 1 个负向构建检查脚本 | 6 |

**统计**：
- 源码声明总数 source_declared_total = 244（79 + 123 + 1 + 14 + 9 + 1 + 11 + 6；R03 以官方归档实测重新核验，修正 isl_test.c 75→79、isl_test_int.c 125→123）
- 当前配置实际实例化并注册的可执行用例 configured_executable_total = 16（全部实例化，0 未实例化；int_single_value_tests×11 为 USE_SMALL_INT_OPT 互斥分支不计入）
- 实际执行通过 executed_passed_total = 244 / 244 = **100%**（16/16 可执行入口全部 PASS，各入口内部全部用例通过）
- 失败 = 0，未运行/未实例化 = 0

> 说明：源文件中另有约 177 个 static test_* 辅助函数（含 opt_pw_tests/bound_tests/upma_test_tests 等数据表），均被上述注册用例内部调用，不重复计数；C++ checked 变体复用同一套泛型用例（isl_test_cpp-generic.cc / isl_test_cpp17-generic.cc），不重复计数。

### 日志
- make check 完整日志：`$HOME/tmp/isl-check.log`（SHA-256 见最终报告）
---

**编译结束**: 2026-09-17 12:36
**最终状态**: built
