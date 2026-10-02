# iguana 1.2.0 适配笔记

## 概览

- 软件：iguana 1.2.0（qicosmos/iguana，universal serialization engine）
- 类型：header-only C++ 库（`package_type = header-library`，Conan 依赖为 0）
- 构建系统：CMake（上游自带 CMakeLists.txt，测试为内置 doctest + ctest）
- 目标平台：HarmonyOS PC (aarch64-linux-ohos)
- 工具链：clang 15.0.4 / libc++ / cmake 4.1.2 / conan 2.29.1 / ninja
- 适配路径：路径 A（基础适配，无补丁）
- 状态: built

## 编译环境

```bash
cd ~/Desktop/build_in_harmonyos
conan create archives/i/iguana/1.2.0 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方内部走 CMake 路径：

1. `source()` 解包上游 `v1.2.0` 官方 tarball（sha256 校验）。
2. `generate()` 注入 `CMAKE_CXX_STANDARD=17`、`BUILD_UNIT_TESTS=ON`、
   `IGUANA_FAST_BENCHMARK_COMPILE=ON`、`LINKLIBC++=ON`（profile 为 libc++），
   并在 OHOS 上按 E092 固定 `CMAKE_SYSTEM_NAME=Linux` /
   `CMAKE_SYSTEM_PROCESSOR=armv8`。
3. `build()` 配置并编译上游全树（库测试 + example + benchmark），随后用
   `ctest --output-on-failure` 跑上游完整测试套件。
4. `package()` 安装 `include/iguana`、`include/frozen`（上游内置的 frozen
   头文件，`field_reflection.hpp` 依赖）与 `licenses/LICENSE`。
5. `test_package/` 以第三方消费者身份 `find_package(iguana)`，
   做 JSON/XML/YAML 双向往返与异常路径断言。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake.test(cli_args=["--output-on-failure"])` 报 `Unknown argument --output-on-failure` | Conan 2 的 `CMake.test()` 把 `cli_args` 透传给 native build tool（`cmake --build <dir> --target test -- --output-on-failure`），`--output-on-failure` 是 ctest 而非 make/ninja 的参数 | 改为 `self.run("ctest --output-on-failure -j<n>", cwd=self.build_folder)`，与仓库既有配方（avro-cpp 等）一致 |
| 2 | 头文件库必须同时安装 `frozen/` | `iguana/field_reflection.hpp` 与 `iguana/ylt/reflection/template_string.hpp` 直接 `#include "frozen/..."`，只装 `iguana/` 会让消费者编译失败 | `package()` 同时安装 `iguana/**` 与 `frozen/**`，保留 include 根目录布局 |
| 3 | 默认构建会连 benchmark 一起编译 | 上游 CMakeLists 无条件 `add_executable(*_benchmark)` | 用上游自带开关 `IGUANA_FAST_BENCHMARK_COMPILE=ON`（-O0）压缩验证构建时间，不影响测试覆盖 |

## 平台差异说明

- 上游 `test/test_some.cpp`、`test_xml.cpp`、`test_yaml.cpp` 等所有用例在 OHOS
  上均**原样通过**，未修改任何上游测试用例（`patches_applied: []`）。
- iguana 不触碰 Linux 专有系统调用或平台私有接口，本包不含平台补丁。
- `iguana/version.hpp` 的 `IGUANA_VERSION` 宏仍停留在 `1.0.5`（上游未随
  release 更新）；包版本按上游 git tag 取 `1.2.0`（R37，首次适配无后缀）。
- 可选宏 `THROW_UNKNOWN_KEY` 由上游 CMake `add_definitions` 注入，只影响
  “未知字段是否抛异常”的语义；消费者若需要同语义可自行定义，库本身默认行为
  不受影响（非法数字等语法错误在默认配置下也会抛 `std::runtime_error`）。

## 验证结果

```text
上游测试（build() 内 ctest）:  100% tests passed, 0 tests failed out of 11
                              Total Test time (real) = 2.77 sec
消费者测试（test_package）:    IGUANA_CONSUMER_CHECKS=17 FAILURES=0
                              IGUANA_CONSUMER_OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| include/iguana/*.hpp, *.h | 公共头文件（含 detail/、ylt/reflection/），共 48 个 |
| include/frozen/** | 上游内置 frozen 头文件（反射容器依赖） |
| licenses/LICENSE | Apache-2.0 |

## 交付与 staging 说明

- `packaging/iguana-1.2.0-ohos-aarch64.tar.gz`：从 Conan 包目录导出的发布产物
  （`include/iguana/**`、`include/frozen/**`、`licenses/LICENSE`）。头文件库无
  `.so`/可执行文件，因此不存在需要 strip / 签名 / RPATH 处理的二进制，也没有
  独立的 debug 产物（无调试符号）。
- `.staging-verified`：staging 校验标记。头文件库的 staging 校验等价于
  “消费者视角能包含并调用安装后的包”，由 `conan create` 的 `test_package`
  阶段完成（`IGUANA_CONSUMER_OK`，17/17 断言通过）。
- 上述 packaging 产物与标记属于本地归档元数据，**不入 PR**（CI JC3 禁止提交
  压缩包）。

## 编译结束

- 目标：在鸿蒙 PC 上完成 iguana 1.2.0 的头文件库适配并跑通上游测试。
- 结论：上游 doctest 套件 11/11 通过、消费者用例 17/17 通过，零补丁、零依赖。

### 对话 #1

- 会话：Codex（Lee-BX / 南京大学 PT）
- 过程：init-build → 手写 CMake 头文件库配方 → `conan create` 验证 →
  `conan-verify`（G0-G4/L2/L4/L5 全通过）→ `finish`（W2/W3 通过）→ 提交 PR。
- 期间修正：`CMake.test(cli_args=...)` 在 Conan 2 下参数错位（改为直接调用 ctest）。
---

**编译结束**: 2026-10-01 20:42
**最终状态**: built
