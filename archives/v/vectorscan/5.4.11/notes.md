# vectorscan 5.4.11 适配笔记

## 编译环境

- 构建系统: CMake
- 编译日期: 2026-09-10
- 目标平台: HarmonyOS aarch64
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 构建工具: GNU Make 4.4.1
- Conan: 2.29.1
- 状态: built

## 编译步骤

1. 使用 `ci/conan/profiles/ohos-aarch64` 安装并复用 `boost/1.84.0`。
2. 从官方 vectorscan 5.4.11 归档（SHA-256 为
   `905f76ad1fa9e4ae0eb28232cac98afdb96c479666202c5a4c27871fb30a2711`）准备源码，应用
   `patches/5.4.11-0001-fix-cmake.patch`。
3. 以 Release、静态库、`CMP0167=OLD`、关闭 SVE/SVE2 和默认关闭上游单元测试的配置构建；
   Conan 配方在 HarmonyOS 上使用 `cmake --build -- -j1`。
4. 构建期工具 Ragel 6.10 从固定 SHA-256 的上游归档构建到任务私有前缀，递归构建和安装使用
   `make SHELL=/bin/sh`。
5. 在默认 `with_chimera=False` 配置下独立打开 `BUILD_UNIT_TESTS=ON` 构建上游测试目标，运行
   `unit-hyperscan` 和 `unit-internal`，再安装 `libhs.a`、`libhs_runtime.a` 及公开头文件；
   条件目标 `unit-chimera` 需要另行启用 `with_chimera=True`，本轮不将其记为已通过。
6. 通过 Conan `create` 执行干净 W3 构建和 `test_package`，并用 C API 消费者完成静态链接、
   分配 scratch、扫描和回调检查。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 4.x 弃用旧式 FindBoost | CMP0167 新策略默认启用 | 配置 `CMAKE_POLICY_DEFAULT_CMP0167=OLD` |
| 2 | OHOS 头文件中使用 `pthread_setcancelstate` | HarmonyOS 平台不提供该取消接口 | 在 Boost 线程休眠实现中增加 `BOOST_SP_NO_PTHREAD_SETCANCELSTATE` 兼容宏 |
| 3 | 打包构建不应默认编译上游测试，但测试目标需可复现 | 上游测试目录与库构建耦合 | 增加 `BUILD_UNIT_TESTS` 选项，库构建默认关闭，独立测试阶段显式打开 |
| 4 | HMDFS 上并行 Make 出现 jobserver FIFO 权限错误和头文件竞态 | 设备文件系统不支持 GNU Make 并行 jobserver FIFO | OHOS Conan 构建显式串行化为 `-j1`，并在采信轮临时使用 `tools.build:jobs=1` |
| 5 | Ragel 引导构建在 Bash 下出现 `getcwd`/`.deps` 错误 | 设备文件系统与 Bash 的工作目录处理不兼容 | Ragel 的递归 `make` 和安装命令显式使用 `SHELL=/bin/sh` |
| 6 | Conan 组件依赖需要精确闭合 | Boost 1.84 的 Conan 组件键为 `boost_headers`，其 CMake target 名为 `Boost::headers` | 将 `hs` 组件依赖声明为 `boost::boost_headers`，保留 CMake target 名与 Conan 组件键的区分 |
| 7 | C API 消费者用 C 链接器链接静态 C++ 实现时缺少 C++ 运行时 | `libhs.a` 包含 C++ 实现，经典 CMakeDeps 不自动传播 C++ 链接语言和 OHOS libc++ | package_info 声明 `hs.languages = ["C++"]`，消费者 target 使用 C++ linker，OHOS 的 `hs` 组件补充 `c++` 系统库 |

## 源码修改

- `patches/5.4.11-0001-fix-cmake.patch`：设置 Boost 的 OHOS 兼容宏；将 Boost 依赖接入 Conan 组件；
  增加 `BUILD_UNIT_TESTS` 开关以区分库构建和上游测试构建。
- `conanfile.py`：使用 `boost::boost_headers`；OHOS 构建串行化；声明 C++ 链接语言并暴露 OHOS libc++ 系统库。
- `test_package/CMakeLists.txt`：启用 C/C++ 双语言并将消费者目标的链接语言固定为 C++，覆盖 C API 的实际静态链接场景。

## 依赖版本

- boost/1.84.0
- pcre/8.45（仅 `with_chimera=True` 时启用）
- Ragel 6.10（源码构建期工具）
- CMake 4.x
- Clang 15.0.4
- GNU Make 4.4.1

## 验证结果

### 默认配置上游测试（with_chimera=False）

```text
unit-hyperscan: 2978/2978 passed（33 个测试类）
unit-internal: 14040/14040 passed（73 个测试类）
合计: 17018/17018 passed，未出现 SKIPPED 汇总行
```

### 可选 Chimera 测试（本轮未运行）

上游 `unit/CMakeLists.txt` 在 `BUILD_CHIMERA=ON` 时额外构建 `unit-chimera`。按源码注册和
参数展开，该目标包含 50 个直接 `TEST`、32 个 `HybridCompile` 参数测试，以及
`6 × 14 × 2 = 168` 个 `HybridScan` 参数测试，共 250 个个体测试。本轮默认配置关闭
`with_chimera`，因此这 250 个测试记为未运行，不计入通过数；上游可选测试总量为
`17018 + 250 = 17268`。

### Conan/W3 与消费者

```text
Conan clean create: PASS
test_package: 1 个消费者场景，5/5 断言通过
G2: PASS
G3: PASS
G4/L2/L4/L5: 完成手工补测；静态包无 ELF，消费者为 PIE、NX、full RELRO
```

Conan 产物包含 `lib/libhs.a`、`lib/libhs_runtime.a`、5 个 `include/hs/*.h` 头文件和
`licenses/LICENSE`；没有动态库或可执行文件。L5 以本轮 10 个文件的 SHA-256 清单建立首个基线，
当前没有历史基线可供漂移比较。

## 注意事项

- 本适配状态为 `built`，不是 `published`；本轮没有 release/debug tar.gz 或 `packaging/` 归档产物。
- 设备 HMDFS 上不要恢复并行 Make；OHOS 配方的 `-j1` 是为设备文件系统约束保留的构建行为。
- `test_package` 表面使用 C API，但静态库实现包含 C++；下游使用经典 CMakeDeps 时必须保留 C++
  链接语言和 OHOS libc++ 传递信息。
- `conan-verify` 的 G4/L2/L4/L5 在当前工具版本中无法可靠解析 package/cache 路径，结论以
  `reports/conan-verify-supplement.md` 的人工补测记录为准。
