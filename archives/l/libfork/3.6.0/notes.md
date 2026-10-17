# libfork 3.6.0 适配笔记

## 编译环境
- 构建系统: cmake（header-only INTERFACE 库，C++23 协程）
- 编译日期: 2026-09-03
- 编译器: clang/clang++ 15.0.4（OHOS SDK 26.0.0.18，目标 aarch64-unknown-linux-ohos）
- 状态: built（conan-verify 8 门禁通过；制品发布由 CI 合并后流水线执行）

## 编译步骤
1. `ohc-run.py init-build libfork 3.6.0 --url=https://github.com/ConorWilliams/libfork/archive/refs/tags/v3.6.0.tar.gz`
   - 官方标签 v3.6.0 已核验（git ls-remote 70766ede）；tarball SHA-256 = 2265d2e3…（本地与重新下载一致）
2. `ohc-run.py lang-preflight libfork 3.6.0` — cpp 匹配通过（R47）
3. 探索编译（主机 aarch64，OHOS clang 15, `-std=c++2b`）：
   - `clang++ -std=c++2b -O2 -pthread -Iinclude test/single_header/main.cpp`（上游单头文件自检，fib(10)==55）
   - 等价消费者测试：`#include <libfork.hpp>` 的 fib(10)==55 + `lf::fold` 空 range 返回 nullopt + `lf::for_each` 原地自增 → 编译并原生运行通过（exit 0）
4. `ohc-run.py conan-init` → 重写 conanfile.py 为 header-library 配方（禁用 LF_NO_HWLOC/LF_NO_BOOST_ATOMIC）
5. `ohc-run.py refresh-patch --auto` → 生成 6 个补丁
6. `ohc-run.py conan-verify libfork 3.6.0` → G0-G4 + L2/L4/L5 全部 PASS
7. `ohc-run.py finish libfork 3.6.0 built` → W3 本地 CI 模拟通过（build_and_test.sh），归档完成

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `#include <source_location>` 编译失败（fatal error） | OHOS 定制 libcxx（libcxx-ohos, _LIBCPP_VERSION 15004）不提供 <source_location> 头文件，`__cpp_lib_source_location` 特性宏被注释禁用 | 补丁 0004：`__has_include(<source_location>)` + 特性宏能力探测；不可用时提供 lf::impl 内部最小 source_location_t 占位类型（file_name/line/function_name 返回空值），`non_null()` 默认参数改为 `make_source_location()`。纯能力探测，无平台宏 |
| 2 | `std::ranges::shuffle/max_element/destroy/uninitialized_default_construct_n/empty` 无匹配成员 | OHOS libc++ 以 `_LIBCPP_HAS_NO_INCOMPLETE_RANGES` 编译（头文件存在但符号未导出，属 incomplete ranges 集合） | 补丁 0001/0002/0003/0005/0006：替换为经典算法（std::shuffle / std::max_element 比较器 / std::destroy / std::uninitialized_default_construct_n / std::ranges::size==0），语义等价 |
| 3 | init-build 误判 BUILD_SYSTEM=autotools | libfork 为 CMake header-only 库，init-build 的构建系统探测不适用 | conan-init 生成的 autotools 模板配方整体重写为 CMake header-library 配方；manifest build.system 修正为 cmake |
| 4 | W3 JC 门禁被无关历史基线阻塞 | main 基线含其他库提交的运行时状态文件（embree/.submit-state.json 等 9 个路径）与 tarball | 按 oh-executor 基线规则：对审计确认属于其他库的精确路径做临时 index 隔离（git rm --cached，记录 blob/内容 SHA-256），W3 复验通过后无条件恢复（git reset），未提交、未删除基线文件 |

## 源码修改（补丁）

| 补丁 | 修改 |
|------|------|
| 0001 | algorithm/fold.hpp: `std::ranges::empty(range)` → `std::ranges::size(range) == 0`（2 处） |
| 0002 | core/co_alloc.hpp: `std::ranges::destroy(m_span)` → `std::destroy(begin,end)` |
| 0003 | core/impl/awaitables.hpp: `std::ranges::uninitialized_default_construct_n` → `std::uninitialized_default_construct_n` |
| 0004 | core/impl/utility.hpp: source_location include 加 `__has_include` 守卫；新增 source_location_t 占位类型与 make_source_location()；non_null 默认参数调整 |
| 0005 | schedule/impl/numa_context.hpp: `std::ranges::shuffle` → `std::shuffle` |
| 0006 | schedule/lazy_pool.hpp: `std::ranges::max_element(nodes,{},proj)` → `std::max_element` 比较器 |

## 依赖版本
- 无 Conan requires（Threads 为系统库；hwloc/Boost.atomic 可选依赖已禁用）

## 验证结果
```bash
# 上游等价测试（OHOS clang 15, -std=c++2b, aarch64 本机原生执行）
./fib_check   # fib(10)==55 → exit 0
./fold_check  # fold 空range nullopt + fold(1..10000)==50005000 + for_each → exit 0
# conan-verify：G0/G1/G2/G3/G4/L2/L4/L5 全 PASS
# finish W3：build_and_test.sh 本地 CI 模拟通过（conan create + L0 门禁）
```

## 注意事项
- libfork 需 C++23（CMake target cxx_std_23）；OHOS clang 15 接受 `-std=c++2b`
- 单头文件 single_header/libfork.hpp 为生成文件（tools/make_single_header.cpp），按 R6 不改生成文件；补丁只作用于 include/ 源码
- 上游完整 Catch2 测试套件因 ohpcd registry 无 catch2 配方无法在 OHOS 工具链构建，以单头文件自检 + 消费者等价测试替代（已记录于 test_package/MANIFEST.yml）
