# alpaca 0.2.1 适配笔记

## 适配结论

- 构建系统：CMake；源码包 SHA-256 为 `05d49a2dc9c6a9e07c0cbc4e26caec273a8666270c82d7c3f0ede4f3a9258f4e`。
- 适配路径：路径 B（依赖适配并沉淀 OHOS 类型可移植性知识）；补丁仅扩展
  `long long` 与 64 位整数等价处理，并将 `vector<bool>` 代理引用显式转成
  `bool`，不改变序列化格式。
- 配方关闭 samples、benchmarks 和 Python 绑定，并在 `can_run(self)` 时执行上游 doctest。

## 验证

- 上游：349/349 通过；计数来自设备端 doctest 运行时的实际 test cases。
- OHOS 修复：上游 `std::chrono::milliseconds::rep` 为 `long long`，而原版
  仅为 `int64_t` 提供序列化、反序列化、类型信息和大小端处理，导致编译期
  无匹配重载；`0001-support-long-long-duration-rep-on-ohos.patch` 逐处补齐。
- 链接修复：OHOS libc++ 的 `vector<bool>` 迭代器产生代理引用，原版将其送入
  只有声明没有定义的泛型类模板；`0002-serialize-vector-bool-values.patch`
  在专用重载中按 `bool` 值逐项路由，避免未定义符号。
- 包装修复：上游 CMake 只安装 `include/alpaca/detail/*.h`，遗漏公开的
  `include/alpaca/detail/types/*.h`；配方现在递归复制完整 public header tree，
  并由消费者测试实际 include/使用这些头文件。
- 知识库草稿：`knowledge/drafts/DRAFT-alpaca-ohos-duration-long-long.{kv,md}`
  和 `knowledge/drafts/DRAFT-alpaca-vector-bool-proxy.{kv,md}`。
- 消费者：1/1 通过，调用 `alpaca::serialize` 与 `alpaca::deserialize` 验证聚合体往返。

## Conan 包接口

- CMake 包名：`alpaca`。
- CMake target：`alpaca::alpaca`。
- 运行时链接库：无。
