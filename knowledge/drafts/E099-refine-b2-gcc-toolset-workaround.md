# E099 边界细化：b2 在 OHOS 可直跑（gcc toolset 伪装绕过 --target 注入）

## 背景

E099 断言 b2（Boost.Build）不兼容 OHOS，本仓库全部 boost 包因此走手动编译
路线。任务 boost-1.85 1.85.0-b2-nodocs（PR #9275）按路径 C 设计了对照实验，
实证 b2 的真实可用边界。

## 错误特征（clang toolset 路线）

- `fatal error: '__config_site' file not found`
- `fatal error: 'cstddef' file not found`
- `cxx11_static_assert : no`（全部 cxx11 检查失败，cached）
- 库目标静默不构建（cxx_requirements 不满足）

## 根因

b2 clang toolset 的 `init-flags-cross`（tools/build/src/tools/clang.jam:96）
在 `<target-os>linux/<architecture>arm/<address-model>64` 下自动注入
`--target=arm64-pc-linux`，后置于用户配置，覆盖 OHOS clang 默认 target
（aarch64-unknown-linux-ohos）。target 变化导致 clang 的 include 搜索路径
丢失 libcxx-ohos 目录与 sysroot（对比：默认 target 下 4 条搜索路径，
`--target=arm64-pc-linux` 下只剩 1 条），libc++ 头文件全部找不到。

注意顺序陷阱：在 user-config.jam 的 `<cxxflags>` 里显式加
`--target=aarch64-unknown-linux-ohos` 无效——b2 把自己注入的 --target 放在
命令行更后（后写者赢）。

## 解法（已验证）

user-config.jam 以 **gcc toolset 名字**注册 OHOS clang++（gcc.jam 不注入任何
--target）：

```jam
using gcc : 15 : /data/service/hnp/bin/clang++ :
    <cxxflags>"-std=c++17 -stdlib=libc++ -O2 -DNDEBUG -fPIC ..."
    <linkflags>"-stdlib=libc++"
    <archiver>/data/service/hnp/bin/llvm-ar
    ;
```

引擎运行环境两个附加条件：
1. b2 二进制动态链接 libc++_shared.so → LD_LIBRARY_PATH 注入 SDK libc++
   目录（`clang++ -print-file-name=libc++_shared.so` 自省定位）
2. b2 testing.capture-output 写 /tmp/jam*.tmp → TMPDIR/TMP 重定向到可写
   目录（OHOS /tmp 只读，E002）

## 实证矩阵（2026-09-09/10）

| 实验 | 结果 |
|---|---|
| bootstrap.sh 自举 b2 引擎 | ✅（E068 的"SHELL 机制失败"未复现） |
| clang toolset 默认配置 | ❌ __config_site not found |
| cxxflags 显式正确 --target | ❌ 被 b2 后置覆盖 |
| **gcc toolset 伪装** | ✅ 全通 |
| 10 库 b2 构建（static+multi） | ✅ ELF64/AArch64 |
| b2 原生测试框架 | ✅ 259 项 0 失败（空闲时段另验证 1134 项全过） |
| b2 install（--prefix） | ✅ |
| tool_requires b2 5.3.2 一致性 | ✅ 与源码树 b2 5.1.0 行为一致 |

## 对既有知识的影响

- E099：`rec_priority=1 use-cmake-build` 与 `rec_priority=2 header-only`
  之间应插入新首选：**gcc toolset 伪装直跑 b2**（对 1.86-1.89 等
  CMake 官方支持不完整的中间版本尤其有价值）
- E068：SHELL 执行机制问题在 b2 5.1/5.3 实测未复现；E068 本体是 python
  ctypes find_library 的 ldconfig 问题，与 boost 无直接关系（历史归档错误关联）

## 参考

- 配方：archives/b/boost-1.85/1.85.0-b2-nodocs/conanfile.py
- 完整实验报告：archives/b/boost-1.85/1.85.0-b2-nodocs/notes.md
- PR：#9275
