# perl-moosex-test-role

MooseX::Test::Role — 用于测试 Moose/Moo 角色的工具模块，提供便捷函数创建消费角色（role）的类和对象，简化角色单元测试。

## 功能

- `requires_ok($role, @methods)` — 测试角色是否要求指定方法
- `consuming_class($role, %args)` — 创建消费角色的类，返回包名
- `consuming_object($role, %args)` — 创建消费角色的对象实例
- `consumer_of($role, %methods)` — consuming_object 的别名（无命名参数）

支持 Moose::Role、Moo::Role 和 Role::Tiny 三种角色类型。

## 版本列表

| 版本 | 状态 | 编译日期 |
|------|------|----------|
| [0.08](./0.08/) | published | 2026-06-23 |
