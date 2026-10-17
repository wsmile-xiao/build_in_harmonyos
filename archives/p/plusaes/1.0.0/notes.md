# plusaes 1.0.0 适配笔记

## 编译环境
- 构建系统: custom（上游源码根目录没有构建入口；配方直接调用 clang++ 编译上游测试 TU）
- 编译日期: 2026-09-27
- 编译器: clang 15.0.4（`/data/service/hnp/bin/clang++`，target aarch64-unknown-linux-ohos）
- 目标平台: HarmonyOS PC arm64（os=OHOS, os.version=6.0, arch=armv8, compiler.libcxx=libc++）
- 状态: built

## 版本与来源核验（W0）

- 上游 tag：`git ls-remote --tags https://github.com/kkAyataka/plusaes` 共 **6 个 tag** 全部命中
  （v0.0.1 / v0.9.0 / v0.9.1 / v0.9.2 / v0.10.0 / **v1.0.0 = b521b898bac522dca67175edaa1b8b5791c6e22b**）。
- 源码 sha256 **三处同值**：本地 curl 下载、`conan create` 内 `get()` 下载、
  conan-center-index `recipes/plusaes/all/conandata.yml` 记录值，均为
  `0e33e8d0e2ea5e6f9eb7a06093f576350ce8ef58339ce9de791514a8f433087d`。
- 依赖：**0**（`package_type = header-library`，无 requires / tool_requires；
  上游测试内嵌 gtest 源码，不需要外部测试依赖）。
- 平台可移植性（W0-3）：ISA 专属头与 glibc printf 钩子族 grep **0 命中**。
  裸 `sse`（忽略大小写）在仓库内有 493 处命中，**全部**位于
  `unit_test/lib/include/gtest/**` 的 `ASSERT_`/`EXPECT_` 宏名与注释中（如 `ASSERT_DEATH`），
  核心头 `include/plusaes/plusaes.hpp` 命中数为 **0** —— 即所谓 SIMX/SSE 命中系
  `ASSERT_*` 子串误报，不在构建面上；配方不引入任何 `-msse*`/`-m*` 相关选项。

## 编译步骤

配方 `build()`（R33：编译器取自 `tools.build:compiler_executables`，不读 shell 环境变量）：

1. 直接调用 `clang++ -std=c++11 -O2 -Wall -I include -I unit_test/lib/include
   -I unit_test/src/gtest <gtest-all.cc + main.cpp + test-{ctr,gcm,inc,plusaes}.cpp>
   -lpthread -o plusaes_unit_test` —— TU 清单与上游 `lin/unit_test/Makefile.am`
   的 `unit_test_SOURCES` 逐条一致。
2. `./plusaes_unit_test --gtest_list_tests` —— 打印框架注册用例（N 的权威读数）。
3. `./plusaes_unit_test` —— 全量执行，`[==========] 111 tests from 8 test suites ran`
   与 `[  PASSED  ] 111 tests.` 进入 `conan create` 日志。

