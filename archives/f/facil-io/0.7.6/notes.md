# facil-io 0.7.6 适配笔记

## 编译环境
- 构建系统: cmake（上游 CMakeLists 极简：单静态库目标，无 install 规则）
- 编译日期: 2026-09-14
- 编译器: clang（OHOS aarch64 交叉工具链）
- 状态: built

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `cmake_minimum_required(VERSION 2.4)` 被 CMake 4.x 拒绝 | 上游 CMakeLists 声明的最低版本过低 | CMakeToolchain 变量注入 `-DCMAKE_POLICY_VERSION_MINIMUM=3.5` |
| 2 | 无 install 规则、目标名 `facil.io`（点号导致输出 `libfacil.io.a`，`-l` 无法链接） | 上游仅定义库目标未定义发布 | package() 手动打包：库改名 `libfacil.a`；头树 `lib/` 整体按相对路径拷入 `include/`；includedirs 复刻 CMake 的 7 个 PUBLIC 目录 |
| 3 | TLS 双实现文件同编 | `fio_tls_openssl.c` 有 `#if HAVE_OPENSSL` 守卫，未定义时为空编译 | 不注入 HAVE_OPENSSL，自然走 `fio_tls_missing.c` 等价空实现，无 OpenSSL 依赖 |

## 上游测试清点（R51 第一步）

- tests/ 目录为独立手工程序，上游 makefile 流程 `make test` 不被 CMake 注册；CMakeLists 仅构建库目标，无 CTest
- **上游静态测试数 N_static = 0**（如实申报，CMake 注册口径）

## 消费者测试（test_package，N_consumer = 1）

`test.sh` + `test.c`：以使用者身份编译并运行真实 HTTP 服务端/客户端回环——
工作线程 `http_listen("18472", "127.0.0.1", .on_request=...)` + `fio_start`，
主线程原生 socket 连接 127.0.0.1:18472 发 GET，断言响应含 `200` 与处理体
`facil-http-ok`（50 次重试容忍启动延迟）。

## 四维测试账本

| 维度 | 数值 | 来源 |
|---|---|---|
| 上游静态声明 N_static | 0 | CMake 注册口径清点 |
| 构建系统注册 N_registered | 0 | 无 CTest 注册 |
| 实际执行 N_executed | 0 | 无上游自动化套件 |
| 未执行分类 | 0 | — |
| 消费者测试 N_consumer | 1（链接+HTTP 回环断言） | test_package/test.sh |

## 源码修改

无补丁（patches: {}）。

## 依赖版本

无外部依赖（pthread/m 为系统库；OpenTLS 走空实现，无需 OpenSSL）。

## 路径 B 判断

- CMake 兼容与无 install 规则打包均为常见模式；无新错误签名。
- 结论：**纯路径 A，不申报路径 B**。

## 验证结果

（待 conan-verify / W3 运行后回填）
---

**编译结束**: 2026-09-14 03:31
**最终状态**: built
