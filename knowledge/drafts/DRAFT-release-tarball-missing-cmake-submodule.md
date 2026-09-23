# DRAFT-release-tarball-missing-cmake-submodule：发布归档缺失 CMake 子模块的处理边界

## 现象

某些 GitHub release tarball 保留 `.gitmodules` 和对 `cmake/common` 的引用，却没有把子模块内容打进发布归档。此时根 CMake 可能在 `include(tools)`、`include(compile_flags)` 或自定义安装宏处失败。recipe 若直接执行 `git submodule update`，还会引入未锁定的 SSH 网络和非源码依赖。

## 可复用处理

1. 先核对发布 tarball 是否真的包含子模块目录和被引用的 CMake 模块；不要把工作树中偶然存在的子模块误当作 release 内容。
2. 对 header-only 库，优先确认公共头文件能否独立编译，并在 recipe 中用锁定的官方 tarball + Conan package layout 建立包边界。
3. 若上游自带示例是唯一可执行验证，可用 profile 指定的 OHOS 编译器直接构建并运行这些示例；test_package 再通过生成的 CMake target 真实调用公共 API。
4. 只有在子模块来源、版本和许可均可锁定时，才考虑把它作为显式 source/patch 纳入 recipe；不要在构建中执行未锁定的 SSH 子模块更新。

## 证据

- fsm-variant v1.0.0 的 `.gitmodules` 声明 `cmake/common`，但官方 tarball 中不存在该目录；根 CMake 随后报 `include could not find requested file: tools/compile_flags` 与 `Unknown CMake command configure_and_install`。
- 直接用 OHOS clang++ C++17 构建官方两个示例、再用 Conan CMakeDeps consumer 验证 `mp::fsm` 均通过。

## 边界

这条知识不适用于语言预检不匹配，也不允许跳过真实上游测试、伪造安装产物或用 dummy 子模块掩盖 API/ABI 问题。
