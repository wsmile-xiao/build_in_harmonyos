# DRAFT-glob-0.0.1：离线 CMake 安装边界

## 现象

`p-ranav/glob` 是无外部运行时依赖的 C++17 库，但上游 CMakeLists 在 configure 阶段通过 CPM.cmake 下载 `PackageProject.cmake`。源码归档同时没有自动化测试目标和显式 install 规则，因此直接套 Conan CMake 配方会遇到网络依赖，或无法形成可消费的 package/lib 与 package/include。

## 可复用处理

当 PackageProject 只负责安装/导出，而不参与库编译时，可以：

1. 删除 configure-time CPM/PackageProject 网络获取。
2. 明确声明库类型（本例为 `STATIC`）。
3. 使用 `GNUInstallDirs` 添加 `install(TARGETS ...)` 和 `install(DIRECTORY include/ ...)`。
4. 让 Conan 的 `CMake.install()` 收集安装结果。
5. 用真实 API consumer 验证头文件、链接库和运行时返回值。

该知识适用于离线 Conan/CI 的一般 CMake 依赖，不是 glob 的一次性补丁；若 helper 还承担其他功能，应改用 pinned 本地 helper 或受控构建依赖。
