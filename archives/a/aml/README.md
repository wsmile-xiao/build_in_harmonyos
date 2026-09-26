# aml

aml — Another Main Loop：一个小型 C 主循环/事件循环库（ISC 许可）。
上游仓库：https://github.com/any1/aml ，版本 1.0.0（tag v1.0.0）。

## 依赖

- 运行期：无外部 Conan 依赖（仅系统 libc / pthreads / librt）
- 构建期：meson、ninja、clang（OHOS SDK 15.0.4）

## OHOS 适配要点

- Meson 构建（`meson.build` → `libaml.so` / `libaml.a`），公共头文件安装到 `include/aml1/aml.h`，pkg-config 名 `aml1`
- 后端自动探测：`sys/epoll.h` 存在则选 epoll 后端，否则 kqueue
- 补丁 0001：meson 特性检测 `cc.has_function('pthread_setcancelstate')`，仅在可用时注入 `-DHAVE_PTHREAD_SETCANCELSTATE`
- 补丁 0002：`src/thread-pool.c` 的 `pthread_setcancelstate` 调用加特性检测守卫（OHOS libc 无该符号，与 Android 情况类似；保留上游 `__ANDROID__` 守卫，未硬编码平台宏）
- 消费者测试 `test_package/test.c`：调用公共 API `aml_new`/`aml_ticker_new`/`aml_start`/`aml_run`/`aml_exit`/`aml_version`，验证事件循环与 ticker 回调真实触发

## 版本索引

| 版本 | 状态 | 构建日期 | 备注 |
|------|------|----------|------|
| 1.0.0 | published | 2026-09-24 | 首次适配（见 `1.0.0/notes.md`） |
