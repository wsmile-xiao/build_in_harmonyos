# qpid-proton

Apache Qpid Proton is a lightweight, high-performance AMQP 1.0 messaging
library. The C library provides the message/type codecs and engine
(`libqpid-proton-core`), the messenger and reactor APIs plus the non-blocking
epoll proactor (`libqpid-proton-proactor`, both also folded into the legacy
`libqpid-proton`).

- 上游: https://github.com/apache/qpid-proton （tag `0.38.0`）
- 许可证: Apache-2.0
- 构建系统: CMake
- 依赖: `openssl/3.5.8.1`（静态链接，TLS 支持）

## OHOS 适配要点

- **CMake 平台**：CMake 4.1 无 `Platform/HarmonyOS.cmake`，`CMAKE_SYSTEM_NAME` 别名到 `Linux`
  （否则不产生 `DT_SONAME`、`DT_NEEDED` 记构建路径、导出配置带 `IMPORTED_NO_SONAME`）；
  同时清空 `LIB_SUFFIX` 保证装到 `lib/`。
- **SONAME**：`CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE`，保留不带动版本的 `DT_SONAME`，不生成 `.so.N` 软链。
- **epoll 语义**：HarmonyOS 的 epoll 不支持 `EPOLLONESHOT`，会令 proactor 轮询自旋不返回；
  `patches/0001` 用 `EPOLL_CTL_MOD(events=0)` 在投递后立即"单次化"补上该语义。
- **签名**：OHOS 加载时校验 ELF `.codesign`，而 CMake install 会重写依赖树内库的 RUNPATH
  使签名失效；配方在 `package()` 里重签 `lib/*.so`。
- **-Werror**：关闭上游默认的 `ENABLE_WARNING_ERROR`（上游对 Darwin 亦如此）。
- 包内不含可执行文件；`find_package(Proton)` 可用 `lib/cmake/Proton/ProtonConfig.cmake`，
  亦可用 `pkg-config libqpid-proton`。下游（如 openmama 的 `cmake/FindProton.cmake`）设
  `PROTON_ROOT` 指向包目录即可按 `include/`、`lib/` 命中。

## 版本

- 0.38.0: 初次适配（上游 0.38.0，2026-09-21）。上游 ctest 注册 11 条目 9 通过，
  2 条失败均为上游内置测试证书 2025-11-24 过期（与平台无关，详见版本 notes.md）。
  test_package 13/13 通过。
