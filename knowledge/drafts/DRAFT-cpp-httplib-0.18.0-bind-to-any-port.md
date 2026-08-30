# DRAFT-cpp-httplib-0.18.0-bind-to-any-port - cpp-httplib test_package 中 bind_port() 不存在，需用 bind_to_any_port() 获取已绑定端口

> 正式编号未分配；合并/提升时由知识库维护流程分配下一个可用 E###。
> 来源：cpp-httplib 0.18.0 Path B 知识草稿（R02），基于 cpp-httplib-0.18.0-r01-bootstrap-and-adapt-pc1-60-20260829T153115Z 首轮真实适配问题。

## topic

在编写 cpp-httplib 0.18.0 的 test_package 消费者测试时，尝试用
`Server::bind_to_port(host, 0)` + `Server::bind_port()` 绑定任意端口并读取
实际端口号，编译失败：`httplib::Server` 没有 `bind_port()` 成员。

## error_signature

首次 `conan create` 的 test_package 编译阶段报错：

```text
/path/.../test.cpp:18:20: error: no member named 'bind_port' in 'httplib::Server'
    int port = svr.bind_port();
               ~~~ ^
1 error generated.
make[2]: *** [CMakeFiles/test_cpp_httplib.dir/build.make:79: ...] Error 1
ERROR: cpp-httplib/0.18.0 (test package): Error in build() method, line 29
	cmake.build()
	ConanException: Error 2 while executing
```

## root_cause

cpp-httplib 0.18.0 的 `httplib::Server` 并没有 `bind_port()` 这个成员方法。
可用的端口绑定 API 是：

- `bool bind_to_port(const std::string &host, int port, int socket_flags = 0)` —— 绑定到指定端口，返回 bool；
- `int bind_to_any_port(const std::string &host, int socket_flags = 0)` —— 绑定到系统自动分配的任意端口，直接返回实际端口号（int）；
- `bool listen_after_bind()` / `bool listen(host, port, ...)`。

在本地起一个 Server 做真实 HTTP 往返测试时，常希望绑定到自动分配的端口
再拿回端口号用于 Client 构造。若按"bind + 读端口"的通用思路去找
`bind_port()`，该符号不存在，编译直接失败。

## solution

改用 `bind_to_any_port()`，它在绑定后直接返回可用端口号：

```cpp
httplib::Server svr;
svr.Get("/ping", [](const httplib::Request &, httplib::Response &res) {
    res.set_content("pong", "text/plain");
});

int port = svr.bind_to_any_port("127.0.0.1");   // 返回自动分配的端口
if (port <= 0) { /* 绑定失败 */ return 1; }

std::thread th([&]() { svr.listen_after_bind(); });
// ...
httplib::Client cli("127.0.0.1", port);
if (auto res = cli.Get("/ping")) { /* 校验 status==200 && body=="pong" */ }

svr.stop();
th.join();
```

## evidence

- 首次失败：`conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64`，
  退出码 1，test_package 编译阶段报 `no member named 'bind_port' in 'httplib::Server'`。
- 修改 test_package/test.cpp 为 `bind_to_any_port()` 后重跑同一命令，退出码 0。

## verification

- 修复后 `conan create` 全流程通过（os=OHOS arch=armv8 clang 15 libc++ cppstd=17，
  ohos-aarch64 profile）。
- 包引用：`cpp-httplib/0.18.0#0ee6ed5bef721ec833693bf736a4af61:da39a3ee5e6b4b0d3255bfef95601890afd80709#7089347df6b29fe8d2b87f96d38e659b`。
- test_package 消费者测试运行输出：`cpp-httplib test PASSED: GET /ping -> 200 'pong'`。

## applicability

- 适用：任何需要让 `httplib::Server` 绑定到系统自动分配端口并获取该端口
  的消费者测试/样例代码（本地 HTTP 往返验证）。
- 边界：不涉及 `bind_to_port(host, 固定端口)` 的固定端口用法；也不涉及
  HTTPS（`SSLServer`）场景，但端口获取语义一致。
- 本条目只描述 cpp-httplib 0.18.0 的 API 事实，不涉及其他库。

## recovery_condition

- 若再遇 `no member named 'bind_port' in 'httplib::Server'`：把
  `bind_to_port(host, 0)` + 读取端口的方式替换为 `bind_to_any_port(host)`，
  用其返回值构造 Client 即可。
- 前提：bind 成功返回 >0 的端口；绑定失败时 `bind_to_any_port()` 返回
  非正数需做失败处理。
