# winregfs —— Windows 注册表 FUSE 文件系统

[winregfs](https://codeberg.org/jbruchon/winregfs) 把 Windows NT 注册表 hive
文件（如 `SYSTEM`、`SOFTWARE`、`NTUSER.DAT`）以普通目录树的形式挂载出来，
让 shell 脚本可以直接读写注册表键值，而不必导出/解析 `.reg` 文本。
它把 chntpw 的 `ntreg.c` 注册表库与 FUSE 粘合在一起。

## 产物

| 工具 | 用途 |
|------|------|
| `mount.winregfs` | 通过 FUSE 把 hive 挂载为目录树（读写，值大小上限 8192 字节） |
| `fsck.winregfs`  | 递归遍历 hive 的全部键与值并报告损坏（偏移/类型错误） |

## OHOS 适配要点

- 依赖 FUSE 2.x API（`FUSE_USE_VERSION 26`），使用 `libfuse/2.9.9`。
- OHOS 的 libfuse 包不提供 `fuse.pc`，上游 `pkg-config fuse` 取不到路径；
  补丁让 Makefile 支持从外部注入 `FUSE_CFLAGS`/`FUSE_LDFLAGS`。
- OHOS musl libc 不导出 POSIX 线程取消 API（`pthread_cancel` 等），
  而 `libfuse.a` 会引用它们；补丁提供 `pthread_compat.c` 兼容实现（知识库 E085）。

详见该版本目录下的 [`notes.md`](0.8/notes.md)。
