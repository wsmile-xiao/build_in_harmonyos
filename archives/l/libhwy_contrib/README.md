# libhwy_contrib

Google Highway 上游工程 `hwy_contrib` 目标库的独立 Conan 包：包含 vqsort 向量化排序
（`hwy/contrib/sort`）、图像处理（`hwy/contrib/image`）、线程池与拓扑感知
（`hwy/contrib/thread_pool`，编译源 `topology.cc`）的实现，其余 contrib 组件
（algo/dot/math/matvec/random/bit_pack/unroller）为纯头文件接口。

与核心包 `highway`（同上游 google/highway）的关系：本包经 `requires` 引用
highway 获取核心 `libhwy` 与全部头文件，自身只安装 `libhwy_contrib` 编译库，
消费图内不产生重复头文件。消费者直接依赖本包即可使用 contrib 功能。

- 上游: https://github.com/google/highway
- 许可证: Apache-2.0
- 构建系统: CMake
