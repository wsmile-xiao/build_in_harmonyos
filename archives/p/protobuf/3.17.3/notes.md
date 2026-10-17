# protobuf 3.17.3 适配笔记（依赖库 · 方式二）

## 编译环境

- 构建系统：CMake（上游 require ≥3.1.3，实际版本见"工程点 5"）
- 生成器：Ninja（见"工程点 4"）
- 目标平台：HarmonyOS PC aarch64
- 编译器：OpenHarmony Clang 15（OHOS SDK），上游 C++11（配方未强制 cppstd，CMake 内 set C++11）
- 依赖：zlib/1.3.1（可选，with_zlib=ON，已在 ohpcd 制品仓发布、可下载）

## 迁移范围

protobuf 3.17.3（2021-05）是较老版本，构建结构与新版（如 33.6）差异明显：

1. **构建入口在顶层 `cmake/` 子目录**：根目录无 `CMakeLists.txt`。配方用 `CMake.configure(build_script_folder="cmake")`。
2. **不依赖 abseil-cpp**：abseil 是 protobuf ≥23.x 才引入的；3.17.3 仅有可选外部依赖 zlib。Deps 分析见 `reports/deps-report.md`。
3. **源码自带预生成 `.pb.cc`**：`src/google/protobuf/*.pb.cc` 共 11 个直接编入 `libprotobuf`/`libprotoc`，交叉编译无需运行 host `protoc`；`protoc` 为目标端 aarch64 二进制。

## 关键工程点（本环境障碍的自主动处理）

4. **OHOS 环境 `/bin/sh` 不可执行**：CMake 默认 Unix Makefiles 生成器调用 `/bin/sh` 报 `Permission denied`。改用 **Ninja** 生成器（`tc.generator = "Ninja"`）绕开。
5. **新 CMake 移除 `<3.5` 兼容**：上游 `cmake_minimum_required(3.1.3)` 触发 `Compatibility with CMake < 3.5 has been removed`。显式传 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5`。
6. **OHOS 文件系统禁止创建符号链接**：`protoc` 目标设置了 `VERSION` 属性，CMake 4 在 POSIX/OHOS 为可执行文件生成版本符号链接失败（`cmake_symlink_executable: Permission denied`）。打补丁去掉 `VERSION`，产物为普通 `protoc` 可执行（`patches/0001-disable-protoc-version-symlink.patch`）。
7. **conan cache 布局冲突**：conan cache 的构建根 `b/` 已被源码内容占用且含 `b/build` 路径，`cmake_layout` 生成的 `build/<build_type>` 子目录与之冲突（`NotADirectoryError`）。改用自定义 layout，build 目录设为 `bld`。
8. **pkgconfig 元数据可重定位**：安装后将 `.pc` 的 `prefix` 改为 `${pcfiledir}/../..`。
9. **上游 gtest 需要 C++11 兼容的 googletest**：googletest v1.15.2 要求 C++14，而 3.17.3 用 C++11（`set(CMAKE_CXX_STANDARD 11)`）。改用 **googletest v1.10.0**（C++11 兼容）放入 `third_party/googletest`，并开启 `protobuf_BUILD_TESTS=ON`。
10. **zlib target 名不匹配**：Conan 的 zlib 生成 CMake target 为小写 `zlib::zlib`，而上游 `cmake/CMakeLists.txt` 检查 `ZLIB::ZLIB`（大写）→ `ZLIB_LIBRARIES` 为空，导致上游 `tests`/`libprotobuf` 链接时 `undefined symbol: deflate`。在 `generate()` 注入 `ZLIB_LIBRARIES=zlib::zlib`，并打补丁 `0002-tests-link-zlib.patch` 给上游测试目标补 zlib 链接；`test_package/CMakeLists.txt` 补 `find_package(zlib CONFIG REQUIRED)`。
11. **test_plugin 子进程需 libc++**：上游 `CommandLineInterfaceTest` 会 fork 出 `protoc`/`test_plugin` 子进程，需 `LD_LIBRARY_PATH` 指向 OHOS SDK 的 `aarch64-linux-ohos` 才能加载 `libc++_shared.so`（否则报 `symbol not found`）。

## 测试统计

- 上游 gtest（构建 target：`tests`/`lite-test`/`lite-arena-test`）：已在真机构建并**实际运行，2330/2330 (100%) 全部通过**，无失败、无跳过（`tests` 为 2275/2275，200 test suites；`lite-test` 53/53；`lite-arena-test` 2/2）。
- test_package 消费者用例（Any 打包/解包、二进制序列化、JSON 转换、Arena）：**4/4 (100%)**，共 19 断言。
- `protoc --version` 烟雾测试：通过，输出 `libprotoc 3.17.3`。
- 运行说明：上游 gtest 运行需 `LD_LIBRARY_PATH` 指向 OHOS SDK 的 `aarch64-linux-ohos`（供 `protoc`/`test_plugin` 子进程加载 libc++）。

## 门禁与产物

- G2/G3/G4、L0/L2/L4/L5 均通过（详见 `reports/test_report.md`）。
- 产物 SHA256 基线见 `reports/test_report.md` §4。

## 路径分类

本次为依赖库适配（方式二），按路径 A（【依赖项】）提交，不申报 B/C。

---
**编译结束**: 2026-09-03
**最终状态**: built
