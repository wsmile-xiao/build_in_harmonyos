# aws-c-mqtt 0.15.2 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-07-18
- 编译器: clang
- 状态: built

## 编译步骤
使用 Conan 2 驱动标准 CMake 构建：

1. 导出同 PR 中的 AWS C 依赖配方：aws-c-common、aws-c-cal、aws-c-compression、aws-c-io、aws-c-http。
2. 配置 `BUILD_SHARED_LIBS=OFF`、`BUILD_TESTING=ON`。
3. 执行 `cmake.configure()`、`cmake.build()` 和 `cmake.test()`，运行上游 CTest 测试。
4. 通过 `test_package` 编译并链接 `aws-c-mqtt`，覆盖基础初始化与依赖链接场景。

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CI Worker 访问 GitHub 源码偶发超时 | Worker 网络对 github.com 不稳定 | 保留官方 URL 首位，并补充 3 个经过 SHA256 校验一致的镜像 URL 作为下载兜底 |
| 2 | CI 门禁要求执行上游官方测试 | 仅构建库和 test_package 不足以满足 L1 测试执行验证 | 启用 `BUILD_TESTING=ON` 并在 `build()` 中调用 `cmake.test()` |

## 验证
- 源码镜像均与官方 tarball 的 SHA256 一致：`66f3f5edff4ad1f765a86d3342b6017d0f29f950c1c24f8c1edacdc895202edc`。
- `conanfile.py` 通过 Python 语法检查。
- CI 中以最新提交为准执行 `/rebuild` 后验证。
