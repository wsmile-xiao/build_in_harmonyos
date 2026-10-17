# NNG 1.10.1 适配笔记

## 编译环境

- 构建系统：CMake
- 编译日期：2026-09-02
- 编译器：clang 15.0.4 / clang++ 15.0.4
- 平台：HarmonyOS PC aarch64
- 状态：built

## 编译步骤

```bash
source .build-context-nng-1.10.1
cd $BUILD_SRC_DIR
mkdir build-ohos-1.10.1 && cd build-ohos-1.10.1
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DNNG_TESTS=ON -DNNG_TOOLS=ON
cmake --build . --parallel 1
cmake --install . --prefix $DEFAULT_PREFIX
ctest -j 4 --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | `init-build` 默认识别为 autotools | 工具未识别该版本的 CMake-only 项目 | 手动按 CMake 流程构建，并在配方中使用 `CMakeToolchain`/`CMake` |
| 2 | `nng.sp.transport.ipc.ipc_test` 超时 | HarmonyOS 工作目录的 Unix domain socket bind 返回 `Permission denied` | 记录为平台限制；TCP/inproc 等核心传输测试正常 |
| 3 | `nng.multistress`、`nng.reqstress` abort | 压力测试受到 IPC 权限限制影响 | 记录为平台限制，不修改上游测试 |

## 源码修改

无源码修改，无补丁。

## 依赖版本

无外部依赖。NNG 1.10.1 的 CMake 构建使用自身源码提供的实现。

## 验证结果

- 编译：通过
- 上游测试：87 项执行，84 项通过，3 项因 HarmonyOS IPC 权限限制失败，通过率 96.55%
- 消费者测试：调用 `nng_pair0_open`、`nng_close` 和 `nng_version`，并执行 `nngcat --version`，通过
- Conan 配方构建将 `NNG_TESTS=OFF`，上游完整测试在独立的源码构建中执行；Conan `test_package` 负责消费者视角 API 验证
- 安装产物：静态 `libnng.a`、头文件、CMake package config 和 `nngcat`

## 注意事项

NNG 不生成 pkg-config 文件，消费者应使用安装目录中的 `nng-config.cmake`。上游 1.11 归档记录了相同的 IPC/压力测试限制，本版本未修改任何上游测试用例。
---

**编译结束**: 2026-09-02 16:07
**最终状态**: built
