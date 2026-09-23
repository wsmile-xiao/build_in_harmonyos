# Broker

Broker（Zeek 消息代理）实现进程内 pub-sub 消息总线：endpoint 提供发布/订阅与
数据存储（master/clone）抽象，网络层基于 CAF（C++ Actor Framework）。

## HarmonyOS 适配

- C++17 / CMake 构建；发布 `libbroker` 静态库（默认）与公共头文件。
- CAF 按上游默认方式随 broker 捆绑构建（`add_subdirectory(caf)`）：v1.4.0
  将 zeek/actor-framework 固定提交作为 `caf/` 子模块，其源码树与上游 CAF
  0.17.6 发布版本逐字节一致（树 diff 验证 0 差异）。制品仓已发布的
  actor-framework/0.17.6 配方固定 `CAF_NO_OPENSSL=ON` 且缺少 broker 需要的
  `openssl`/`test` 组件，因此本配方不采用该包。
- GitHub tag 压缩包不含子模块内容，配方补充官方子模块源归档（caf、zeek/cmake、
  zeek-3rdparty）并合并到源码树。
- 上游 C++ 测试套件（`tests/cpp/`，CTest 注册）在构建阶段执行；测试与新增
  消费者测试详见 `test_package/`。

## 依赖

- `openssl/3.5.8.1`（broker 与 libcaf_openssl 使用）

## 参考

- https://github.com/zeek/broker
- https://github.com/zeek/actor-framework
