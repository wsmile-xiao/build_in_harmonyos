# tracy（HarmonyOS PC 适配）

[Tracy](https://github.com/wolfpld/tracy) 是一个实时帧剖析器（frame profiler）。
本目录收录其**客户端库**（`TracyClient`）在 HarmonyOS PC（OpenHarmony, aarch64）
上的适配配方。

- 归档版本：`0.13.1`（`archives/t/tracy/0.13.1/`）
- 上游源：https://github.com/wolfpld/tracy/archive/refs/tags/v0.13.1.tar.gz
  （sha256 `d4efc50ebcb0bfcfdbba148995aeb75044c0d80f5d91223aebfaa8fa9e563d2b`）
- 依赖：无第三方 Conan 依赖；系统库 `pthread`、`dl`（由 OHOS sysroot 提供）
- 构建系统：CMake（仅构建 `TracyClient`，不构建 profiler GUI）
- 产物：`lib/libTracyClient.a` 静态库 + `<prefix>/include/tracy/{tracy,client,common}/**.h`
- 补丁：2 个 libc 探针补丁（musl/OHOS 缺少线程取消 API 与 `program_invocation_*`），
  详见 `0.13.1/notes.md` 与 `0.13.1/conandata.yml`
- 消费者用法：`#include <tracy/TracyC.h>` 或 `#include <tracy/Tracy.hpp>`；
  必须定义 `TRACY_ENABLE`（配方已通过 `cpp_info.defines` 自动导出）
