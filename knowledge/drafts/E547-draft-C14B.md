# E547（草稿）CMake 4.x 对 -D 相对值安装目录变量解析到 CMAKE_BINARY_DIR → 主库"安装"进构建树被静默跳过

- **现象**：`conan create` 成功且无报错，但包内 `lib/` 缺主库共享库（只有插件/头文件）；构建树 `lib/` 里却有主库。`cmake --install` 日志无对应条目。
- **根因**：本环境 CMake 4.1.2 对经 `-D` 以普通变量传入的相对值（如 `LIB_INSTALL_DIR=lib`），在上游 CMakeLists 执行 `set(LIB_INSTALL_DIR ... CACHE PATH)` 类型升级时按 `CMAKE_BINARY_DIR` 解析为 `<build>/lib`。该目录同时是 `CMAKE_LIBRARY_OUTPUT_DIRECTORY`（构建产物地），安装"源=目的"，`cmake --install` 静默跳过。最小复现实验：仅 `LIB_INSTALL_DIR` 这一命名触发，其他命名不触发；传绝对值则直通。
- **解法**：配方 `generate()` 对 `LIB_INSTALL_DIR` 传包目录绝对路径（`self.package_folder + "/lib"`）。
- **验证**：包内 `lib/libopenbabel.so{,.8,.8.0.0}` 齐全；上游 ctest 与 test_package 全过。
- **注意**：同配方的 `CMAKE_LIBRARY_OUTPUT_DIRECTORY` 也传绝对路径（`<build>/lib`），与上游测试 ENVIRONMENT 的烘焙假设一致。
- **来源**：openbabel 3.2.1 OHOS aarch64 适配，PR #14369。
