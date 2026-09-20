# polyseed 1.0.0 适配笔记

## 软件信息

- 名称: polyseed
- 版本: 1.0.0 (上游 tag `v1.0.0`, commit e3851656)
- 上游: https://github.com/tevador/polyseed (tevador, Monero 创始人之一)
- 许可: LGPL-3.0-only
- 语言: 纯 C (17 个 .c 文件, CMake 构建, C11)
- 性质: Monero/CryptoNote 16 词助记码种子库; 密码学原语与 UTF-8 规范化通过
  `polyseed_inject()` 运行时依赖注入提供, 库本身零第三方链接依赖

## W0 依赖检查

- conanfile `requires`: 无 (DI 设计, 上游 CMakeLists 不链接任何外部库)
- 制品仓无需预拉取依赖; `polyseed/1.0.0` 远端不存在 (本任务为首次适配)

## 上游测试申报 (R51)

- 测试目录: `tests/`, 单一文件 `tests/tests.c` (888 行, libc `assert()` 驱动)
- ctest 注册数: 0 (CMakeLists 仅 `add_executable(polyseed-tests)`, 无 enable_testing)
- main() 用例数: 51 (48 个 RUN_TEST + 3 个 RUN_MULT; 每个 RUN_MULT 展开 10 个语言
  subtest, 设备日志合计 78 行 PASSED)
- 源码断言点: 83 处 `assert(`
- 运行方式: 构建后直接执行 `./polyseed-tests`, 退出码即测试结果
- 真机实测 (HarmonyOS PC aarch64, clang 15.0.4): 见 reports/test-report.md

## 关键适配问题: AArch64 char 符号性

- 现象: 默认参数编译 (CFLAGS=-fPIC -O2) 后, 上游套件在
  `test_roundtrip1` (多语言 encode/decode 往返) 断言失败:
  `Assertion failed: res == POLYSEED_OK (tests/tests.c: test_roundtrip1: 505)`,
  SIGABRT (exit 134), 英语之后的首个非 ASCII 词表往返失败。
- 根因: `src/dependency.h` 的 `utf8_nfkd_lazy()` 与 `src/lang.c` 的
  `compare_str_noaccent()` / `compare_prefix_noaccent()` 均以 `*p < 0` 判定
  非 ASCII 字节, 该写法依赖 `char` 为有符号。AArch64 ELF ABI 默认
  `char` 无符号 (实测设备 `CHAR_MIN=0`), 非 ASCII 分支被静默禁用,
  多语言词表查表/比较路径行为改变导致往返失败。
- 实证: 同一设备、同一 clang, 仅追加 `-fsigned-char` 重新 configure+build 后,
  上游 51 用例全部通过 (78 行 PASSED, exit 0, 日志
  `probe-build/signed-tests.log`)。
- 修复: 不打源码补丁, 在 conanfile `generate()` 中注入
  `tc.extra_cflags.append("-fsigned-char")`, 保持上游源码逐字不动。
  该标志仅影响本库编译单元的 plain-char 解释, 公开头文件
  `include/polyseed.h` 无依赖 plain-char 符号性的内联逻辑, 对消费者无副作用。
- R8 合规: patches/ 为空, 无 `__OHOS__` 宏、无 `/usr/local`、无 SYS_PREFIX。

## 构建/打包说明

- 上游 CMakeLists 无条件同时构建 `polyseed` (SHARED) 与 `polyseed_static`
  (STATIC, OUTPUT_NAME polyseed) 并一并 install。配方按 `shared` 选项在
  `package()` 中删除另一形态, 保证消费者链接的正是其请求的库型。
- `build()` 中直接运行 `polyseed-tests` (上游无 ctest 注册), 使每次
  `conan create` 都真实执行上游套件。
- test_package 为消费者回归测试 (51 条实际执行断言), 含全部 10 种语言
  encode/decode 往返, 复现并守护 char 符号性问题。

## 验证记录

- lang-preflight (R47): task=cpp, detected=c, 兼容族通过 (源文件 17 个, c 100%)
- 探测构建: 设备原生 OHOS SDK clang 15.0.4, cmake 4.4.3, 一次通过, 零补丁
- 上游测试: 默认参数 FAIL (1 用例断言失败) → `-fsigned-char` PASS 51/51
- conan-verify: G0-G4 全部 PASS (VERIFY_RC=0), 见 reports/test-report.md 第 2 节
- 本地 CI 门禁 (G0/G0e/L0/KC/JC/L1/L1e/L2/L4/L5 全绿, Pass rate 100%):
  见 reports/test-report.md 第 4 节

---

**编译结束**: 2026-09-19 18:06
**最终状态**: built
