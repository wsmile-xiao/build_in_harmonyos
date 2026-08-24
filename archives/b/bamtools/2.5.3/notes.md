# bamtools 2.5.3 OHOS 适配笔记

## 构建信息

- 上游源码：<https://github.com/pezmaster31/bamtools/releases/tag/v2.5.3>
- 构建系统：CMake
- 编译器：Clang 15，libc++
- Conan 依赖：`zlib/1.3.1.1`
- 构建类型：静态库与命令行工具
- 源码补丁：无

## 适配说明

BamTools 2.5.3 可直接使用 Conan 的 `CMakeToolchain` 和 `CMakeDeps` 在 OHOS aarch64 上构建。配方显式启用静态库和上游 CTest，并使用已发布的 zlib 配方提供 `find_package(ZLIB)` 所需配置。

旧归档中手工链接 libc++/libc++abi 的补丁不再由 Conan 配方使用；工具链已通过 `compiler.libcxx=libc++` 提供正确的标准库配置。

## 测试结果

### 上游测试

上游注册 2 个 CTest，用例均保留并在 `conanfile.py::build()` 中执行：

1. `bamtools_help`：执行 `bamtools --help`。
2. `bamtools_stats`：对上游 `sam_spec_example.bam` 数据执行统计。

探索性构建和 `conan create` 均通过 2/2 上游测试。

### 消费者测试

`test_package/test.cpp` 链接已打包的 `bamtools::bamtools` 目标，调用 `BamAlignment::SetIsMapped()` 与 `IsMapped()` 验证实际 API。测试采用 Conan 临时构建目录并显式激活 `conanrun` 环境。

## 验证命令

```bash
python3 $SKILL_ROOT/scripts/ohc-run.py conan-verify bamtools 2.5.3
python3 $SKILL_ROOT/scripts/ohc-run.py finish bamtools 2.5.3 built
```

最终状态：`built`，等待 PR CI 验证与合并后发布。
---

**编译结束**: 2026-08-23 23:46
**最终状态**: built
