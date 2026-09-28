# mikelankamp-fpm 1.1.0 适配笔记

## 项目概况

- 上游：`https://github.com/MikeLankamp/fpm`（官方 tag `v1.1.0`，tag tarball；sha256 见 conandata.yml）
- 类型：**header-only** C++ 定点数学库（CMake INTERFACE 目标 `fpm`），仅 3 个头文件
- 许可证：MIT
- 依赖：**0 外部依赖**（测试框架是上游随包内嵌的 `3rdparty/googletest`）
- 包内容：`include/fpm/{fixed,ios,math}.hpp` + `licenses/LICENSE`
- 分支：`feat/mikelankamp-fpm-1.1.0`（分支名去前缀 == 包目录名-版本，精确匹配）

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-09-27
- 编译器: clang/clang++ 15.0.4（OHOS SDK aarch64，profile `ci/conan/profiles/ohos-aarch64`）
- CMake: 4.1.2 / Conan: 2.29.1
- 状态: built

## 编译步骤

```bash
# 1) 本地试跑（验证配方自包含性）
conan create archives/m/mikelankamp-fpm/1.1.0 \
  -pr:h=$HOST_PROFILE -pr:b=$HOST_PROFILE -c tools.build:jobs=2     # rc=0

# 配方 build() 内部（逐字取自 trial-create.log 的 RUN: 行）
cmake -G "Unix Makefiles" -DCMAKE_TOOLCHAIN_FILE=... -DCMAKE_BUILD_TYPE="Release" <src>
cmake --build <build> --target fpm-test -- -j2          # 只建测试目标，绝不建默认目标
<build>/fpm-test                                        # 上游用例全量执行
```

**为什么不建默认目标**：v1.1.0 的 `CMakeLists.txt` **没有任何 option 开关**，且默认 `all`
目标包含两个 `ExternalProject_Add`（`libfixmath`、`cnl`，都要 git clone）以及
`fpm-benchmark` / `fpm-accuracy` 两个工具。按目标构建 `fpm-test` 使 `conan create`
**全程不联网**，也不会把与交付物无关的工具编进包里。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 直接 `cmake --build`（默认目标）会触发 `ExternalProject_Add` 的 git clone | v1.1.0 的 CMakeLists 无 `BUILD_ACCURACY`/`BUILD_BENCHMARK`/`BUILD_TESTS` 等开关（那是 master 后来才加的），benchmark/accuracy 与两个对照库无条件进入 `all` | 配方 `build()` 改为 `cmake.build(target="fpm-test")`，并断言产物存在 |
| 2 | 上游 `cos(0)` 与 `sin(pi/2)` 返回 65535/65536（比 1 低 1 LSB） | 上游 minimax 多项式在 `fixed_16_16` 下的固有精度（1/65536 ≈ 1.53e-5），**与 OHOS 无关** | 不改上游；`test_package` 按 1 LSB 容差断言并在 consumer.cpp 注释写明依据 |
| 3 | 上游测试的「用例数」有四个口径，直接取 grep 行数会被判少报 | `TEST_P`（Combine 参数化）与 `TYPED_TEST` 在运行期大量展开 | 按候选数法取最大值 N=34671，差额 34577 逐项归因（见 test_package/MANIFEST.yml） |

## 源码修改

**无**。本版本 `patches/` 目录不存在：上游源在 OHOS clang 15 下原样编译，测试用例数与
断言数零改动（conandata.yml 无 `patches` 键，配方 `export_conandata_patches`/`apply_conandata_patches`
为零补丁空转）。

## 依赖版本

无编译依赖、无运行依赖（`build.dependencies: []`）。

## 验证结果

### 上游测试（两表的上游行）

取数命令与完整口径见 `test_package/MANIFEST.yml`；原始日志在 `$HOME/tmp/mikelankamp-fpm-1.1.0/`。

```bash
# 设备端原生构建 + 沙箱 HOME 下直跑（独立于 conan 的第二条证据链）
cmake -S <src> -B native-build -DCMAKE_BUILD_TYPE=Release
cmake --build native-build --target fpm-test --parallel 2
HOME=$TASK_DIR/test-home ./native-build/fpm-test
```

原始日志摘录（`fpm-test-direct.log`）：

```
[==========] Running 34671 tests from 19 test suites.
[==========] 34671 tests from 19 test suites ran. (9911 ms total)
[  PASSED  ] 34671 tests.
```

ctest 注册口径（`ctest.log`）：

```
100% tests passed, 0 tests failed out of 94
Total Test time (real) = 210.04 sec
```

`TOTAL = PASS + FAIL + SKIP + NOT_RUN` → `34671 = 34671 + 0 + 0 + 0`（N=34671，N′=34671，通过率 34671/34671 = 100%）。

### conan create（干净轮，配方自包含性）

`conan create` rc=0，日志中：

```
mikelankamp-fpm/1.1.0: RUN: ".../build-release/fpm-test"
[==========] Running 34671 tests from 19 test suites.
[==========] 34671 tests from 19 test suites ran. (8797 ms total)
[  PASSED  ] 34671 tests.
mikelankamp-fpm/1.1.0 (test package): RUN: "./consumer"
mikelankamp-fpm consumer OK: 26 checks passed (arithmetic raw conversion sqrt trig rounding io hash)
```

### test_package（鸿蒙特有测试行）

`consumer.cpp` 只 include 安装后的头文件，**26 项断言**全部通过，覆盖算术精确性、raw
表示往返、跨格式转换、sqrt/sin/cos/atan 对照 double 参考、取整族/fmod、`operator<<`/`>>`
往返与 `std::hash` 行为。该行即 PR 正文「鸿蒙特有测试」行的取数来源（26 ≥ 1）。
