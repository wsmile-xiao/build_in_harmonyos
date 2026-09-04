# array-hash 0.7.2 适配笔记

## 编译环境
- 构建系统: CMake（库本身为 header-only）
- 编译日期: 2026-09-03
- 目标环境: OpenHarmony HongMeng Kernel 1.12.0 aarch64
- 工具链: OHOS Clang 15.0.4、CMake 4.1.2、Conan 2.29.1
- 状态: built

## 编译步骤

本地使用官方 `v0.7.2` 源码归档（SHA-256 为
`0f360be97fe21a3d6dc4e843559a3f7011e90cb31b483875802205209766591e`），在本地
提交 `85a647a1101a8a20055599ad764eeff58733ac77` 完成配方、补丁和测试后推送。
远端构建输入为任务私有目录
`/storage/Users/currentUser/tmp/w3-array-hash-src-85a647a110`，不是 Git worktree；
来源 SHA、完整输入清单和逐文件哈希核对见工作流设备运行报告。

实际设备命令为：

```bash
cd /storage/Users/currentUser/tmp/w3-array-hash-src-85a647a110/archives/a/array-hash/0.7.2
conan create . \
  -pr:h=/storage/Users/currentUser/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/ws/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

配方先以 CMake 配置 C++11，再用 OHOS clang++ 静态编译上游五个 Boost.Test 源文件，
最后由 Conan 构建并运行 CMake consumer test；构建和测试均按 `-j1` 执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试默认需要 Boost.Test 链接库 | OHOS 设备缓存提供 Boost 头文件，但未提供可用的 `libboost_unit_test_framework` | 应用 `0001-use-header-only-boost-test.patch`，把入口改为 `boost/test/included/unit_test.hpp`，并定义 `BOOST_DISABLE_THREADS` |
| 2 | CMake toolchain 显示 profile 的 C++17 | 远端 profile 的默认 `compiler.cppstd` 为 17 | 库配方和 test package 都显式传递 `CMAKE_CXX_STANDARD=11`；日志确认 CMake 将标准修改为 11，上游直接编译命令也使用 `-std=c++11` |
| 3 | 远端全量 worktree 存在 `libXext` 大小写碰撞 | HMDFS 大小写不敏感导致 `libXext` 与 `libxext` 不能同时无损落盘 | 不清理共享 worktree；使用来源 SHA 导出的任务私有 scoped snapshot，并记录该冲突未进入本次构建读取范围 |

## 源码修改

`0001-use-header-only-boost-test.patch` 仅修改上游 `tests/main.cpp` 的 Boost.Test
入口头文件；没有修改 array-hash 的公共 API 或实现。配方导出四个公共头文件
（`array_growth_policy.h`、`array_hash.h`、`array_map.h`、`array_set.h`）和 LICENSE。

## 依赖版本

测试构建依赖 `boost/1.90.0` 的头文件；运行时没有 Conan 依赖。源码和工具链版本
分别由上面的归档 SHA、OHOS Clang 15.0.4、CMake 4.1.2 和 Conan 2.29.1 固定。

## 验证结果

```bash
Running 153 test cases...
*** No errors detected
array-hash consumer test PASSED
EXIT_CODE=0
```

上游测试通过 153/153；`test_package` 构建并执行 1/1，消费者程序包含 10 个显式
map/set API 检查，全部通过。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `array-hash/0.7.2` Conan package | header-only | 4 个公共头文件、LICENSE；package ID `da39a3ee5e6b4b0d3255bfef95601890afd80709` |

## 注意事项

源码包名 `array-hash` 与上游 CMake 包名 `tsl-array-hash` 不同；消费者应使用
`find_package(tsl-array-hash CONFIG REQUIRED)` 和 `tsl::array_hash`。本次远端验证
的来源 worktree 仍保留与本库无关的大小写冲突，不能将任务私有 snapshot 作为完整无损
仓库副本；设备运行报告保存实际输入目录、清单和例外证据。
