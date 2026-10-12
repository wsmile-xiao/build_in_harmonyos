# sems-gsm

SEMS（SIP Express Media Server，SIP 媒体服务器）+ GSM 06.10 编解码插件
（上游 `core/plug-in/gsm`）。上游 2.1.0 起由 Makefile 全面迁移到 CMake。

## Homepage
https://github.com/sems-server/sems

## License
GPL-2.0-or-later

## Build System
CMake（上游 2.1.0 起）

## 交付物
- `lib/sems/plug-in/gsm.so` —— 本任务目标：GSM 06.10 编解码插件
- `lib/sems/plug-in/*.so` —— 其余 38 个插件（ann_b2b、sbc、registrar、dsm、wav、voicebox 等）
- `sbin/` —— `sems` 主程序与 23 个运维工具（sems-stats、sems-list-calls、sems-sbc-* 等）

## Dependencies
- `libgsm/1.0.18` —— GSM 06.10 编解码（gsm 插件链接；已在制品仓发布）
- `libevent/2.1.13` —— 核心必需（AmRtpSocket 等；已在制品仓发布）

## OHOS Adaptation
- musl 无 `libresolv`：`res_search` 在 libc 内，去掉无条件 `-lresolv`
- musl 不实现 `pthread_cancel`：`AmThread::cancel()` 改为协作式停止（`_stopped` 标志）
- 上游 `FindLibevent2` 找到库但未 `include_directories` → patch 补 include path
- `xmlrpc2di` 捆绑的 xmlrpc++ 无条件包含 OpenSSL 头（上游守卫不完整）→ 以
  `EXCLUDE_APP_MODULES=xmlrpc2di` 排除（gsm 插件不需要）
- `SEMS_DOC_PREFIX`/`SEMS_RUNDIR_PREFIX` 默认指向 `/usr/share`、`/var`，包内重定向
- 最小化构建面：`SEMS_USE_PYTHON/SPANDSP/OPUS/MP3/ILBC/MONITORING=OFF`

## 验证
- 上游测试（R51）：`core/tests` 构建为 `sems_tests`，ctest 注册 1 项 → **1/1 Passed**
- 消费者测试（R34）：`test_package` dlopen 包内 `lib/sems/plug-in/gsm.so`
  （RTLD_NOW|RTLD_GLOBAL，加载器同机制）、dlsym 插件 ABI 入口 `amci_exports`
  与包内编解码符号、跑真实 GSM 06.10 往返；并冒烟运行包内 `sbin/sems -v`

## 已知限制
- `xmlrpc2di` 插件被排除（其捆绑 xmlrpc++ 需 OpenSSL；如需可补 `openssl` 依赖再放开）
- Rust 监控工具未编译（CI 无 Rust 工具链；上游自动回退 Python wrapper）
- `AmThread::cancel()` 在 OHOS 为协作式停止，对 gsm 编解码路径无影响
