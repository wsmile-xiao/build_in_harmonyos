# DRAFT-alpaca-vector-bool-proxy：`vector<bool>` 代理引用的序列化边界

## 现象

alpaca 上游测试在 OHOS libc++ 完成编译后链接失败，错误符号包含
`std::__n1::__bit_const_reference`，并指向未定义的泛型 `to_bytes` 实例。

## 根因

`std::vector<bool>` 是位压缩特化容器。它的迭代器返回实现相关的代理引用，
不是普通 `bool`。通用容器循环把该代理交给了“非聚合 class”序列化模板；该
模板只有声明没有定义，于是错误被延迟到链接阶段。

## 修复模式

`vector<bool>` 必须保留专用序列化重载：先写入容器长度，再把每个元素显式绑定
为 `bool` 值后进入标量路由。这样不依赖 libc++ 代理类型名称，也不改变已有
逐字节编码。反序列化仍使用 `vector<bool>` 的 bool 元素路径。

## 验证要求

上游测试必须完成编译和链接，并实际运行覆盖 `vector<bool>` 的测试；消费者还
应验证包含 `std::vector<bool>` 的聚合体序列化往返。仅通过编译、删除该测试或
忽略链接器未定义符号都不能作为通过证据。
