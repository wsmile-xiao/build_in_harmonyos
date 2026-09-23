# cm256cc 1.1.2 适配笔记

## 编译环境
- 构建系统: cmake（C++11）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4（OHOS aarch64）
- 状态: built

## 编译步骤

1. `cmake -B build -DCMAKE_BUILD_TYPE=RELEASE`（设备原生探测：Target architecture: ARM64 → 自动 `-DUSE_NEON`，NEON 为 AArch64 强制路径）。
2. `cmake --build build`：生成 libcm256cc.so（SONAME libcm256cc.so.1）与 BUILD_TOOLS=ON 的 cm256_test / cm256_tx / cm256_rx。
3. 上游测试：`LD_LIBRARY_PATH=. ./cm256_test` —— 4 个场景函数（ExampleFileUsage、example2、example3、example4）全部通过，退出码 0。
4. Conan 配方：CMakeToolchain 传 `-DBUILD_TOOLS=ON` 保留上游测试工具；`cmake.install()` 安装 lib/include/pkgconfig/bin。

## 上游测试统计

| 口径 | 数值 |
|------|------|
| 上游自动化场景数（cm256_test main() 中的 4 个 bool 场景函数） | 4 |
| 实际执行 | 4 |
| 通过 | 4 |
| 失败 / 跳过 | 0 / 0 |

说明：cm256_tx / cm256_rx 为需要双进程 + UDP 对端的演示工具，无自动判定逻辑，不计入自动化测试数；test_package 额外复跑了包内安装的 cm256_test（exit 0 断言）并新增真实 API 消费者测试（encode→丢块→decode→逐字节比对，3 项断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者编译报 unknown type 'GF256_ALIGNED' / 'uint8_t' | 安装头 gf256.h 依赖编译期 SIMD 宏选择分支；库以 `-DUSE_NEON` 编译，但 cpp_info 未向消费者传播该宏 | recipe `package_info()` 按架构写入 `cpp_info.defines = ["USE_NEON"]` |
| 2 | L0p 门禁：library 包未声明 shared 选项 | 门禁要求库包显式声明 | 增加 `options={"shared":[True,False]}`，默认 True；上游 CMake 硬编码 SHARED，`validate()` 拒绝 shared=False |
| 3 | curl/8.15.0 锁 zlib/1.3.1 与 openssl/3.5.6.1 需 zlib/1.3.1.1 图冲突 | 制品仓修复版 zlib 与 curl 的精确依赖并存 | `requires("zlib/1.3.1.1", override=True)`（gnustep-gui 先例） |

## 源码修改

无补丁。

## 依赖版本

无外部 conan 依赖（sse2neon.h 随官方源码内嵌）。

## 验证结果

```bash
$ cmake -B build -DCMAKE_BUILD_TYPE=RELEASE && cmake --build build
$ LD_LIBRARY_PATH=. ./build/cm256_test   # 4/4 场景 OK，rc=0
$ conan-verify: G0-G4/L2/L4/L5 全部 PASS，test_package 消费者 3 断言 + cm256_test 通过
```

## 注意事项

- 上游 CMakeLists 内部 VERSION_STRING 仍为 1.1.0（tag v1.1.2 未同步），产物 SONAME 为 libcm256cc.so.1；配方版本与任务/目录一致为 1.1.2。
- ARM64 上 NEON 为强制路径（upstream: "Advanced SIMD is mandatory for AArch64"）；x86 特有的 try_run 探测在该平台不触发。
---

**编译结束**: 2026-09-08 23:55
**最终状态**: built
