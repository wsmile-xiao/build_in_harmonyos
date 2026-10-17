# libcork

## 简介

A simple, easily embeddable cross-platform C library（轻量可嵌入式跨平台 C 基础库）。
提供数据结构（array/buffer/dllist/hash-table/ring-buffer/slice/mempool/managed-buffer）、
核心工具（allocator/error/gc/hash/byte-order/ip-address/timestamp）与进程管理
（subprocess/directory-walker/threads descriptor），并附带 cork-hash 命令行工具。

## OHOS 适配

- 构建系统: cmake
- 适配版本: 0.9.0
- 补丁: version.sh 修复、CORK_BUILD_TESTS 选项、BUILD_SHARED_LIBS 控制、
  cork_ipv6_init 越界修复（上游缺陷）、cmake_minimum_required 提升至 3.5
- 详见各版本 notes.md 与 reports/test-report.md 获取适配详情

## 依赖

- 无运行依赖；上游单元测试需要 check 框架（制品仓已发布 check/0.15.2）

## 功能验证

- 上游测试全量台账: 45 check 单元用例 + 29 cram CLI 用例 = 74/74 通过
- OHOS 专项测试（端序/哈希确定性/buffer/timestamp）全部通过
- test_package 消费者验证通过

## 参考

- 上游仓库: https://github.com/dcreager/libcork
- 许可证: MIT（RedJack, LLC）