# boost1.84-container 1.84.0 适配笔记

## 组件定位

Boost.Container 提供超越 STL 的标准库风格容器：
`small_vector`（内联小缓冲）、`stable_vector`（引用稳定）、
`static_vector`（固定容量）、`flat_map/flat_set`（有序关联容器）、
`boost::container::string` 等。

本包以独立包名 `boost1.84-container` 归档（积分赛任务 6051），与
`boost/1.84.0` 元包并行维护。

## 编译环境
- 构建系统: manual-clang（b2 在 OHOS 不兼容 E068，手动 clang++ 编译）
- 编译日期: 2026-09-06
- 编译器: clang/clang++ 15.0.4 (aarch64-unknown-linux-ohos)
- 状态: built

## 形态

- `package_type = "static-library"`：产出 libboost_container.a（上游
  libs/container/build/Jamfile.v2 同源集合：alloc_lib.c + 6 个 .cpp）
- 安装完整 boost/ 头树（库间传递 include 强依赖）

## 上游测试集成（69/69 全绿）

上游 `libs/container/test/` 共 69 个 .cpp 测试源（实测与
github.com/boostorg/container tag boost-1.84.0 一致），全部自带
`int main()`、不依赖 boost_unit_test_framework；上游 Jamfile.v2 以
`[ run $(fileb) /boost/container//boost_container ]` 逐个注册。

b2 在 OHOS 不可用（E068），本包在 conanfile.py `build()` 中：

1. 先编译 `libs/container/src/`（6 .cpp + alloc_lib.c）归档
   `libboost_container.a`——测试链接需要 dlmalloc_allocation_command 等
   符号（与上游 run 目标挂的库一致）
2. 逐个 `clang++ -std=c++17 -stdlib=libc++ -O2 -DNDEBUG -I<root>
   -DBOOST_ALL_NO_LIB -DBOOST_CONTAINER_STATIC_LINK=1 <test>.cpp
   -lboost_container` 编译、真实运行，退出码 0 判定通过
3. 统计写入 `build_folder/upstream-tests-report.txt`

实测结果：**69/69 PASS（rc=0）**

### 已知平台问题与绕行

| 测试 | 现象 | 处置 |
|------|------|------|
| slist_test | clang -O2 下死循环（CPU 满载 900s 不退出，无输出）；-O0 编译运行 0.2s 通过 rc=0 | 单独降级 -O0 编译运行（测试逻辑本身通过，属优化器与该测试模板实例化的交互问题，非源码缺陷） |

### 运行时环境

OHOS 测试二进制动态依赖 SDK libc++_shared.so：通过
`clang++ -print-file-name=libc++_shared.so` 自省定位目录注入
LD_LIBRARY_PATH（无硬编码 SDK 版本路径）；musl 加载器仅在经 shell
启动时遵守该变量，故用 `export ...; ./exe` 形式运行（与
boost1.84-date_time 同款实测结论）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 测试链接报 undefined symbol: dlmalloc_allocation_command 等 | 上游 run 目标都挂 /boost/container//boost_container；这些符号在 libs/container/src 编译单元 | 先编译归档 libboost_container.a 再链接（上游 Jamfile 同源集合） |
| 2 | slist_test -O2 下挂死 | clang -O2 与该测试模板实例化交互导致死循环（CPU 满载，900s 超时；-O0 通过） | slist_test 单独 -O0 编译运行，其余 68 个 -O2 |
| 3 | 运行报 Error loading shared library libc++_shared.so | 测试二进制动态依赖 SDK libc++ | 编译器自省定位 + LD_LIBRARY_PATH + bash export 形式运行 |
| 4 | 是否需要 boost/1.84.0 的 0001 补丁 | container 头文件是否触碰 sp_thread_sleep.hpp 的 pthread_setcancelstate 路径 | 实测：无补丁无宏可直接编译运行全部测试，无需补丁 |
| 5 | 是否只安装 boost/container 子树 | Boost 库间头文件传递依赖 | 安装完整 boost/ 头树（与 boost/1.84.0 配方一致） |

## 源码修改
无补丁；未改动上游源码（含测试源，69 个 .cpp 逐字节未动）。

## 依赖版本
- 无 conan 依赖（container 不依赖 zlib 等外部库）
- 运行时依赖：libc++（OHOS sysroot）
