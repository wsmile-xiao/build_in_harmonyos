# vali

Varlink 协议的纯 C 实现 + 接口代码生成器，由 [emersion](https://emersion.fr/)
（Simon Ser，freedesktop 系——wayland、mako、wlsunset 等项目的作者）维护。
Varlink 是一种基于 Unix socket 的点对点 IPC/RPC 协议，报文是 JSON，接口用
`.varlink` 接口定义文件描述。

vali 提供：

- **客户端**：`vali_client_connect_unix()` / `vali_client_connect_fd()`，
  同步调用 `vali_client_call()`、多回复调用 `vali_client_call_more()` /
  `vali_client_call_wait()`、单向调用 `vali_client_call_oneway()`
- **服务端**：`vali_service_create()`，可监听 Unix socket 或接管已有 FD
  （`vali_service_listen_fd()` / `vali_service_create_conn()`），
  由调用方驱动事件循环 `vali_service_dispatch()`
- **接口注册表**：`vali_registry_*`，按接口名分发方法调用，并自动实现
  `org.varlink.service` 标准接口
- **代码生成器 `vali`**：把 `.varlink` 接口定义转成带类型检查的 C 客户端/
  服务端桩代码

- 上游：https://gitlab.freedesktop.org/emersion/vali
- 构建：Meson（`meson setup build && ninja -C build`）
- 依赖：json-c（报文编解码）、aml（事件循环）
- 许可证：MIT
- 测试：`test/meson.build` 注册 2 条 —— `basic`（fork + socketpair 的
  客户端/服务端往返）与 `certification`（Varlink 官方认证套件，`self-test` 模式）

## OHOS 适配

- **零补丁**：上游源码一行不改。两个真正的移植障碍都在 `conanfile.py` 的
  `generate()` 里解决，不改动上游：
  1. **json-c 头目录**：上游写 `#include <json_object.h>` 这类顶层兼容头，
     而 json-c 官方 CMakeLists 只把 16 个头装到 `include/json-c/`（顶层那批是
     Debian/Alpine 的 `json-c-dev` 打包时补的符号链接）。配方补一个
     `-I<json-c>/include/json-c`。
  2. **NDEBUG**：上游 `test/basic.c` 在 NDEBUG 下主动失败
     （`#ifdef NDEBUG` → 打印提示并 `return 1`）；CI profile 是
     `build_type=Release`，Meson 会定义 NDEBUG。配方显式把 meson 的
     `b_ndebug` 覆写为 `false`。
- **构建工具**：基础镜像与 CI 环境都没有 meson（`command -v meson` 为空），
  `tool_requires("meson/1.11.0")` 引入。
- **依赖**：全部经 conan pkg-config 提供（`json-c.pc` / `aml1.pc`），
  并保持 `wrap_mode=nodownload` —— 上游 `subprojects/aml.wrap` 是
  `[wrap-git] revision = HEAD`，一旦走 subproject 回退就会去 clone 上游 HEAD。
- **上游测试真实执行**：不裁剪 test/，`build()` 内跑 `meson test -v`，
  2 条测试的结果进入 `conan create` 日志。上游测试**零修改**。
- **构建期自举**：上游用 `custom_target` 调用刚编译出的 `bin/vali` 生成
  `org.varlink.service.{h,c}`。本例是原生构建（OHOS aarch64 上直接编译运行），
  所以这条路径可用；交叉编译场景需要另行提供可执行的 tool。
- **包内清理**：删除上游安装的 `lib/pkgconfig/vali.pc` —— 它的 prefix 是构建期
  根目录（conan 用 `--prefix=/` 配 meson），且 `Requires` 只声明 json-c、
  漏掉静态链接真正需要的 aml。

## References

- https://gitlab.freedesktop.org/emersion/vali
- https://varlink.org/ — Varlink 协议规范
- https://gitlab.freedesktop.org/emersion/dalligi — 上游用的 CI 模板