`package()` 把 `include/plusaes/plusaes.hpp` 装进 `include/`、`LICENSE_1_0.txt`
装进 `licenses/`（`package(): Packaged 1 '.hpp' file` + `1 '.txt' file`）。
`test_package` 用 CMake `find_package(plusaes)` → `plusaes::plusaes` 编译消费者程序并 `self.run()` 执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `TypeError: get() got an unexpected keyword argument '1.0.0'` | `conandata.yml` 的 `sources` 按版本号分层，直接 `**self.conan_data["sources"]` 把版本键当参数展开 | 改为 `self.conan_data["sources"][self.version]` |
| 2 | 上游唯一构建骨架 `lin/`（bootstrap→configure→make）在 CI worker 上不可用 | `bootstrap` 要 `autoheader/aclocal/automake -a/autoconf`，worker PATH **无 automake**（设备 harmonybrew 有 ⇒ 设备全绿不等于 CI 绿） | 配方不走 autotools，按 `lin/unit_test/Makefile.am` 的 TU 清单直接编译同一组源文件 |
| 3 | 上游没有 `make check` 入口 | `lin/unit_test/Makefile.am` 用 `bin_PROGRAMS = unit_test` 且未声明 `TESTS`，构建出二进制但不自动执行 | 以 gtest 二进制自身做层 1：`--gtest_list_tests`（注册数）+ 全量执行（PASS/FAIL），均落在 `conan create` 日志 |
| 4 | 消费者测试编译报 `no matching function for call to 'key_from_string'` | `key_from_string` 按**数组长度**重载（17/25/33），字面量必须正好 16/24/32 字符 | 采用上游 `test-plusaes.cpp` 的字面量 `"123456789012345678901234"`、`"abcdefghijklMNOPQRSTUVwxYz789012"` |
| 5 | `decrypt_*` 返回的 `padded_size` 与「原文长度」直觉相反 | 源码 `*padded_size = last[15]` 写的是 **PKCS 填充长度**，原文长度 = 密文长度 − padded_size | 断言按该语义写：`padded_size == 1` 且 `len - padded_size == 15`，并逐字写进 `notes` 与 `MANIFEST.yml` |
| 6 | CTR 已知答案初判失败（凭记忆写的期望值 `874d6191…` 不符） | 记忆值有误，非实现问题 | 用独立的 `openssl enc -aes-128-ecb` 对同一 key/计数块交叉核验：`E(key,ctr)=727b7f12b22722038ea2c4643f2062ed`，⊕ 明文 = `19bac1f09c67bd95679fba754cb375c7`，与 plusaes 输出逐字节一致；CBC 首块同样经 openssl 复算得 `7649abac8119b246cee98e9b12e9197d`（= NIST SP 800-38A F.2.1） |
| 7 | CMake 打印 `System is unknown to cmake, create: Platform/HarmonyOS` | 该设备 CMake 4.1.2 无 HarmonyOS 平台模块（OHOS 适配版 conan 把 `os=OHOS` 映射为 `CMAKE_SYSTEM_NAME=HarmonyOS`） | 仅告警、非致命：configure/build/test 三段 rc 全 0，消费者二进制真实执行 25 checks 全过；未改 `CMAKE_SYSTEM_NAME` 以免偏离 conan 官方 toolchain 行为 |

## 源码修改

无。本次适配 **0 个补丁**（`patches_applied: []`）：上游 `include/plusaes/plusaes.hpp`
（1301 行）、`unit_test/**`、`lin/**` 全部逐字节保持 v1.0.0 原貌，所有适配都在配方侧完成。

## 依赖版本

- 运行期/编译期依赖：无（0 依赖）。
- 测试依赖：无外部依赖，gtest 源码随上游归档内嵌（`unit_test/lib/include/gtest` + `unit_test/src/gtest/gtest-all.cc`）。
- 构建工具：设备/CI 自带 clang 15.0.4、CMake 4.1.2、Conan 2.29.1。

## 验证结果

```bash
# 层 1 + 层 2（同一命令即采信轮所用）
conan create archives/p/plusaes/1.0.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
#   [+ ] conan create rc=0
#   [+] 111 tests from 8 test suites ran → [  PASSED  ] 111 tests.
#   [+] test_package: 25 checks passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| `include/plusaes/plusaes.hpp` | 头文件本体（1301 行，ECB/CBC/CTR/GCM） |
| `licenses/LICENSE_1_0.txt` | Boost Software License 1.0 |

## 注意事项

- **header-only 交付形态**：包内无 `lib/`、无 `bin/` ⇒ 无 `commands.json`（R38/L0k 正确）；
  消费者按 device-facts §二 的口径需人工补测（本次 `test_package` 已在设备真跑 25 项断言）。
- **上游源码根无构建入口**（构建骨架在 `lin/` 子目录）⇒ `finish` 的 G0 clean-verify
  按入口探测必然落空，属**非阻塞**告警（`step25_g0_clean_verify` 只 warn 不改判），
  与 G2/`conan create` 的真实结论互不影响。
- 上游 `lin/configure.ac` 的版本号仍写 `0.0.1`（上游自身的陈旧值），配方与 manifest
  一律以 `1.0.0` 为准。
