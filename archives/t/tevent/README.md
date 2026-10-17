# tevent

tevent 是 Samba 项目的事件循环库，提供文件描述符、定时器、信号、立即事件
（immediate）、队列（queue）等事件源的统一封装，并在其上实现异步请求框架
`tevent_req`。它是 Samba、tdb、ldb 以及大量 Samba 生态组件的基础运行时。

## 功能概述

- **事件循环**：epoll / poll / select / standard 多后端，`tevent_loop_once()`、
  `tevent_loop_wait()` 驱动。
- **事件源**：`tevent_add_fd()`、`tevent_add_timer()`、`tevent_add_signal()`、
  `tevent_create_immediate()`、`tevent_queue`。
- **异步请求框架**：`tevent_req` 状态机（`tevent_req_create/post/done/error`）。
- **调试与追踪**：`tevent_set_debug()`、trace callback（attach / before_handler /
  handler / detach 各阶段）。
- **talloc 集成**：所有对象挂在 `TALLOC_CTX` 层级下，随父对象一起释放。
- **线程支持**：`tevent_threads`（跨线程 immediate 投递）。

## OHOS 适配

- **构建方式**：上游 standalone tarball 使用 Samba waf，其 configure 探针
  依赖可写 `/tmp` 并要完整构建 `lib/replace`，在 OHOS worker 上不可用。
  本仓库改用 **direct-cc** 直接驱动 clang 编译 15 个 `tevent*.c`，宏集合
  固定写在 `conanfile.py` 的 `COMMON_DEFINES` 中。
- **lib/replace 兼容层**：tevent 依赖 `replace.h` 提供的若干宏。其中
  `strerror` 需要 `-DHAVE_STRERROR` 才不会走已废弃的 `sys_errlist[]`；
  `rep_memset_s()`（由 `ZERO_STRUCT`/`BURN_DATA` 展开而来）由
  `files/tevent_ohos_compat.c` 提供，因为上游 `lib/replace/replace.c`
  无法脱离 waf 生成的 `config.h` 单独编译。
- **后端**：OHOS 提供 `sys/epoll.h`，因此编译 `tevent_epoll.c` 并启用
  epoll 后端；`tevent_backend_list()` 中可见 `epoll`。
- **信号数**：`TEVENT_NUM_SIGNALS` 取 65（对应 OHOS 的 `_NSIG`）。
- **已知差异**：上游 `bindings.py`（pytevent CPython 扩展）未启用——本仓库
  只构建纯 C 静态库，OHOS 构建机上没有 Python 开发头。`test_req.c` /
  `testsuite.c` 虽在源码根目录，但未出现在上游 wscript 的构建/测试目标里，
  不算上游测试。

## 依赖关系

- **编译依赖**：`talloc/2.4.4`（`tevent.h` 公共头 include `<talloc.h>`，
  故声明为 transitive）。
- **运行依赖**：无（静态库；下游链接时需一并链接 talloc）。
- **构建期使用但不进包**：`third_party/cmocka`（上游单测框架，随 tarball 提供）。

## 为什么值得收进知识库

tevent 是 samba 家族三件套（talloc / tdb / tevent）里唯一带事件循环与
异步状态机的库，`sys_errlist` 遗留符号、`rep_memset_s` 宏展开、
`TEVENT_NUM_SIGNALS` 的运行时信号常量这三类问题在同类 autotools/waf
移植中会反复出现，具有普遍参考价值。

## 参考资料

- 官网：https://tevent.samba.org/
- 源码：https://download.samba.org/pub/tevent/
- API 文档：https://tevent.samba.org/tevent_8h.html
