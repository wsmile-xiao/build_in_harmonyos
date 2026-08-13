# s2n-tls 1.7.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 通过 Conan 声明 `aws-lc/5.4.0` 作为运行时依赖
2. 设置 `CMAKE_PREFIX_PATH` 指向 aws-lc 包目录，使 CMake 的 `find_package(crypto)` 定位到 `crypto-config.cmake`
3. 启用 `SEARCH_LIBCRYPTO=ON` 使用外部 libcrypto
4. 启用 `BUILD_TESTING=ON` 构建上游单元测试
5. 关闭 `UNSAFE_TREAT_WARNINGS_AS_ERRORS` 避免测试代码的平台特定警告导致构建失败
6. 执行 `conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | conanfile.py 中 url 字段指向 awslabs/s2n-tls | 组织名错误 | 修正为 aws/s2n-tls |
| 2 | manifest.yaml dependencies 为空列表 | 遗漏 aws-lc 依赖 | 填充为 ["aws-lc/5.4.0"] |
| 3 | conandata.yml 手动添加镜像代理 URL | 违反 R39 规范 | 移除镜像 URL，仅保留官方 GitHub 源 |
| 4 | s2n_stacktrace_test 测试失败 | OHOS 不支持 execinfo/backtrace | 使用 ctest -E 排除，在 MANIFEST.yml 声明豁免 |
| 5 | 上游测试未运行 (BUILD_TESTING=OFF) | 规则 5 硬性要求 | 启用 BUILD_TESTING=ON，在 build() 中运行 ctest |

## 源码修改

无补丁。上游源码未做任何修改，仅通过 CMake 选项控制构建行为。

## 依赖版本

- aws-lc/5.4.0 (提供 libcrypto 加密原语)
- OHOS 系统库: dl, rt, pthread

## 验证结果

```bash
conan create . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing

# 上游测试结果
282/283 Test passed (s2n_stacktrace_test 豁免)
99% tests passed, 0 tests failed out of 282

# test_package 结果
1/1 Test #1: test_s2n_tls ... Passed
100% tests passed, 0 tests failed out of 1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lib/libs2n.so | 3.3MB | 动态链接库 |
| include/s2n.h | - | 主头文件 |
| include/s2n/unstable/*.h (11个) | - | 不稳定 API 头文件 |
| lib/s2n/cmake/*.cmake (4个) | - | CMake 配置文件 |

## 注意事项

1. s2n_stacktrace_test 因 OHOS 不支持 execinfo/backtrace 而豁免，CMake feature probe 已正确检测该能力缺失
2. 上游集成测试 (19个) 需 Python pytest + s2nc/s2nd 命令行工具，未在适配中运行
3. 模糊测试 (30个) 需 LLVM -fsanitize=fuzzer，交叉编译环境不支持
4. libcrypto.a 来自 aws-lc，在构建时静态链接到 libs2n.so

---

**编译结束**: 2026-07-27 12:27
**最终状态**: built

## 最终状态

COMPLETED — s2n-tls 1.7.6 适配完成，状态: built
