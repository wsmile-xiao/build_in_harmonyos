# open-dis-cpp 1.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-29
- 编译器: clang 15.0.4 / clang++（`/data/service/hnp/bin/`），libc++，conan 2.29.1（OHOS 适配版）
- 平台: HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 编译步骤

上游是纯 CMake 工程（`CMakeLists.txt` 三个开关：`BUILD_SHARED_LIBS` / `BUILD_EXAMPLES` / `BUILD_TESTS`），
配方只用 `CMakeToolchain` 注入 cache 变量，**上游源码零改动**：

1. 设备原生探索构建（定性用）：
   ```bash
   CC=/data/service/hnp/bin/clang CXX=/data/service/hnp/bin/clang++ \
     cmake -S . -B build-ohos -DCMAKE_BUILD_TYPE=Release \
           -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5
   cmake --build build-ohos -j4
   ctest --test-dir build-ohos --output-on-failure     # 1/1 入口，内含 8 个 TEST_CASE 全过
   cmake --install build-ohos --prefix "$TEST_PREFIX"  # 337 文件：2 .so + 331 .h + 4 .cmake + LICENSE 未装（配方补装）
   ```
2. Conan 配方构建（CI 同源）：
   ```bash
   conan create archives/o/open-dis-cpp/1.0.1 \
     -pr:h=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 \
     -pr:b=$TARGET_REPO/ci/conan/profiles/ohos-aarch64 --build=missing
   ```
   `generate()` 注入：`BUILD_SHARED_LIBS=ON`（上游默认，非系统同名库按 §7 走动态）、`BUILD_TESTS=ON`、
   `BUILD_EXAMPLES=OFF`、`CMAKE_POLICY_VERSION_MINIMUM=3.5`；`build()` 内 `cmake.test()` 跑上游测试；
   `package()` `cmake.install()` + 补装 `LICENSE` 到 `licenses/`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 直接失败：`Compatibility with CMake < 3.5 has been removed ... add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to try configuring anyway`（无该变量时 rc=1 逐字复现） | 上游 `cmake_minimum_required(VERSION 3.2)`，设备与 CI 同为 CMake 4.1.2，已移除 <3.5 兼容 | 配方 `generate()` 注入 `CMAKE_POLICY_VERSION_MINIMUM=3.5`（不改上游文件，不打补丁） |
| 2 | 构建树里 `test/UnitTestSuite` 起不来：`Error loading shared library ../libOpenDIS6.so` | ①`add_library` 未设 `VERSION/SOVERSION` → 无 SONAME；②CMake 对未知平台（uname=HarmonyOS → `Platform/HarmonyOS` 缺失）不写 RPATH；③链接行用相对路径 `../libOpenDIS6.so`（`readelf -d` 实证 NEEDED），musl 加载器对含 `/` 的名字按**进程工作目录**解析 | 不改源码：CTest 执行 `add_test(NAME ...)` 默认以测试所在二进制目录（`build/test/`）为工作目录，`../libOpenDIS6.so` 恰好解析成功（`ctest` 1/1 实测）；消费者侧由 CMakeDeps 传**绝对路径**给链接器，NEEDED 为绝对路径/`libOpenDIS6.so`，conanrun 下实测可执行 |
| 3 | 手写消费者回环 `copy == src` 恒为 false，字段级断言却全过 | `Pdu::_length` 只在 `unmarshal()` 里回填；内存构造的 PDU `_length=0`，而 `marshal()` 写的是 `getLength()`（= `getMarshalledSize()` 计算值）→ `Pdu::operator==` 比 `_length` 必不等 | 采用上游自己的惯用法（`test/PduUtils.cpp InitPDU` 逐个 PDU 都调 `pdu.setLength(pdu.getMarshalledSize())`）：回环前 `setLength(getMarshalledSize())`；已在测试源码注释说明 |
| 4 | `DataStream::empty()` 语义与直觉相反 | `empty()` 只看"是否从未写入"（上游 `DataStreamTests.cpp` 里读完全部数据后仍断言 `!empty()`）；读写位要用 `GetReadPos()`/`GetWritePos()` | 「已读尽」断言改为 `GetReadPos() == GetWritePos()` |
| 5 | DIS6 / DIS7 不能同时链接进一个程序 | 两库类名大量重叠（92 个同名头文件）且同处 `namespace DIS`，内存布局不同；`dis6/utils/Endian.h` 与 `dis7/utils/Endian.h` 甚至共用同一个 include guard `_dcl_dis_endian_h_` | `package_info()` 拆成 `dis6` / `dis7` 两个 conan component（`open-dis-cpp::dis6` / `open-dis-cpp::dis7`），test_package 三个消费者按协议版本分别链接；README/notes 记录边界 |
| 6 | 测试源码里扫 `/proc/self/exe` 找 `libOpenDIS6.so` 恒 miss（而 `grep -abo` 在同一文件能命中） | `strstr()` 是 C 字符串扫描，ELF 头第 8 字节就是 `\0`，扫到即停 | 改 `memcmp` 逐字节扫描 + 保留 `nlen-1` 跨块尾部；`/proc/self/maps` 同一函数复用 |
| 7 | configure 时刷 `System is unknown to cmake, create: Platform/HarmonyOS` | 设备 `uname` 为 HarmonyOS，CMake 内置平台表没有该系统名 | 无害告警（只影响平台模块选择，`try_compile` 均 Success，configure/build/test/install 全绿），不处理、不写 PASS 以外的结论 |
| 8 | `finish` 内嵌的 G0 干净构建验证报 `cmake configure 失败 (exit 1)`（非阻塞告警，但会留在收尾日志里） | G0 的 CMake 入口按 manifest 的 **`build_options`**（单行键）取参，只读 `configure_options`（YAML 列表）的是 autotools 路；缺该键时 G0 不带 `CMAKE_POLICY_VERSION_MINIMUM=3.5` → 撞上问题 #1 同一根因 | manifest `build:` 段补单行 `build_options: "-DBUILD_SHARED_LIBS=ON -DBUILD_TESTS=ON -DBUILD_EXAMPLES=OFF -DCMAKE_POLICY_VERSION_MINIMUM=3.5"`，两个键语义相同、分别服务两条入口（实测复跑 G0 `cmake configure 成功`，读数见 `reports/g0-clean-verify.md`） |

