# aws-c-auth 0.10.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 使用 Conan 配方 (`conanfile.py`) 进行交叉编译
2. 通过 `CMAKE_PREFIX_PATH` 传递 aws-c-common、aws-c-cal、aws-c-io、aws-c-http、aws-c-sdkutils、aws-lc、aws-c-compression 的包路径，确保 `find_package` 能找到原始 CMake 配置文件
3. `conan create` 构建并发布到本地缓存

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `Threads::Threads` 目标缺失 | CMake 未识别 OHOS 为 UNIX，导致 `FindThreads` 模块未自动加载 | 在 CMakeLists.txt 中 `find_package(aws-c-common REQUIRED)` 之后插入 `find_package(Threads REQUIRED)` |
| 2 | `aws_tls_handler_protocol` 符号未定义 | aws-c-io 以 `BYO_CRYPTO=ON` 编译时该函数未导出，但 aws-c-http (shared, from remote) 引用它 | test_package 中提供 `stub.c` 返回空 `aws_byte_buf`，通过 `--export-dynamic` 导出符号供运行时解析 |

## 源码修改

- **0001-CMakeLists.txt.patch**: 在 `find_package(aws-c-common REQUIRED)` 之后插入 `find_package(Threads REQUIRED)`

## 依赖版本

- aws-c-common/0.14.3
- aws-c-cal/0.9.15
- aws-c-io/0.27.5
- aws-c-http/0.11.0
- aws-c-sdkutils/0.2.7
- aws-lc/5.4.0
- aws-c-compression/0.3.2 (transitive)

## 验证结果

```bash
conan create . --build=missing  # PASS
conan test test_package aws-c-auth/0.10.4  # 1/1 PASS
conan-verify  # ALL PASS (G0-G4 + L2/L4/L5)
```

## 注意事项

- 使用 `CMAKE_PREFIX_PATH` 而非 `CMakeDeps`，因为 aws-c-common 的 CMake 配置创建 `AWS::` 前缀目标并添加自定义 CMake 模块路径，`CMakeDeps` 会替换为不同目标名导致构建失败
- 使用 `shared=False`（静态库），与仓库内其他 aws-c-* 包保持一致。HarmonyOS 动态链接器不支持 `LD_LIBRARY_PATH`/`DT_RPATH`/`DT_RUNPATH`，test_package 无法在运行时定位共享库
- stub.c 中的 `aws_byte_buf_stub` 结构体使用 `size_t` 类型与 `struct aws_byte_buf` 保持 ABI 一致。stub 仍需保留因为依赖包（aws-c-http 等）从远程下载的是 shared 版本

---

**编译结束**: 2026-07-27 15:11
**最终状态**: built

## 最终状态

COMPLETED — aws-c-auth 0.10.4 适配完成，状态: built
