# DRAFT-emhash-1.2.0-upstream-test-header-api-drift-minimal-member-patch

> Draft: DRAFT-emhash-1.2.0-upstream-test-header-api-drift-minimal-member-patch
> 来源: emhash 1.2.0 R02 返工（executor pc2-31, 2026-09-22）
> 状态: 草稿（待审核 promote）

## 错误特征

```text
tests/unit/test_runtime_stats.cpp:18:16: error: no member named 'runtime_stats' in 'emhash8::HashMap<int, int>'
tests/unit/test_runtime_stats.cpp:202:7: error: no member named 'reset_stats' in 'emhash8::HashMap<int, int>'
```

## 触发条件

- 构建系统: cmake（header-only 库）
- 阶段: 上游测试编译
- 前提: 官方 tag 的 tests/ 中存在引用头文件未实现 API 的独立测试文件；该 API 在官方 tag 全部头文件与上游 main 分支均不存在（测试先于实现提交，test/header API drift）；测试文件自身声明默认配置（如 EMH_ENABLE_STATS=0）下 API 应返回基础快照

## 根因分析

上游把测试先于实现提交进 tag：tests/unit/test_runtime_stats.cpp 期望
runtime_stats()/reset_stats()/EMH_ENABLE_STATS 统计框架，但官方 v1.2.0 全部头文件
与上游 main 分支 grep 均为 0 命中（API 任何版本都不存在）。按未实例化测试恢复硬规则，
"已被源码枚举的独立测试未纳入测试目标"默认视为当前库测试构建缺陷，不能直接作为可接受
的统计差异——必须先核验 API 全树存在性，再在当前库允许范围内以最小补丁补齐可实例化项。

## 推荐方案

**方法**: upstream-test-header-api-drift-minimal-member-patch

**说明**: 三步恢复法（可跨库复用）:
1. 核验: 在官方 tag 全树（include/ 全部头）与上游 main 分支分别 grep 该 API/宏；双查均 0 命中才确证"测试先于实现提交"。
2. 最小补丁: 在当前库允许范围内（当前库自己的头文件，不触碰框架/其他库）给相关容器类补最小成员——快照结构 + runtime_stats() + reset_stats()；快照只反映真实容器状态（size/bucket_count/load_factor/max_load_factor），禁用宏（EMH_ENABLE_STATS=0 默认）下计数器返回 0、reset_stats 为空操作；不改变既有 API 与行为。
3. 运行与如实统计: 重新配置、编译并实际运行；可实例化项全部运行（本轮回 8/8 通过）；条件宏互斥分支（#if EMH_ENABLE_STATS 下的 10 个声明，上游无实现）如实保留未实例化，列入台账并给出恢复条件（上游实现完整统计框架），不计为通过、计入分母。

**验证/命令**:
```bash
# 1. API 全树+上游 main 双查
grep -rn "runtime_stats\|reset_stats\|EMH_ENABLE_STATS" include/ tests/   # tag 全树
curl -s https://raw.githubusercontent.com/ktprime/emhash/main/include/emhash/hash_table8.hpp | grep -c runtime_stats  # 上游 main
# 2. 最小补丁后重新配置编译运行
cmake -B build -DEMHASH_ENABLE_FUZZ=OFF -DEMHASH_ENABLE_BENCH=OFF
cmake --build build --target test_runtime_stats -j1
./build/test_runtime_stats    # 8/8 passed
```

## 关键词

test/header API drift, 测试先于实现, upstream test ahead of implementation, runtime_stats, no member named, header-only, 最小补丁, 未实例化恢复, EMH_ENABLE_STATS