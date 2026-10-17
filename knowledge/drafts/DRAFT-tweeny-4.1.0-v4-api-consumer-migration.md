# tweeny v4 API 消费者迁移（草案）

> 草稿编号：DRAFT-tweeny-4.1.0-v4-api-consumer-migration
> 来源：tweeny 4.1.0 适配（mobius3/tweeny @ tag v4.1.0；已有旧归档 tweeny/3）
> 生成日期：2026-09-19
> 路径判定：Path B（知识库扩展）→ new_draft

## 问题描述

本仓库已有 tweeny/3 归档（v3，无测试套件），本次适配 tweeny 4.1.0（v4）时，
沿用 v3 API 编写的 test_package 消费者测试在 conan create（G2 门禁）阶段编译失败：

```
test_tweeny.cpp:70:13: error: no member named 'onStep' in 'tweeny::tween<float>'
tweeny.h:248:9: error: static assertion failed due to requirement
  'std::is_same_v<int, unsigned int>': during() parameters must be of type uint32_t
tweeny.h:246:9: error: static assertion failed due to requirement
  'sizeof...(FrameCountsType) == value_count': during() must have one frame count per tween component
```

## 根因

tweeny v4 相对 v3 是破坏性 API 升级：

1. **事件接口改写**：v3 的成员方法 `onStep(cb)` 被移除，v4 改为
   `t.on(tweeny::event::step, cb)`——回调签名为 `event::response(tween&)`，
   返回 `event::response::ok` / `event::response::unsubscribe`。
2. **during() 类型强约束**：帧数参数必须为 `uint32_t`（int 字面量触发 static_assert
   `std::is_same_v<int, unsigned int>`）；多值 tween 的 during() 帧数必须与组件数
   一一对应（`sizeof...(FrameCountsType) == value_count`）。
3. **帧参数类型**：seek()/peek() 的帧参数由 float 改为 uint32_t。

根本模式：**主版本升级的 header-only 库，消费者测试若照搬旧版 API 会在编译期暴露**
（static_assert / no member 报错），且错误发生在 conan create 的 test_package 阶段，
属于"测试怎么写"而非"库怎么编译"的问题。

## 解决方案

1. 写 test_package/消费者测试前，先读目标版本头文件与 `src/tests/` 上游测试源码，
   确认真实 API 形态（v4 例：`tweeny::from(0.0f).to(100.0f).during(10u).build()`；
   事件用 `t.on(tweeny::event::step, [](const auto& t){ ...; return tweeny::event::response::ok; })`
   并在回调内 `t.peek()` 取值）。
2. 多值 tween 用 `std::get<N>(t.peek())`，单值走标量 API；during() 字面量显式写 `u` 后缀。
3. 配方 build() 保持上游测试选项 OFF（`TWEENY_BUILD_TESTS=OFF`），避免把测试框架
   （Catch2 v3）引入制品依赖；上游自带测试套件在适配流程独立配置
   （`-DTWEENY_BUILD_TESTS=ON` + 制品仓 Catch2/3.8.1）枚举并运行，双口径统计
   （source_declared_total=135 / configured_executable_total=135 /
   executed_passed_total=135/135=100%）。
4. **边界反例（E103 适用边界）**：上游 `cmake_minimum_required(VERSION 3.23...3.28)`
   （区间语法，最低 3.23 ≥ 3.5）被 CMake 4.x 直接接受，**无需**注入
   `CMAKE_POLICY_VERSION_MINIMUM=3.5`——E103 只适用于最低版本 < 3.5 的旧项目
   （如 tweeny v3 的 `VERSION 3.0`）。

## 验证

- conan-verify G2 conan create 通过（test_package 1/1 Passed + ALL CHECKS PASSED，17 断言）
- 鸿蒙专项测试 tests-ohos/ohos_test.cpp 17/17 PASS（exit 0）
- 上游 Catch2 套件 135/135 PASSED（100% 全量通过率，1.75s 实测）

## 适用边界

- 适用：任何已有旧版本归档（如 tweeny/3）的库在新主版本适配时的消费者测试迁移；
  任何"配方不引入测试框架依赖 + 上游测试独立运行"的 header-only 库。
- 反例/不适用：无版本升级的新库适配（API 直接按当前版本写即可）；上游确无测试
  套件且无版本升级的库。

## 查重结论

- exact_duplicate=false；causal_duplicate=false（E103/E321/E322/E307 根因不同）；
- trigger_overlap=partial（E321/E322 同为 header-only CMake INTERFACE 配方族）；
- solution_overlap=partial；combination_novelty=true（事件接口 + 类型强约束组合）；
- boundary_novelty=true（E103 边界反例：3.23...3.28 区间声明无需注入）；
- test_migration_novelty=true（配方不引入测试依赖 + 上游测试独立双口径运行模式）。
- 关系：`similar_to` E321/E322；`prerequisite_of` E103（边界补记）；其余无。
- 决定：`new_draft` → 走 Path B，本 .kv/.md 与前述归档文件同一 PR。