# DRAFT-sili-0.3.0-test-ohos-explicit-wiring：鸿蒙专项测试 test_ohos/ 显式接线规范

> Contributor: pc4-4 | Status: Draft | Updated: 2026-09-21
> Source: sili 0.3.0 R03（分析端验收返工：test_ohos 死代码修复）

## 问题（现象）

- 鸿蒙专项测试目录 `test_ohos/` 若**只有测试源文件**（如 `ohos_test.c`）而没有
  CMakeLists.txt、conanfile.py、MANIFEST.yml 三件套，conan create / CI 测试流程只会
  配置、编译、运行 `test_package` 的用例；`test_ohos` 源文件永远不会被编译或执行，
  成为**死代码**。
- 适配报告若把"本地直连编译运行"的专项测试计为通过率分子，而 CI 口径下该入口
  零覆盖（线程/时间/环境变量/CPU 等鸿蒙路径实际未在交付流程验证），即为**计数虚报**。

## 根因

- 同仓存在自动 glob 编译机制的假设不成立：`irsim/libsigc-2/msdfgen/libmodplug` 的
  `test_ohos/` 均三件齐备，且需显式 `conan test <路径> <ref>` 触发，不存在自动发现。
- 实测案例（sili 0.3.0）：R01/R02 以本地直连方式运行 `ohos_test.c` 并宣称
  「鸿蒙特有测试 1 项、通过率 2/2 (100%)」，R03 分析端验收发现 `test_ohos/` 只有
  `ohos_test.c` 一个文件（97 行），`test_package/conanfile.py` 与 CMakeLists.txt 均未引用，
  主 conanfile.py 无 test() 方法接线 → 死代码，CI 不可复现。

## 可复用方案

### 1. 补全三件套（显式接线）

- `CMakeLists.txt`：
  ```cmake
  cmake_minimum_required(VERSION 3.15)
  project(test_ohos_<lib> LANGUAGES C)
  set(CMAKE_C_STANDARD 99)
  set(CMAKE_C_STANDARD_REQUIRED ON)
  find_package(<lib> REQUIRED)
  add_executable(test_ohos_<lib> <源>.c)
  target_link_libraries(test_ohos_<lib> PRIVATE <lib>::<lib>)
  ```
- `conanfile.py`：`settings = "os","arch","compiler","build_type"`、`test_type = "explicit"`、
  `generators = "CMakeToolchain","CMakeDeps"`、`requirements()` 注入 tested_reference、
  `build()` 用 CMake 配置+构建、`test()` 校验 `os==OHOS` 后用 **build_folder 绝对路径**运行。
- `MANIFEST.yml`：声明 `test_ohos_tests` 入口、`command` 为 `conan test` 调用、count/assertion_count。

### 2. 真实运行

```bash
conan test archives/<首字母>/<库名>/<版本>/test_ohos <库名>/<版本> \
  -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```
必须真实编译并运行，退出码 0 且日志含专项断言输出；记录命令、cwd、退出码与绝对日志。

### 3. 计数口径

- PR「适配后测试统计」只按**实际接线并执行**的用例数填写；未接线前不得将专项测试计为通过。
- `test()` 运行可执行文件必须用 `build_folder` 绝对路径：conanrun 环境下 `sh` 无法用裸
  文件名解析，相对路径会报 `Error 127 / inaccessible or not found`（sili R03 实测修复点）。

## 验证

sili 0.3.0 R03 接线后：`conan test .../test_ohos sili/0.3.0 -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=missing`
退出码 0，日志输出 `ohos_test: all OHOS-specific checks passed (cpus=20, utc=...)` + `sili OHOS test OK`。

## 适用边界 / 反例

- 适用于所有交付鸿蒙专项测试（test_ohos/ 或等价目录）的适配库；纯库无专项测试时不适用。
- 反例：如果专项测试确实无法在 CI 环境接线（真实外部硬阻塞），则按方案 B 从 PR 计数中移除该
  项并保留不可运行证据与恢复条件，不得计为通过。