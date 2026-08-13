# brainfuck 2.7.3 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-11
- 编译器: clang/clang++ (15.0.4, OHOS SDK)
- 状态: built

## 编译步骤

1. init-build 下载源码（waterlan 原官方源 404，改用 GitHub release tag 2.7.3）
2. 手动 CMake 配置验证：
   `cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DENABLE_EDITLINE=OFF -DENABLE_CLI=ON -DBUILD_TESTING=ON -DGETOPT_INCLUDE_DIR=<sysroot>/usr/include`
3. `make -j2 && make install DESTDIR=$TEST_PREFIX`
4. `ctest`：smoke 测试通过（1/1）
5. `conan create`（conan-verify G0-G4 + L2/L4/L5 全部通过）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Findgetopt.cmake 回退到 deps/getopt 编译失败（windows.h not found） | find_path() 不搜索编译器内置 sysroot，找不到 OHOS sysroot 的 getopt.h，回退到 Windows wingetopt shim | conanfile.py generate() 用 `_sysroot_include()` 探测编译器 include 搜索路径，显式设置 `GETOPT_INCLUDE_DIR`（R33） |
| 2 | 下游 find_package 报 include 路径不存在 | 上游 CMakeLists.txt `install(TARGETS)` 未安装公共头文件 brainfuck.h | package() 中补充 `copy(self, "include/brainfuck.h", ...)` |
| 3 | OHOS 无 editline 库 | ENABLE_EDITLINE=ON 默认要求 editline | `-DENABLE_EDITLINE=OFF`（交互式控制台为可选功能） |
| 4 | conandata.yml 注释含裸 URL 导致 pre-download 污染 | build_and_test.sh pre-download 正则提取注释里的仓库基础 URL，其 md5 前缀路径与 tarball URL 前缀相同，replace 时污染 sources.url | 注释中不写裸 URL |

## 源码修改

无补丁（patches/ 为空）。仅配方层处理：补充安装头文件 + getopt 查找路径。

## 依赖版本

无第三方运行时依赖（仅依赖 OHOS sysroot 的 getopt.h 与 libc）。

## 验证结果

```bash
# conan create 内 test_package 执行（libbrainfuck C API 运行 Hello World 并断言输出）
$ ctest
1/1 Test #1: test_brainfuck ... Passed 0.02 sec
100% tests passed, 0 tests failed out of 1

# CLI smoke test
$ brainfuck --version
brainfuck 2.7.3 (Aug 11 2026, 17:47:53)
Copyright (c) 2016 Fabian Mastenbroek.
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libbrainfuck.a | 静态库（C API） |
| bin/brainfuck | 命令行解释器 |
| share/man/man1/brainfuck.1 | 手册页 |
| share/brainfuck/cmake/* | CMake export 配置 |

## 注意事项

- 上游 CMakeLists.txt 不安装公共头文件，必须由配方 package() 补充（否则下游链接失败）
- getopt 查找必须指向工具链 sysroot，禁止回退到 deps/getopt（Windows shim）
- 官方源 waterlan.home.xs4all.nl 已失效（404），统一使用 GitHub release tag 2.7.3
---

**编译结束**: 2026-08-11 19:35
**最终状态**: built
