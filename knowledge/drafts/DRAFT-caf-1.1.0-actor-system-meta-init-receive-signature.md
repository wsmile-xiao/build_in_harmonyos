# DRAFT-caf-1.1.0-actor-system-meta-init-receive-signature：CAF 1.x 消费者四大约束

> Contributor: pc5-7 | Status: Draft | Updated: 2026-09-06
> Source: caf 1.1.0 HarmonyOS PC 首轮适配（archives/c/caf/1.1.0，task caf-1.1.0-r01-pc5-7-20260905T171638Z）
> 对应：knowledge/drafts/DRAFT-caf-1.1.0-actor-system-meta-init-receive-signature.kv

## 现象

在 OHOS/arm64 上编译并运行 CAF（C++ Actor Framework）1.1.0 的消费者程序时，
依次暴露四类真实问题：

1. **运行期 FATAL**（exit 134）：

   ```text
   [FATAL] critical error (caf/actor_system.cpp:429):
   actor_system created without calling caf::init_global_meta_objects<>() before
   ```

2. **编译期 static_assert**：

   ```text
   error: static assertion failed due to requirement 'std::is_same_v<long, void>':
   OnValue must return void      （OnError must return void 同）
   ```

3. **编译期模板推导失败**：

   ```text
   error: no type named 'type' in 'caf::infer_handle_from_class<
     caf::typed_event_based_actor<...>, false>'
   ```

4. **运行期挂起**：进程在 `sys.await_all_actors_done()` 无限等待（timeout 杀掉）。

## 根因

CAF 1.x 相对 0.19 系列重写了运行时初始化与类型注册机制（meta-object 表）：

- ① 创建任何 `actor_system` 之前必须调用 `caf::core::init_global_meta_objects()`
  注册全局类型表，否则第一执行点即 FATAL。
- ② `blocking_response_handle::receive` 的 OnValue / OnError 回调必须返回 `void`
  （`detail::response_type_check` static_assert 强制）；结果只能经引用捕获写出，
  不能 return 值。
- ③ `sys.spawn(typed_impl, ...)` 推导 typed actor 时，若翻译单元只包含
  `caf/typed_actor.hpp`，`typed_event_based_actor` 仍为前向声明，
  `std::is_base_of_v<abstract_actor, T>` 无法求值 → `infer_handle_from_class`
  SFINAE 失败；必须补包含 `caf/typed_event_based_actor.hpp`。
- ④ 事件型 actor（behavior 返回后继续等待消息）运行计数永不为 0，
  `await_all_actors_done()` 永不返回（用 `-n` 跑上游测试二进制不受影响，因为
  测试 main 自带退出序列）。

## 与现有知识的关系（确认去重证据）

检查范围：knowledge/graph/index.tsv（540 条正式条目）+ knowledge/graph/E*.kv +
knowledge/drafts/（83 条草稿）+ knowledge/*.md（平台真理/模式文档）。
检索词：actor / caf / typed_actor / meta_object / init_global / receive /
infer_handle_from_class / send_exit / await_all_actors_done。
结果：四范围均为 **0 语义命中**（drafts 中 DRAFT-ohos-musl-rtti 与 E2173 仅
"actor"/"receive" 字样出现在 fallback 描述文本，属关键词误命中，已排除）。
引擎复检：`engine "actor_system created without calling caf::init_global_meta_objects"`
→ E242（Fortran .mod，无关）；`engine "OnValue must return void"` → E259
（NDEBUG assert，无关）。均非 CAF 知识覆盖。

## 知识库沉淀价值

- **可复用问题类别**：CAF 1.x 消费者适配（任何依赖 CAF 1.x 的库/程序）。
- **适用对象**：test_package 消费者验证、上游测试驱动 main、CAF 下游库
  （如基于 CAF 的分布式/网络应用）迁移 OHOS 或 Linux 时的编译与运行。
- **决策价值**：命中 FATAL/断言/推导失败任一特征即可直接套用四条约束，
  避免反复试错；与 0.19 旧 API 差异显著，移植需按 1.x 重写调用点。

## 修复方案（已在本轮真实验证）

1. `#include <caf/init_global_meta_objects.hpp>`，main 入口首行调用
   `caf::core::init_global_meta_objects()`。
2. receive 一律 void 回调 + 引用捕获（错误经 `caf::error&` 捕获写引用）。
3. typed spawn 翻译单元同时包含 `caf/typed_actor.hpp` 与
   `caf/typed_event_based_actor.hpp`。
4. 收尾先对每个事件型 actor `self->send_exit(actor_cast<caf::actor>(a),
   caf::exit_reason::user_shutdown)`，再 `sys.await_all_actors_done()`。

## 验证

- OHOS 专项测试（tests/ohos_smoke.cpp）：8 个 typed counter actor × 200 轮
  add/get 消息往返，计数器 1600/1600，`OHOS smoke test PASSED`（exit 0）。
- test_package 消费者（test_package/test_package.cpp）：`CAF 64 ping result:
  pong:hello`（exit 0）。
- 上游测试：caf-core-test 188/188 suites、caf-io-test 8/8、caf-net-test 29/29、
  caf-test-test 5/5（230/230 CTest 注册项全过，11574/11574 checks）。

## 边界与反例

- 本约束为 CAF 1.x（1.0/1.1 主线）自身 API 契约，与 OHOS 平台无关，跨平台通用。
- 0.19.x 及更早版本无此四约束，勿套用；1.x 的 `scoped_actor` 快捷链式调用
  （`.` 链）是可选的，不会消除对 init 与签名约束的需求。
- 仅读库（不使用 actor_system/typed actor/receive）的消费者无需这些调用，
  但真实 CAF 库几乎都走 actor 运行时，约束普遍适用。

## 决策

- 四范围查重未命中、存在组合/边界/测试迁移新增差异 → **new_draft（路径 B）**。
- 关系字段：similar_to / caused_by / prerequisite_of / conflicts_with 均无
  （引擎误匹配 E242/E259 语义无关）。