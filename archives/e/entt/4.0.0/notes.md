# entt 4.0.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-19
- 编译器: clang/clang++ (OHOS SDK 15.0.4, aarch64-unknown-linux-ohos)
- 状态: published

## 编译步骤

entt 是 header-only C++ ECS 库，无编译产物，只需安装头文件。

```bash
source .build-context-entt-4.0.0
cd $BUILD_SRC_DIR
export OHOS_TOOLCHAIN_FILE="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/build/cmake/ohos.toolchain.cmake"
cmake -B build -DCMAKE_TOOLCHAIN_FILE=$OHOS_TOOLCHAIN_FILE -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DENTT_INSTALL=ON
cmake --build build -j1
cmake --install build --prefix $TEST_PREFIX
```

注意：entt CMakeLists.txt 中 ENTT_INSTALL 默认 OFF，必须传 -DENTT_INSTALL=ON 才会安装头文件。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | "missing 'typename' prior to dependent type name" 编译错误 (149处 + 8处 ::template) | entt v4.0.0 使用 C++20 P0634R3 特性（省略 typename），OHOS SDK clang 15.0.4 不完全支持 | 在所有依赖类型名前添加 `typename` 关键字，涉及 32 个头文件 |
| 2 | ctest 无法运行 | 上游测试用 FetchContent 从 GitHub 下载 GoogleTest，GitHub 不可达；find_package(GTest) 也未安装 | 记录原因跳过；header-only 库验证通过编译测试程序（include entt.hpp + registry API 调用）替代 |

## 源码修改

32 个头文件添加 `typename` 关键字以兼容 clang 15 C++20 不完整支持：

核心修改模式：
1. `using X = Y<...>::type;` → `using X = typename Y<...>::type;` (149处)
2. `using X = Y::template Z<...>;` → `using X = typename Y::template Z<...>;` (8处)
3. `using X = alloc_traits::allocator_type;` → `using X = typename alloc_traits::allocator_type;` (1处)

涉及文件（全部在 src/entt/ 下）：
- core/type_traits.hpp, core/iterator.hpp, core/memory.hpp, core/algorithm.hpp, core/hashed_string.hpp
- container/dense_map.hpp, container/dense_set.hpp
- entity/entity.hpp, entity/fwd.hpp, entity/group.hpp, entity/handle.hpp, entity/helper.hpp
- entity/mixin.hpp, entity/organizer.hpp, entity/registry.hpp, entity/runtime_view.hpp
- entity/snapshot.hpp, entity/sparse_set.hpp, entity/storage.hpp, entity/view.hpp
- graph/adjacency_matrix.hpp, graph/flow.hpp
- meta/container.hpp, meta/node.hpp, meta/utility.hpp
- poly/poly.hpp
- process/process.hpp, process/scheduler.hpp
- resource/cache.hpp
- signal/dispatcher.hpp, signal/emitter.hpp, signal/sigh.hpp

## 依赖版本

无外部依赖。entt 是纯 header-only 库，仅需 C++20 编译器。

## 验证结果

```bash
# 头文件编译验证
clang++ -std=c++20 -I src test_entt.cpp -o test_entt
# test_entt.cpp: include entt/entt.hpp, create registry, emplace/get component
# 编译通过，运行返回 0

# ctest 状态：跳过（GoogleTest 依赖不可达）
```

## 注意事项

- GitHub 直连不可达，源码通过 gh-proxy.com 镜像下载
- make -j2 因 mkfifo 权限问题失败，改用 -j1
- ENTT_INSTALL 必须显式设为 ON
- 上游测试依赖 GoogleTest（FetchContent 或 find_package），本环境不可用
---

**编译结束**: 2026-08-19 12:08
**最终状态**: built
