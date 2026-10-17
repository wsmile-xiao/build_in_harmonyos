# E599 · 同 tarball CMake 子库独立成包：交付面裁剪 + 父注册面 N 台账

> 实例：`libhwy_test/1.3.0`（google/highway 1.3.0 tarball 内的 `hwy_test` 子库）
> 同族：`libgmpxx/6.3.0`（gmpxx ⊂ GMP，rule4 少报 FAIL 后返修）、`libfstconst/1.8.4`（openfst 子库）

## 1. 问题

同一个上游 tarball 里往往定义多个库目标（Highway：`hwy` / `hwy_test` / `hwy_contrib`）。
把它们各自独立成包时有两类确定性坑：

1. **构建面**：上游把子库的安装规则藏在功能开关里。
   Highway 的 `CMakeLists.txt`：

   ```cmake
   if (HWY_ENABLE_TESTS)
   install(TARGETS hwy_test EXPORT hwy_targets
     LIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
     ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
     RUNTIME DESTINATION "${CMAKE_INSTALL_BINDIR}")
   ...
   list(APPEND HWY_PC_FILES libhwy-test.pc)
   endif()  # HWY_ENABLE_TESTS
   ```

   于是「只为交付子库而最小化构建」时 `HWY_ENABLE_TESTS=ON` 是**交付面的必要条件**，
   不是「为凑数字放开上游 build 开关」。反过来，若用 `cmake --build --target` 只编子库，
   `cmake --install` 对 `install(TARGETS)` 里未构建的目标会直接失败：

   ```text
   CMake Error at cmake_install.cmake:62 (file):
     file INSTALL cannot find ".../libhwy_contrib.a": No such file or directory.
   ```

   即**构建目标集合必须 ⊇ install(TARGETS) 全集**（本例 `hwy`、`hwy_test`；contrib 关闭时不含它）。

2. **N 口径**：外部审查 rule4 是脚本化判据「上游实测 N > 声明 N 即不通过」。子包只申报
   自身交付面的用例数，必然小于父 tarball 全量注册面（`libgmpxx` 实测：自身 22 vs 父面
   190/200 → FAIL）。CMake 工程还有第三层：`gtest_discover_tests()` 的 CTest 用例数**不是
   静态可读的**——它把测试二进制的 `--gtest_list_tests` 输出注册为用例，而 Highway 的
   `HWY_EXPORT_AND_TEST_P` 注册点会按**运行时支持目标数**展开（aarch64 实测 ×2）。
   只按 `add_test` 字面量或源文件数申报，会被下一轮更细的口径超过。

## 2. 四步法

### ① 读 install 门控

```sh
grep -n "add_library(hwy_test\|install(TARGETS hwy_test\|HWY_ENABLE_TESTS" CMakeLists.txt
```

### ② 裁剪构建目标，但覆盖 install 全集

```python
cmake.build(target=["hwy", "hwy_test", "test_util_test"])
```

* `hwy`：`install(TARGETS hwy)` 的产物，也是 `hwy_test` 的 PUBLIC 依赖（漏了 install 必失败）；
* `hwy_test`：交付本体的库目标；
* `test_util_test`：交付面内唯一的上游用例（见 ④）；
* 不编 `hwy/tests/` 下其余 83 个测试可执行文件（不在交付面，可省 1–2 小时 C++ 重模板编译）。

### ③ 候选 N 口径全部读数（同单位不得混用）

| # | 口径 | 单位 | 读数（contrib ON / OFF） | 取数方式 |
|---|------|------|--------------------------|----------|
| a | 测试目标（`HWY_TEST_FILES` 框架注册项） | 个目标 | 84 / 67 | 解析 `CMakeLists.txt` |
| b | 测试源文件数 | 个文件 | 84 / 60（`hwy/tests/*.cc`=60） | 文件清单 |
| c | 源码注册宏点（`HWY_EXPORT_AND_TEST_P` + `TEST(`） | 个注册点 | 436（388+48）/ 348（316+32） | 正则计数 |
| d | **用例数（运行时展开）** | 个用例 | 388×T+48 | 编一个交付面内用例，`--gtest_list_tests` 发现数 ÷ 该文件注册点数 = T |
| e | 断言数（`HWY_ASSERT`） | 个断言 | 851 | 正则计数，**另一单位：只披露、不并入 N** |

主 **N = max(a…d)**；本例 T=2 → d = 824 ≥ 同 tarball 兄弟包 `libhwy/1.3.0` 已通过审查的
`ctest -N` 申报值 801（两者同量级、互为下界印证）。

### ④ 执行面 + 自洽台账

* 只跑**交付面内**用例，本例 `hwy/tests/test_util_test.cc`（上游唯一直接测试 `test_util`
  库本身的用例；其余用例的测试对象是 `hwy`/`hwy_contrib` 的 SIMD 算子）；
* `TOTAL = PASS + FAIL + SKIP + NOT_RUN`，逐项写「不在本包交付面的原因 + 替代验证」，
  **不得写 PASS、不得为凑数打开 contrib/examples 开关**；
* 防空套件假通过：先取发现数再取执行数，`executed < discovered` 直接抛错；
* 消费者断言（`test_package`）单列「鸿蒙特有测试」行，**不并入上游 N**。

## 3. 实测读数（libhwy_test/1.3.0，OHOS aarch64，clang 15.0.4）

```text
HMBS_UPSTREAM_TEST_RESULT={"status":"passed","framework":"hwy-standalone-gtest-shim",
  "scope":"hwy/tests/test_util_test.cc","discovered":4,"executed":4,"passed":4,"failed":0}
HMBS_UPSTREAM_TEST_SURFACE={"test_targets_contrib_off":67,"test_targets_contrib_on":84,
  "registration_sites_contrib_off":348,"registration_sites_contrib_on":436,
  "target_multiplier_measured":2.0,"expanded_cases_contrib_off":664.0,
  "expanded_cases_contrib_on":824.0,"in_surface_sites":{"export":2,"test":0}}
HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":15,"passedCount":15}
```

## 4. 复现命令（设备可直接执行）

```sh
# 源码（与兄弟包 archives/l/libhwy/1.3.0 同一 tarball）
URL=https://github.com/google/highway/archive/refs/tags/1.3.0.tar.gz
mkdir -p "$TASK_DIR/upstream" && curl -fsSL -o "$TASK_DIR/upstream/highway-1.3.0.tar.gz" "$URL"
sha256sum "$TASK_DIR/upstream/highway-1.3.0.tar.gz"   # 07b3c1ba2c1096878a85a31a5b9b3757427af963b1141ca904db2f9f4afe0bc2
tar -C "$TASK_DIR/upstream" -xzf "$TASK_DIR/upstream/highway-1.3.0.tar.gz"

# 本包
conan create archives/l/libhwy_test/1.3.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
  -c tools.build:jobs=2 --build=missing
```

## 5. 边界

* 上游用例与交付面完全不同源（纯绑定层等）时：上游表全部 NOT_RUN + 技术原因，消费者断言单列，
  不得并入上游 N；
* `ctest -N` 拿不到静态用例数时（`gtest_discover_tests` 需先构建），用「注册点数 × 实测 T」
  给出可复现读数并把公式写进 PR 正文，同时给出兄弟包/上游 HEAD 注册面作为下界；
* 子库 install 规则被开关包住且该开关会连带大量非交付面目标时，优先按目标裁剪；
  确需改上游 install 规则时以补丁形式进 `conandata.yml` 并登记 `manifest.patches_applied`。
