# spice

SPICE（Simple Protocol for Independent Computing Environments）远程桌面协议的 **server 侧实现库**（libspice-server）——供虚拟化管理器（QEMU / 独立 server 进程）通过 SPICE 协议向客户端提供远程显示、键盘鼠标与外设通道。

- 上游：https://www.spice-space.org/ （spice-server 0.16.0，LGPL-2.1）
- 构建：meson（C + C++；tarball 内置 spice-common subproject 实体目录，无子模块网络拉取）
- 产物：`lib/libspice-server.so`（单一无版本文件，SONAME 同名）+ `include/spice-server/*.h` + `spice-server.pc`
- 依赖（全部 Conan 制品）：glib / pixman / openssl / libjpeg-turbo / zlib / lz4 / spice-protocol

## OHOS 适配要点（跨版本通用）

1. **单一无版本共享库**：hmdfs 家目录禁止符号链接（`ln -s` EPERM），meson 检测后打印 "Skipping all symlinking" 并跳过全部符号链接，versioned 目标只剩 `libX.so.a.b.c` 本体、缺 `.so` 开发链接，消费者（CMakeDeps `find_library`、链接器 `-lspice-server`）无法解析。平台规范（`no-versioned-soname.cmake`：每个已发布 OHOS 库都是单一无版本文件）即去掉版本化命名；本包以补丁去掉 `library()` 的 `version` 参数达成。cmake 侧等价物：`-DCMAKE_PLATFORM_NO_VERSIONED_SONAME=ON`（先例 libwebp）。
2. **AF_UNIX 方言**：OHOS 对 AF_UNIX socket 的 `IPPROTO_TCP` 选项返回 `ENOPROTOOPT`（keepalive 容错集合需覆盖，`red_socket_set_no_delay` 已有同款先例写法）；hmdfs 不支持路径式 unix socket（`bind` 返回 EPERM，`/tmp` 只读），测试回退抽象命名空间（`@` 前缀，`reds_init_socket` 原生支持）。
3. **shebang 脚本不可直接 execve**（EACCES）：meson `run_command` 与 `glib-mkenums` 均以显式解释器执行（`sh script` / `[python3, script]`，先例 glib）。
4. **构建期 python 依赖**：spice-common 代码生成与 python-checks 需要 `pyparsing`，以第二源固定 2.4.7 sdist + `PYTHONPATH` 注入（不依赖宿主环境）。
5. **重签名**：`package()` 后对 `lib/**/*.so*` 走 `binary-sign-tool` 自签（先例 glib）。
6. **消费者依赖传播**：本平台 conan `requires` 默认不向消费者传递静态库与 header-only 依赖（consumer 侧 CMakeDeps 只生成共享依赖 target）；公共头链引用的包（如 spice-protocol，`<spice/qxl_dev.h>` 被 `spice-core.h` 包含）须在配方显式声明 `transitive_headers=True / transitive_libs=True`（平台惯例，全仓 412 处同款）。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|------|------|------|------|
| 0.16.0 | built | 2026-10-03 | 真机 conan-verify 全门禁通过（meson 23/23 + test_package 22 断言） |
