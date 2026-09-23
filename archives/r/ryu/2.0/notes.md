# ryu 2.0 适配笔记

## 编译环境
- 构建系统: cmake（上游为 Bazel，配方按本仓 alac 0.0.7 先例自带最小 CMakeLists.txt）
- 编译日期: 2026-09-12
- 编译器: clang 15.0.4（OHOS SDK，aarch64-linux-ohos）
- 状态: built
- Conan: OHOS 适配版 2.29.1，profile ohos-aarch64
- 任务: 平台任务 7315；worktree `~/qzy/GLM-14-ryu-2.0`；分支 `feat/ryu-2.0`

## 上游与源码
- 上游: https://github.com/ulfjack/ryu tag v2.0
- URL: https://github.com/ulfjack/ryu/archive/refs/tags/v2.0.tar.gz
- SHA256: a362882dca2b692810aa1508b4fa16572590babd3db394442fb77c89bc1ce9b7
  （设备上两次独立下载逐字节比对一致；tarball 8,281,445 字节，顶层目录 ryu-2.0/）
- 许可: 双许可 Apache-2.0 OR Boost（BSL-1.0），两份 LICENSE 文件均随包安装
- 语言: C（C 实现在 ryu/ 目录；src/ 为 Java 实现，与本次适配无关）
- 上游构建: Bazel（ryu/BUILD、ryu/tests/BUILD、ryu/benchmark/BUILD），无 configure/CMake/Makefile

## 包范围决策（重要）
上游 Bazel 定义了多个独立 cc_library：
- `//ryu`（默认目标）: f2s.c + d2s.c，公共头 ryu.h —— **本包内容**
- `//ryu:generic_128`: generic_128.c，公共头 ryu_generic_128.h —— 不入包，理由见下
- `//ryu:ryu_printf`: d2fixed.c，公共头 ryu2.h —— 不入包（上游即独立组件，aarch64 实测 24/24 可用，后续如需可另立任务）
- `//ryu:d2s_intrinsics`: 纯头文件（static inline）

generic_128 不入包的硬理由：其 `long_double_to_fd128` 在 aarch64 上静默出错（见下节），
入包等于发布一个在该 ABI 上结果错误的公开 API。generic_128 的 float/double/generic
函数本身正常（14/15 相关用例过），失败面仅限 long double 封装。

## 上游测试四维账本（§10.1 口径）
- **N_static = 62**：按 ryu/tests/BUILD 的 6 个 cc_test 目标，对源码 `TEST(` 宏逐个统计：
  d2s_test.cc 9、d2s_table_test.cc 4、f2s_test.cc 9、d2fixed_test.cc（bazel 目标名 ryu_printf_test）24、
  generic_128_test.cc 15、d2s_intrinsics_test.cc 1。
- **N_registered = 6**（Bazel cc_test 目标）/ gtest 运行层注册 62 个原子用例。
- **N_executed = 62**：设备上以 vendored gtest（third_party/gtest 单文件 amalgamation：
  gtest-all.cc + gtest_main.cc）编译 6 个测试可执行文件，全部真实运行，无目标级缺失。
- **结果分类**：61 通过 / 1 失败 / 0 跳过。
  - 失败：`Generic128Test.long_double_to_fd128`（gtest 断言 `-0.0L` → 期望 `"-0E0"`，实际 `"0E0"`；
    ASSERT 失败即中止，该用例后续断言未执行）。
  - 无条件跳过项：0。无因资源缺失、条件编译未注册而未执行的用例。
- **N_consumer = 1**（test_package/test_ryu，25 项显式断言）。

## 失败用例根因分析（含探针证据）
`generic_128.c` 对 long double 硬编码 x86 80-bit 扩展精度布局：

```c
#define LONG_DOUBLE_MANTISSA_BITS 64   /* x86 80-bit 扩展精度 */
#define LONG_DOUBLE_EXPONENT_BITS 15
uint128_t bits = 0;
memcpy(&bits, &d, sizeof(long double));
return generic_binary_to_decimal(bits, 64, 15, true);   /* 符号位 = bit79 */
```