## 源码修改

无。**0 补丁**（`patches: []`），全部适配经配方 `generate()` 的 CMake 变量完成；`PF5` 平台宏闸、
`PF7` 源 URL 闸、`H4` 注释面扫描均无输入。

## 依赖版本

- 编译依赖：**无**（W0 双源复核：CMake `find_package` 面 + 源码 `#include` 面均无第三方库）
- 可选依赖：SDL2 / SDL2_net（仅 `examples/`，`BUILD_EXAMPLES=OFF` 显式关闭）
- 工具链：clang/clang++ 15.0.4、CMake 4.1.2、GNU Make 4.4.1、conan 2.29.1

## 验证结果

```bash
# A. 设备原生探索构建（2026-09-29）
$ ctest --test-dir build-ohos --output-on-failure
100% tests passed, 0 tests failed out of 1
$ ./build-ohos/test/UnitTestSuite
All tests passed (157 assertions in 8 test cases)

# B. 打包库 + 消费者实跑（staging 安装树 $TEST_PREFIX，337 文件）
$ clang++ -std=c++11 -Wall -Wextra test_package/test_*.cpp -I$TEST_PREFIX/include -L$TEST_PREFIX/lib -lOpenDIS6|7
# 零告警；三消费者实跑：
test_dis6_roundtrip : RESULT=ALL PASSED checks=16 failed=0
test_dis7_roundtrip : RESULT=ALL PASSED checks=15 failed=0
test_ohos_runtime   : RESULT=ALL PASSED checks=9 failed=0 skipped=0
#   （含 DT_NEEDED 引用核对 + /proc/self/maps 运行时映射核对 + 网络序落盘 01 02 03 04）

# C. conan create（CI 同源，第 1 轮，2026-09-29，日志 $HOME/tmp/open-dis-cpp-1.0.1/logs/conan-create-1.log）
$ conan create archives/o/open-dis-cpp/1.0.1 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build=missing
CREATE_RC=0
open-dis-cpp/1.0.1: package(): Packaged 2 '.so' files: libOpenDIS6.so, libOpenDIS7.so
open-dis-cpp/1.0.1: package(): Packaged 331 '.h' files / 4 '.cmake' files / 1 file: LICENSE
1/1 Test #1: UnitTestSuite ....... Passed      # 上游测试（cmake.test()）
3/3 Test #?（test_package） ....... Passed      # 消费者 3/3

# D. 干净缓存采信轮（conan_verify_round.sh，2026-09-29，日志 $HOME/tmp/open-dis-cpp-1.0.1/logs/verify-round-1.log）
$ sh $WORKSPACE_ROOT/tools/conan_verify_round.sh open-dis-cpp 1.0.1 \
    --repo "$TARGET_REPO" --task-dir "$TASK_DIR"
ROUND_RC=0            # 0=干净轮 + 证据已留存 + finish 前快照完成
干净轮判读: clean（构建标志计数 run_make=7 calling_build=2 apply_patch=0；缓存轮无这些行）
Verdict: PASS（实跑 G4/L2/L4/L5 = 3/4，跳过 1/4：L2——纯库包无 bin/，等效人工补测见
         reports/conan-verify-supplement.md）
证据副本: conan-create.log 82210 B（sha256 60eb0c37…）、conan-verify-report.md 1761 B（b7fe91aa…）
finish（四步收尾序第 1 步）: FINISH_RC=0 → status=built → finish_restore --apply → capture_evidence --verify
```

## 注意事项

- 上游测试用例数 N=8（`TEST_CASE` 宏 8 == `--list-tests` 注册 8 == Catch2 汇总 8；assertion 口径 157，
  两口径不混用）；test_package 消费者 3 用例 / 40 断言**不进上游分母**。
- `test_package/build/`、`build*/` 属 `.gitignore` 的 `build/` 规则，不入提交面。
- 本包无 `bin/`（纯库），按 R38 **不建** `commands.json`；`packaging/` 为 ARCHIVE-SPEC v3.0 废弃项，不创建。
---

**编译结束**: 2026-09-29 16:14
**最终状态**: built
