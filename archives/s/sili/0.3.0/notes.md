# sili 0.3.0 适配笔记

## 编译环境
- 构建系统: makefile（单头库，Makefile 驱动）
- 编译日期: 2026-09-19
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，--target=aarch64-linux-ohos）
- 交叉工具链: llvm-ar / llvm-ranlib
- 状态: published

## 编译步骤

sili 为单头 C99 库（sili.h + sifig.h），官方 Makefile 使用 `-D SI_IMPLEMENTATION -c sili.h` 产出静态库。

```bash
# OHOS aarch64 交叉编译静态库
SYSROOT=/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot
CC=/data/service/hnp/bin/clang
$CC --target=aarch64-linux-ohos --sysroot=$SYSROOT -O3 -std=c99 \
    -Wall -Wextra -Wpedantic -fPIC -x c -D SI_IMPLEMENTATION -c sili.h -o build/sili.o
llvm-ar rcs build/libsili.a build/sili.o

# 每个上游测试独立编译并运行（Makefile compile_tests 同口径）
for t in bit char general print str system; do
  $CC --target=aarch64-linux-ohos --sysroot=$SYSROOT -O3 -std=c99 \
      -I. tests/$t.c build/libsili.a -lpthread -ldl -o build/tests/$t
  ./build/tests/$t   # exit 0
done
```

## 上游测试全量枚举台账（R51 申报表）

