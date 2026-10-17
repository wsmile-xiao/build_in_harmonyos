# c4core 0.6.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-31
- 编译器: clang/clang++
- 状态: built（最终 SHA 已完成鸿蒙 PC 定向 CI、Conan create 和 test_package 运行验证；尚未 release upload）

## 编译步骤

1. 下载源码包：https://github.com/biojppm/c4core/archive/refs/tags/v0.6.0.tar.gz
2. 初始化编译环境：`python3 scripts/ohc-run.py init-build c4core 0.6.0 --url=<URL>`
3. 语言预检：`python3 scripts/ohc-run.py lang-preflight c4core 0.6.0 --src=$BUILD_SRC_DIR`（判定为 C++）
4. Conan 配方构建：`conan create archives/c/c4core/0.6.0 --profile=ohos-aarch64 --build=missing`
5. CMake 配置由 `CMakeToolchain` 生成，启用 `C4CORE_INSTALL=ON` 和 `BUILD_SHARED_LIBS=OFF`
6. recipe 和 test_package 都通过 `build_tool_args=["-j1"]`，随后由 Conan 执行安装与 test_package

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 配置报错 "unknown platform. CMAKE_SYSTEM_NAME=HarmonyOS" | c4Project.cmake 的 c4_install_exports() 函数中平台检查不包含 HarmonyOS | 修改 cmake/c4Project.cmake 第 2796 行，在 elseif 条件中添加 `(CMAKE_SYSTEM_NAME STREQUAL HarmonyOS)` |
| 2 | `c4Project.cmake` 依赖的 CMake 模块缺失 | cmake 位于 git submodule (biojppm/cmake)，release tarball 不含其内容 | 将实际依赖的模块随 recipe export_sources 一起打包 |
| 3 | CMake 配置报错 `src/c4/ext/debugbreak/debugbreak.h` 不存在 | debugbreak 位于 git submodule，release tarball 中目录为空 | 将官方 `debugbreak.h` 随 recipe 导出并在 `build()` 中还原到源码子模块路径 |
| 4 | 上游 `aalloc_impl.error_out_of_mem` 在 OHOS 失败 | OHOS `posix_memalign()` 对 `SIZE_MAX / 2` 的非零申请返回 `ret=0` 但空指针，未触发 c4core 的错误回调 | 在 `aalloc_impl()` 中将“非零申请得到空指针”与 `ENOMEM` 同等处理；通过 Conan 补丁应用，不修改上游测试 |

## 源码修改

- **cmake/c4Project.cmake** 第 2796 行：在 c4_install_exports() 函数的平台判断 elseif 条件中添加 `(CMAKE_SYSTEM_NAME STREQUAL HarmonyOS)`，使 HarmonyOS 平台与 UNIX/Linux 使用相同的安装导出逻辑。
- 补丁文件：patches/0001-cmake-c4Project.cmake.patch
- **src/c4/alloc.cpp**：初始化分配指针，并将 `posix_memalign()` 返回成功但非零申请得到空指针的情况报告为内存不足。
- 补丁文件：patches/0002-alloc-posix-memalign-null.patch
- 子模块补齐：patches/submodules/debugbreak/debugbreak.h

`build()` 在恢复 release tarball 的 CMake/debugbreak 子模块内容后调用
`apply_conandata_patches()`，确保上述两个补丁都实际应用。

## 依赖版本

c4core 无外部依赖，仅需要 C++11 编译器。

## 验证结果

上游与 Conan 验证代码提交：`b957ca2f363e20ab2d7880bff7288c170aff3031`

- 平台：HarmonyOS PC arm64；Conan profile：`ci/conan/profiles/ohos-aarch64`
- Conan create：主库成功编译、安装和打包 `libc4core.a`；导出 12 个 CMake 模块及 `debugbreak.h`
- test_package：成功解析 `self.tested_reference_str`，链接 `c4core::c4core` 并实际运行；输出 `c4core version: 0.6.0`、`substr length: 26`、`All c4core tests passed!`
- 上游测试：保持 `C4CORE_BUILD_TESTS=ON`，未关闭或修改任何测试；CTest 注册 47 项，在 HarmonyOS PC arm64 的 `test/` 目录执行 `ctest --test-dir test --output-on-failure -j1`，47/47 通过（100%）
- L1e：破坏性反向验证通过，确认测试确实依赖 c4core
- L2：跳过，纯静态库没有 `bin/`
- L4：warning，上游 CMake 辅助脚本中包含通用危险函数匹配；未阻断 CI
- L5：通过，`lib/` 有内容

由于正式共享远端 worktree 存在用户未提交改动，且全仓库 JC5 会命中与本软件无关的隐藏文件，本轮使用最新 SHA 的远端隔离快照执行单软件定向 CI；这不改变正式 worktree。

## 注意事项

- c4core 是纯 C++ 静态库，无可执行文件
- cmake/c4Project.cmake 位于独立 submodule (biojppm/cmake)，需要单独获取
- 构建必须使用 out-of-source 模式（cmake 项目标准做法）
- BUILD_SHARED_LIBS=OFF 强制静态库（R26 规则）
