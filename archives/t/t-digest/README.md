# t-digest

T-Digest — Ted Dunning 的流式分位数估计算法，用极小的内存对海量数据估计中位数、P95/P99 等分位数，支持合并（map-reduce 友好）。

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 3.0 | built | 源码编译（Maven），GitHub tag 下载 |

## 概述

t-digest 提供：
- 流式 add（单点与加权）与压缩（compress）
- 分位数估计（quantile）与分布函数（cdf）
- 多 digest 合并（add(other)）与序列化（asBytes/asSmallBytes）
- ArrayDigest / TreeDigest / AVLTreeDigest 三种实现

## 构建方式

- **类型**：源码编译（Maven）
- **来源**：GitHub（tdunning/t-digest tag t-digest-3.0）
- **Java 运行时**：bishengjdk 17.0.13
- **许可证**：Apache-2.0

## 测试

test_package 通过 Java API 调用验证 t-digest 功能：
- 编写 TestTDigest.java，覆盖 create/add/quantile/cdf/size/centroidCount/compress/merge 与 NaN 拒绝
- test.sh 使用 javac 编译、java 运行测试程序
- 14 个断言覆盖 ArrayDigest、TreeDigest、AVLTreeDigest 与合并路径
