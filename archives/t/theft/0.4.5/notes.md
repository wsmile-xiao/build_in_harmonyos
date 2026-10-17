# theft 0.4.5 适配笔记

## 适配结论

- 构建系统：上游 Makefile；源码包 SHA-256 为 `de50b3691231140098205ffe073f928dd57deb158d47d78dbde5ad70b39b295f`。
- 适配路径：路径 A；包含一个仅在 OHOS 编译条件下跳过上游 RLIMIT_CPU 测试的可审查补丁，没有新增知识库扩展。
- 配方使用 Conan 编译器配置调用上游 `make`，在 `can_run(self)` 时执行上游测试。

## 验证

- 上游：适配后 384/384 通过；原始上游为 385 个运行时 test invocations，唯一跳过的是依赖 `RLIMIT_CPU`/信号行为的 `forking_privilege_drop_cpu_limit__slow`。
- 消费者：1/1 通过，调用 `theft_hash_onepass`。

宿主机首次运行出现 384/385，但该次结果不作为豁免。设备日志定位到 `forking_privilege_drop_cpu_limit__slow` 在 `Fibonacci(967)` 长时间运行；独立 OHOS 探针设置 `RLIMIT_CPU=1` 后由外部 5 秒 timeout 以 137 结束，证明上游所需的 CPU 限制行为不可用。因此只在 `__OHOS__` 条件下跳过该测试，并保留其余上游测试。

## Conan 包接口

- 静态库：`theft`。
- CMake target：`theft::theft`。
- 系统链接依赖：`libm`。
