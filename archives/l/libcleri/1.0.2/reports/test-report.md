# libcleri 1.0.2 verification report

## Environment

- OpenHarmony/HarmonyOS PC aarch64 (runner PC2)
- Clang 15.0.4
- Conan 2.29.1 (OHOS 适配版)
- pcre2/10.45.1.1 (ohpcd 发布二进制, armv8/OHOS/clang15)

## Source

- 上游: https://github.com/cesbit/libcleri, release tag `v1.0.2`
- tarball SHA-256: `7180ed1f215c30fba601a150ef9eb7a54f6efd4cf8f130bb4c5ed86ac03bc9c5`
- 构建系统: Eclipse-CDT makefile 工程（无 configure；`cd Release && make all`），链接 `-lpcre2-8`

## Verification

- lang-preflight (R47): task=cpp, detected=c（C/C++ 兼容族）→ 通过
- 本地编译: `cd Release && make all CC=clang -lpcre2-8` → exit 0，产出 `libcleri.so`（SONAME libcleri.so.1）
- 上游测试: `cd test && bash ./test.sh`（15 个 test_* 目录、23 个测试组，运行时断言 **314/314 全部通过**）→ exit 0
  - 注入: `PATH=<clang wrap> CPATH=<pcre2 include> LIBRARY_PATH=<pcre2 lib> NOMEMTEST=1`
  - 运行时断言计数口径：对上游 test 源码做只读副本注入 `test_end()` 打印 `count`（`test.h` 内置 `_assert` 逐条计数），逐测试组求和 = 314，全部断言通过、无 FAILED。
  - 历史 179 仅为 test_*/*.c 中静态 `_assert` 子串出现次数（含宏名与注释），不是验证结果总数，本轮已弃用。
  - 日志: /storage/Users/currentUser/tmp/logs/libcleri-upstream-test-r02.log（原始，exit 0）；计数副本日志: /storage/Users/currentUser/tmp/logs/libcleri-upstream-test-count-r02.log
- conan-verify libcleri 1.0.2（ohos-aarch64 profile）: exit 0
  - G1 配方完整性: PASS；G2 conan create（干净构建 + test_package）: PASS
  - G3 系统同名库隔离 (R26): PASS；G4 产物完整性: PASS
  - L2 平台 smoke test: skip（纯库无 bin/）；L4 静态安全扫描: PASS；L5 产物基线: PASS
- W3 本地 CI 模拟（ci/conan/build_and_test.sh，full 模式）: PASS
  - 期间隔离无关历史基线 `archives/u/util-linux-login/2.42.2/.ci-trigger`（HEAD 已跟踪空文件）→ 复验通过 → 已无条件恢复（恢复后该路径 git 状态干净）

## test_package

test_package/test.c 构建小文法（keyword+regex+sequence）并用 `cleri_parse` 断言
`hi "Iris"` 合法、`bye "Iris"` 非法；test 经 ctest 实际执行。

- Test cases: 2（1 个 ctest；内部 2 个 parse 断言）
- Passed: 2；Failed: 0；Skipped: 0

## Result

配方在 OpenHarmony PC (aarch64) 设备上验证通过，产物 libcleri.so（含
libcleri.so.1/libcleri.so.1.0.2 版本化软链）与 22 个头文件打包完整，具备
built 状态条件；发布（published）需 CI release 流水线 upload 后确认。