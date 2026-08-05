# libassuan 3.0.2 适配说明

## 基线

- 官方源码: `https://gnupg.org/ftp/gcrypt/libassuan/libassuan-3.0.2.tar.bz2`
- SHA-256: `d2931cdad266e633510f9970e1a2f346055e351bb19f9b78912475b8074c36f6`
- 构建系统: Autotools
- 许可证: LGPL-2.1-or-later
- 依赖: `libgpg-error/1.55`

## OpenHarmony 适配

- 使用 `aarch64-unknown-linux-musl` 作为设备原生构建 triplet，使上游 Linux/POSIX 路径与 musl ABI 保持一致。
- 显式关闭文档构建，避免引入 Texinfo 等非目标主机工具依赖。
- 使用 Conan 依赖前缀和 `gpgrt-config` 查找 `libgpg-error`。
- 通过 Conan target `libgpg-error::libgpg-error` 传播依赖，`libassuan::libassuan` 消费者无需了解 Conan cache 路径。
- 在配置探针和上游测试期间把 Conan 依赖库目录加入 `LD_LIBRARY_PATH`，确保设备能加载 `libgpg-error.so.0`。
- 将源码复制到设备本地 `/data/storage/el2/base/cache`，并在独立 `build/` 子目录执行 VPATH 构建，避免 `configure`、`config.status`、FIFO 和 Unix socket 落到共享 `/storage`。
- 设备本地目录由当前 Conan create 的 `build_folder` 与 `package_folder` 完整路径摘要唯一确定；build 阶段完成测试和 staged install，package 阶段复制 staging 后清理。
- 仅接受 Conan `os=OHOS, arch=armv8`，避免固定 arm64 musl triplet 与包 ID 不一致。
- 通过可审查补丁让上游 fd-passing shell 测试使用设备 Bash，并把路径型 Unix socket 放到设备本地 cache；共享 `/storage` 文件系统不允许 `AF_UNIX` bind。

## 测试

- 配方在构建后执行上游完整 `make -j1 check`。
- 上游测试覆盖版本检查、pipe client/server IPC，以及平台支持时的 fd passing。
- `test_package` 额外通过 `socketpair` 和 `fork` 建立真实 Assuan 客户端/服务端，验证 `ECHO` 数据事务与 `BYE` 关闭流程。
- socket-FD 消费者显式忽略 `SIGPIPE`，使 peer 关闭时由 libassuan 返回错误而不是终止应用进程。
- 版本 manifest 按仓库 schema 只统计上游官方测试 4/4/0；消费者另计 1/1，通过一个完整 ECHO/BYE 事务验证，不声明无法稳定逐项核对的 assertion 数。

## 状态

设备完整 CI 已通过，当前状态为 `built`；尚未上传 Conan 制品或推送最终交付分支。