aarch64 OHOS（与 aarch64 Linux 相同）的 long double 是 IEEE binary128（quad）：
设备探针（~/tmp/uc2/ryu-2.0/ldprobe.c）实测：
- `sizeof(long double) == 16`
- `-0.0L` 的符号位在 bit127（quad ABI）= 1，而上游读取的 bit79 = 0 → 符号丢失，输出 `"0E0"`
- `1.0L` 的 quad 指数字段（bits[112..126]）= 16383（标准 binary128 偏置）

结论：**上游可移植性缺陷，非 OHOS 适配引入**——同一代码在 aarch64 Linux 上同样命中；
与 musl/libc 无关（纯位布局问题）。不修改上游测试、不为通过率静默删用例，
如实按 61/62（执行项）与 62 静态全量口径上报。包范围决策（generic_128 不入包）同时
将该缺陷与发布产物隔离。

## 编译步骤
1. W0：`ci/scripts/preflight_check.sh ryu/2.0` → 通过（无依赖声明）。
2. W0b：`recipe-search ryu` → 无相似配方（语料 4433 条），走模板；CI 能力矩阵 Bazel ❌
   （设备与 CI 均无 bazel），故按 alac 0.0.7 先例自带 CMakeLists.txt。
3. 上游测试先行（探索性验证，`~/tmp/uc2/ryu-2.0/upstream-tests.sh`）：
   vendored gtest + 6 个上游测试用 clang 15 直接编译运行（见上节结果）。
4. 配方：conanfile.py（CMake helper + CMakeToolchain，R32 `os in ("Linux","OHOS")`，
   R33 不裸用 shell 编译器变量）+ 自带 CMakeLists.txt（仅编译 d2s.c/f2s.c）。
5. W3：`conan create` 全量验证（配方自包含：下载→解压→CMake→test_package 消费者测试运行）。

## 源码修改
无补丁（patches_applied: []）。无平台宏注入（PF5 合规）。上游源码零修改。

## 依赖版本
无外部依赖（含测试：上游自带 vendored gtest，未引入制品仓 gtest 依赖）。

## 验证结果
```bash
# 上游测试（设备实跑，clang 15 + vendored gtest）
d2s_test            9/9  PASSED
d2s_table_test      4/4  PASSED
f2s_test            9/9  PASSED
d2fixed_test       24/24 PASSED
generic_128_test   14/15（1 失败：long_double_to_fd128，根因见上）
d2s_intrinsics_test 1/1  PASSED
合计                61/62（执行项），静态全量 62
# 消费者测试
test_ryu            25/25 断言通过，退出码 0
```

## 已知限制
1. 包不包含上游可选组件 generic_128（其 long double 封装在 aarch64 上有上游布局缺陷）
   与 ryu_printf/d2fixed（上游独立组件；aarch64 实测可用，如需可另立任务扩展包）。
2. 上游测试 62 项中 1 项（generic_128 long double）在本平台失败，根因见上，属上游缺陷。
3. 上游测试的运行不在 conanfile build() 内（upstream_test_in_build: false）——
   上游测试依赖 Bazel/vendored gtest，CI 只读 4 类文件不参与；运行证据为设备侧
   探索性验证日志（~/tmp/uc2/ryu-2.0/upstream-tests.log），不入归档树。

## 路径 B 判断素材
- 候选知识主题：①「上游以 Bazel 构建（无 CMake/autotools 入口）时的 CMake 化模式：
  export_sources 自带最小 CMakeLists + 按上游默认 cc_library 目标圈定包范围」；
  ②「third_party/gtest 单文件 amalgamation 使 gtest 系上游测试可零依赖真实运行」；
  ③「long double 位布局可移植性：x86 80-bit 硬编码在 aarch64 quad ABI 下的失败签名
  （-0.0 符号丢失）+ 探针定位法」。
- 查重与门槛核对结论见主理收口时的知识库查重；本包按纯路径 A 交付，
  主题 ③ 若查重未命中可考虑随本 PR 或另立知识 PR 沉淀。
---

**编译结束**: 2026-09-12 09:17
**最终状态**: built