### 测试源与框架
| 项目 | 文件 | 类别 | 是否独立上游用例 | 说明 |
|------|------|------|------------------|------|
| 用户测试源 | tests/bit.c | 用户测试源 | ✅ 2 个用例 | test_bit / test_overflow（main 调用） |
| 用户测试源 | tests/char.c | 用户测试源 | ✅ 1 个用例 | main 内 TEST_START 内联测试 |
| 用户测试源 | tests/general.c | 用户测试源 | ✅ 1 个用例 | main 内 TEST_START 内联测试（7 个编号子块为打印分隔，非框架用例） |
| 用户测试源 | tests/print.c | 用户测试源 | ✅ 1 个用例 | main 内 TEST_START 内联测试 |
| 用户测试源 | tests/str.c | 用户测试源 | ✅ 3 个用例 | test_string / test_builder / test_conv（main 调用） |
| 用户测试源 | tests/system.c | 用户测试源 | ✅ 1 个用例 | main 内 TEST_START 内联测试（环境变量/DE/CPU） |
| 框架头 | tests/test.h | 框架头/宏 | ❌ | TEST_START/TEST_COMPLETE/ASSERT 宏，非用户用例 |
| 样例 | examples/sili/*.c（7 个） | 样例 | ❌ | array/benchmarking/bit/file/optional/str/thread |
| 样例 | examples/sifig/ini.c + res/mod.ini | 样例 | ❌ | 配置读取样例 |
| 基准 | examples/sili/benchmarking.c | 基准 | ❌ | 性能基准，非断言测试 |
| 测试脚本 | Makefile compile_tests | 构建目标 | ❌ | `for f in tests/*.c; make SRC=$f` 枚举 |

### 双口径台账
- `source_declared_total` = **9**（官方 tag 源码可复制枚举规则：tests/*.c 中 main() 直接调用的 `test_*` 函数 + 含 TEST_START 的 main 内联入口）
- `configured_executable_total` = **9**（当前 OHOS 配置全部实例化：6 个测试可执行文件注册 9 个用例，无互斥分支/条件宏丢弃）
- `executed_passed_total` = **9**，失败 = **0**，未运行/未实例化 = **0**
- 全量通过率：**9/9 (100%)**；当前配置可执行集合通过率：**9/9 (100%)**

### 映射链（源码声明 → 构建目标 → 注册 → 执行日志）
| 用例 | 源码声明 | 构建目标 | 注册 | 实际执行 |
|------|----------|----------|------|----------|
| test_bit | tests/bit.c:81 | build/tests/bit | main 调用 | exit 0，2 个 TEST_COMPLETE 标记 |
| test_overflow | tests/bit.c:119 | build/tests/bit | main 调用 | exit 0 |
| char main 内联 | tests/char.c:7 | build/tests/char | TEST_START | exit 0 |
| general main 内联 | tests/general.c:18 | build/tests/general | TEST_START | exit 0 |
| print main 内联 | tests/print.c:28 | build/tests/print | TEST_START | exit 0 |
| test_string | tests/str.c:42 | build/tests/str | main 调用 | exit 0 |
| test_builder | tests/str.c:365 | build/tests/str | main 调用 | exit 0 |
| test_conv | tests/str.c:596 | build/tests/str | main 调用 | exit 0 |
| system main 内联 | tests/system.c:7 | build/tests/system | TEST_START | exit 0 |

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
1 | GitHub 直连下载超时 | 网络到 github.com 不可达 | 通过 ghfast.top 镜像获取官方 tag v0.3.0 源码，SHA-256=3c50399542e19e0bf2eb1788542277d63978da9e71466a83b512360c938b10dc；conandata.yml 保留官方 URL |
2 | /tmp 写入失败 | 平台 /tmp 限制 | 使用 $HOME/tmp 作为 TMPDIR（环境已配置） |
3 | make 缺 automake | 平台工具链 | 单头库无需 autotools，直接 clang 交叉编译 |

## 源码修改

无补丁（单头库，官方源直接编译通过）。

## 依赖版本

- 无第三方运行时依赖（仅 -lpthread -ldl 系统库）
- 工具链: clang 15.0.4 / llvm-ar / OHOS SDK sysroot 26.0.0.18

## 验证结果

```bash
# 6 个上游测试全部 exit 0；日志见报告
sha256sum build/libsili.a
```

## 消费者验证（test_package，R34/PF3）

- 源文件：`test_package/test.c`（链接 libsili.a，include 公开头 sili.h，调用 si_stringEqual / si_stringFromCStr / si_stringTrim / si_stringUpper / si_stringLower / si_printfLn）
- 编译命令：`clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -O2 -std=c99 -I<src> test_package/test.c <src>/build/libsili.a -lpthread -ldl -o sili-consumer`
- cwd：`archives/s/sili/0.3.0`；运行退出码 0；输出 `test_sili: all consumer checks passed` / `sili consumer test OK`

## 鸿蒙专项测试（test_ohos，独立计数）

- 源文件：`test_ohos/ohos_test.c`（公开 API：si_threadMake/Run/Join、si_timeNowUTC/Local、si_sleep、si_envVarSet/GetData/Unset、si_cpuProcessorCount、si_stringFromCStr/Trim）
- 编译命令：`clang --target=aarch64-linux-ohos --sysroot=$SYSROOT -O2 -std=c99 -I<src> test_ohos/ohos_test.c <src>/build/libsili.a -lpthread -ldl -o sili-ohos-test`
- 运行退出码 0；输出 `ohos_test: all OHOS-specific checks passed (cpus=20, utc=1789826203292373437)`

## R02 返工复验（2026-09-20）

- 修复：test_package/conanfile.py 补回 `from conan import ConanFile`（R01 缺导入致远端 CI NameError）
- 上游测试双口径复验：source_declared_total=9，configured_executable_total=9，executed_passed_total=9（100%），失败 0，未运行 0；映射与 R01 台账一致（6 可执行文件，bit 2/char 1/general 1/print 1/str 3/system 1）
- 鸿蒙专项测试：ohos_test exit 0；消费者测试：test_sili exit 0
- conan create（G2）PASS：日志确认 test_package 编译 test_sili 并 `1/1 Test #1: test_sili Passed 0.02 sec`
- 证据日志：`$HOME/tmp/sili-evidence/r02/`（upstream/ohos/consumer 三份，SHA-256 已记录）

## R03 返工复验（2026-09-21）

- 缺陷确认：test_ohos/ 仅 ohos_test.c（97 行），无 CMakeLists.txt/conanfile.py/MANIFEST.yml 三件套；test_package 与主 conanfile 均未引用 → 死代码，CI 不可复现「鸿蒙专项 1 项、通过率 2/2」
- 修复（方案 A 接线运行）：补齐三件套（CMakeLists.txt：find_package(sili)+add_executable(test_ohos_sili)+target_link_libraries(sili::sili)；conanfile.py：test_type="explicit"+CMakeToolchain/CMakeDeps+test() 用 build_folder 绝对路径运行；MANIFEST.yml 声明入口），`conan test .../test_ohos sili/0.3.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing` 编译运行退出码 0（日志 ohos-wired-r03.log：`all OHOS-specific checks passed (cpus=20)`）
- 实测修复点：conanfile test() 用裸文件名运行报 Error 127（conanrun 环境 sh 无法解析相对路径），改 build_folder 绝对路径后通过
- **PR 测试统计口径校正（以实际接线并执行为准）**：上游 9/9（双口径不变）；鸿蒙专项测试 1 项真实接线执行通过（conan test 入口，不再只计本地直连）；消费者验证 1 项（test_package test_sili 1/1 Passed）；「适配后合计 11 项 +2」保持，但鸿蒙专项计数以 CI 可复现口径为准
- 知识候选：test_ohos 接线规范为已验证可复用新候选（四范围查重无覆盖），建立草稿 knowledge/drafts/DRAFT-sili-0.3.0-test-ohos-explicit-wiring.kv/.md，随本库进入同一 PR（new_draft）

## 注意事项

- 库类型（静态库 libsili.a），无 CLI 产物，不需要 commands.json（R38）
- conandata.yml 源 URL 使用官方 https://github.com/EimaMei/sili
---

**编译结束**: 2026-09-21 00:24
**最终状态**: published
