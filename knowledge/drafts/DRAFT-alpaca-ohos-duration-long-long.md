# DRAFT-alpaca-ohos-duration-long-long：OHOS `chrono::duration::rep` 类型可移植性

## 现象

在 OHOS 设备编译 alpaca 0.2.1 上游测试时，`std::chrono::milliseconds::rep`
被实现为 `long long`。原版头文件只对 `int64_t` 提供大整数序列化重载，因而
`duration` 测试在模板实例化阶段失败：

```text
error: no matching function for call to 'to_bytes'
requirement '... long long ...' was not satisfied
error: no matching function for call to 'from_bytes'
```

## 根因

`int64_t` 是实现相关的 typedef。不能假设它在所有 OHOS/C++ 标准库组合中都与
`long long` 是同一个类型。alpaca 0.2.1 的 `to_bytes`、`from_bytes`、`type_info`
和大小端分支使用精确 `std::is_same_v<T, int64_t>` 约束，未覆盖这种合法的
64 位整数类型表示。

## 可复用修复模式

涉及公开头文件模板和固定宽度整数时，应同时检查：

- 序列化与反序列化的所有容器重载；
- 类型信息映射，确保仍编码为同一个 64 位字段类型；
- 大小端转换分支，确保按相同宽度调用既有实现；
- `std::chrono::duration` 等标准库类型的实际 `rep` 类型。

本适配在上述四处补充 `long long` 处理，保持编码格式不变，并保留完整上游
测试。该问题是源码可移植性缺陷，不属于 OHOS 缺特性，因此不能通过关闭测试或
把失败登记为环境跳过来规避。

## 验证证据

alpaca 0.2.1 设备端最终应记录完整 doctest 运行结果、Conan 包安装结果和
消费者 `alpaca::serialize`/`alpaca::deserialize` 往返结果；上游用例数量按
运行时实际 `test cases` 统计，消费者用例另行计数。
