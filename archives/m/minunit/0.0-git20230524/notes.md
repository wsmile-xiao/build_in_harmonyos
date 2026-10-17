# minunit 0.0-git20230524 适配笔记

## 编译环境
- 构建系统: 无（header-only 单头文件库，上游根目录无 CMakeLists/Makefile）
- 编译日期: 2026-10-02
- 编译器: clang 15（OHOS aarch64，/data/service/hnp/bin，profile tools.build:compiler_executables 注入）
- 状态: built

## 背景与动机

minunit（siu / David Siñuela Pastor）是极简 C 单元测试框架：整个库只有一个头文件
`minunit.h`，提供 MU_TEST/MU_TEST_SUITE 测试定义、MU_RUN_TEST/MU_RUN_SUITE 驱动、
mu_check/mu_assert/mu_assert_int_eq/mu_assert_double_eq/mu_assert_string_eq 五断言宏
+ mu_fail、MU_REPORT 统计输出与 real/proc 计时、MU_EXIT_CODE 失败计数返回。
任务池 #14771 认领适配。

版本号依据：上游 master 线无 tag / 无 release（master-only 库），按仓库 master-only
规则取 `0.0-gitYYYYMMDD`：
- master HEAD `a0586569bd8abfb7a37390d670484c201e9173bf`（`git ls-remote` 实取）
- 该提交日期 2023-05-24（tarball 内文件时间戳 2023-05-25 00:36 一致佐证）
→ **0.0-git20230524**

W0 依赖核查（2026-10-02 实测）：
- minunit.h 全文审查：仅 C99 标准库（stdio/string/math）+ POSIX 计时器
  （unistd/time/sys/time/sys/resource/sys/times），**零第三方依赖** ✅
- `conan download minunit/* -r=ohpcd --only-recipe` → 不存在（新适配）✅

源码拉取与校验：
```bash
git ls-remote https://github.com/siu/minunit.git master
# → a0586569bd8abfb7a37390d670484c201e9173bf  refs/heads/master
curl -L -o master.tar.gz https://github.com/siu/minunit/archive/refs/heads/master.tar.gz
# sha256 = 144c2518446032b1181b7656e9ddeba0c51337afa6b32401bc05c4f30d873a6e
# tarball 内层目录 minunit-master/，get(strip_root=True) 展开
```

## 编译步骤

```bash
# 本地配方验证（W3，OHOS aarch64 profile）
conan create archives/m/minunit/0.0-git20230524 \
  -pr:h ~/.conan2/profiles/ohos-aarch64 -pr:b default --build=missing
# → build() 编译并运行上游官方测试 minunit_example（官方契约 exit==6 PASS）
# → test_package 消费者测试 PASS（minunit 断言宏真跑）

# 上游官方测试单独复跑（设备原生，官方 CI 同款口径）
/data/service/hnp/bin/clang -std=c99 -Wall -Wextra -I minunit-master/ \
  minunit-master/minunit_example.c -lm -o minunit_example && ./minunit_example
# → "11 tests, 11 assertions, 6 failures" + exit 6 = 官方 check PASS
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方测试程序退出码非零（6），常规"零退出码=PASS"判定会误判失败 | minunit 的 MU_EXIT_CODE = minunit_fail（失败计数）。官方 ci/check_example.sh 契约：exit==6 → PASS（11 用例中 6 个 `*_fail` 演示用例是框架故意失败的特性，用于验证断言捕获） | 配方 build() 内 `self.run(..., ignore_errors=True)` 取回 retcode，按官方契约 `retcode == 6` 判 PASS，否则 ConanException |
| 2 | 上游 ci/Makefile 在 Linux 下链接 `-lrt`，OHOS 是否需要 | Makefile 按 `UNAME_S == Linux` 分支追加；构建宿主 `uname -s` = HarmonyOS，按上游自身逻辑不链；且 OHOS musl 的 timer 符号（clock_gettime/times/sysconf）全在 libc，无独立 librt | 不追加 -lrt，仅 -lm（实测链接运行均正常） |
| 3 | header-only 库如何满足"上游测试进统计表" | 上游无 ctest/make check，官方测试形态是"编译 example + 断言退出码" | build() 中直接编译官方 minunit_example.c 并按 check_example.sh 契约运行；test_package 再用消费者视角真跑 minunit 断言（含预期失败用例的精确校验） |
| 4 | `-lrt` 与 musl 的关系记录 | OHOS musl：librt 为 stub，timer 函数并入 libc | knowledge 记录：遇到其他库上游按 Linux 分支链 -lrt 时，HarmonyOS 宿主天然走非 Linux 分支 |

## 源码修改

无需补丁（patches/ 为空，仅 .gitkeep）：
- minunit.h 在 OHOS clang15 -std=c99 下零警告（example 自身 2 个 unused-parameter 警告属上游源码风格）；
- `_POSIX_C_SOURCE 200112L` + clock_gettime/sysconf(_SC_CLK_TCK)/times 计时路径在 OHOS musl 全部可用；
- `__unix__` 分支自动命中（HarmonyOS 定义 `__unix__`），无需任何平台宏适配。

## 依赖版本

- 无（W0 实测：零第三方依赖，settings 归一后纯头文件交付）

## 验证结果

```bash
# 1) 上游官方测试（设备原生 + conan create build() 内各跑一遍）
#    编译: clang -std=c99 -Wall -Wextra -I<src> minunit_example.c -lm
#    运行: ./minunit_example → exit 6（官方契约 ci/check_example.sh）
#    输出: "11 tests, 11 assertions, 6 failures"（6 个 *_fail 演示用例按设计失败）
#    判定: PASS（官方口径）
# 2) conan create + test_package（消费者测试，minunit 断言宏真跑）
#    → PASS: 5 个正向断言用例（mu_check/mu_assert/mu_assert_int_eq/
#      mu_assert_double_eq/mu_assert_string_eq）全绿 + 5 个预期失败用例
#      逐一校验（断言消息内容 + MU_EXIT_CODE == 5）+ setup/teardown 计数校验
```

## 注意事项

- 版本号是 `0.0-git20230524`（master-only 规则），不是上游 tag——上游无任何 tag。
- 消费者用法：`#include <minunit.h>`（include/ 根，非 minunit/ 子目录）。
- CMake 目标 `minunit::minunit`；minunit.h 中的计时器在 `__unix__` 分支展开，
  Windows 消费者走 Windows.h 分支（OHOS 无关，保留上游原样）。
- cpp_info.system_libs = ["m"]：mu_assert_double_eq 用 fabs/log10（glibc 侧真实依赖；
  musl 中 libm 并入 libc，-lm 无害）。

---

**编译结束**: 2026-10-02
**最终状态**: built
