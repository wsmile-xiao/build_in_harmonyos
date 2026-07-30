# robin-map 1.4.1 适配笔记

> **状态说明**：已使用 OpenHarmony SDK 6.1.0.31 完成 OHOS aarch64
> `conan create`，上游 Boost.Test 132/132 通过，Conan 消费测试 1/1
> 通过，`conan-verify` G0-G4、L2/L4/L5 全部通过。当前状态为
> `built`；上传制品仓后再改为 `published`。

## 编译环境

- 构建系统: cmake
- 编译日期: 2026-07-18
- SDK: OpenHarmony 6.1.0.31
- 编译器: OHOS Clang 15.0.4
- 构建宿主: Linux x86_64 Docker
- 执行方式: OHOS aarch64 静态测试程序通过 qemu-user 执行

## 编译步骤

1. 下载官方源码：`v1.4.1.tar.gz`（SHA256 与 Homebrew 一致）
2. CMake 配置（Conan `CMakeToolchain`）：
   - `TSL_ROBIN_MAP_ENABLE_INSTALL=ON`
   - OHOS 上按需将 `CMAKE_SYSTEM_NAME` 映射为 `Linux`（E092 类问题）
3. `cmake --build` + `cmake --install`：安装 `include/tsl/` 与 `share/cmake/tsl-robin-map/`
4. 使用 Boost 1.86.0 头文件编译上游完整 Boost.Test 套件
5. 静态链接 OHOS aarch64 测试程序并通过 qemu-user 执行
6. 执行 Conan `test_package`，验证下游 `find_package`、编译、链接及运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 归档仅有 manifest/notes，无 Conan 配方 | 历史 partial 记录 | 按 ARCHIVE-SPEC v3.0 补齐 conanfile/conandata/test_package |
| 2 | 下游查找名与 Conan 名不一致 | 上游 CMake 项目名为 `tsl-robin-map` | `cmake_find_mode=none` + 安装上游 Config；test 使用 `find_package(tsl-robin-map)` |
| 3 | 动态测试程序在 QEMU 中缺少 OHOS rootfs | 动态解释器为 `/lib/ld-musl-aarch64.so.1` | 测试程序使用 `-static` 链接 |
| 4 | Boost 头文件触发 `-Wold-style-cast -Werror` | 上游将严格警告应用到第三方头文件 | 使用 `-isystem` 引入 Boost 头文件 |
| 5 | Boost 引用 `pthread_setcancelstate` | OHOS pthread 不提供线程取消 API | 单线程测试定义 `BOOST_DISABLE_THREADS` |

## 源码修改

应用 `0001-use-header-only-boost-test.patch`：

- 将 Boost.Test 切换为 header-only 入口；
- 移除对预编译 `Boost::unit_test_framework` 的链接；
- 不修改任何测试逻辑和断言。

## 依赖版本

- 运行时依赖：无（纯头文件库）
- 测试依赖：Boost 1.86.0 源码头文件（配方直接下载并校验 SHA256，不依赖 Conan 制品仓）
- 构建工具：CMake 3.28.2、OHOS Clang 15.0.4
- 测试执行工具：qemu-user

## 验证结果

验证命令：

```bash
cd archives/r/robin-map/1.4.1
conan create . -pr:h=ohos-aarch64-6.1 -pr:b=default --build=missing
python3 scripts/ohc-run.py conan-verify robin-map 1.4.1 \
  --profile ohos-aarch64-6.1
```

结果：

- 上游 Boost.Test：132/132 通过，`*** No errors detected`
- Conan `test_package`：1/1 通过，输出 `1: one`、`2: two`
- `conan-verify`：G0-G4、L2/L4/L5 全部 PASS

## 注意事项

- 本包为 `nanobind` 方案 A 前置依赖：须先发布再适配 nanobind（R36）
- 库类型，不要添加 `commands.json`（R38）
- QEMU 验证覆盖 CPU 指令、静态 ABI 和功能行为；不等同于真机系统集成验证

---

**编译结束**: 2026-07-18 14:36
**最终状态**: built（OHOS aarch64 编译、上游测试和 Conan 消费测试通过）
