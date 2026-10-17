# libfuse for HarmonyOS (OpenHarmony)

## 概述

libfuse（FUSE，Filesystem in Userspace）的参考实现在 HarmonyOS/OpenHarmony
(aarch64) 上的编译指南和适配记录。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | libfuse (fuse3) |
| 最新适配版本 | 3.16.1 |
| 下载地址 | https://github.com/libfuse/libfuse/releases/download/fuse-3.16.1/fuse-3.16.1.tar.gz |
| 官方文档 | https://github.com/libfuse/libfuse |
| 许可证 | LGPL-2.1 (library), GPL-2.0 (utilities) |
| 构建系统 | Meson (3.x) / Autotools (2.x) |

## 鸿蒙环境

| 项目 | 值 |
|------|-----|
| SDK | ohos-sdk 26.0.0.18 |
| 架构 | aarch64 |
| 编译器 | clang 15.0.4 (LLVM) |
| Meson | 1.11.0 (3.x) |
| Ninja | 1.13.1 |

## 已适配版本

- [3.16.1](./3.16.1/) — 已适配（Meson，含 pthread_cancel 缺失的等价实现；`status: built`，待 CI 上传后转 published）
- [2.9.9](./2.9.9/) — 已归档（Autotools，`--disable-example` 绕过 pthread_cancel）
- 3.18.2 — 未通过（`status: failed`：混用了 BSD 挂载后端且未处理 pthread_cancel，导致 `unmount` / `pthread_cancel` 未定义；保留目录仅作历史记录）

## 关键适配点

1. **`host_machine.system()` 返回 `harmonyos`**：上游用
   `host_machine.system().startswith('linux')` 选择挂载后端，OHOS 上条件不成立，
   会错误地选到 `mount_bsd.c`；须把 `harmonyos` 视同 Linux（E090）。
   这是 3.18.2 失败的根因之一（连带 `unmount` 未定义）。
2. **`pthread_cancel` 家族缺失**：OHOS musl libc 既不声明也不导出
   `pthread_cancel` / `pthread_setcancelstate` / `pthread_setcanceltype` /
   `pthread_testcancel`（E085）。3.16.1 的做法是 meson 侧
   `cc.has_function('pthread_cancel')` 探测 + C 侧 `#ifdef` 守卫，
   缺失时用**退出标志 + 有界 poll** 替代，而不是空壳 stub。
3. **meson 布尔 `configuration_data` 生成无值 `#define`**：为真时写出
   `#define HAVE_X`（无值），为假时写出 `#undef HAVE_X`，因此守卫只能用
   `#ifdef`/`#ifndef`；写成 `#if HAVE_X` 在探测为真时会预处理报错。
4. **`close(fd)` 不能唤醒阻塞的 `read()`**：所以「关掉 channel fd 让 worker 退出」
   的死锁式兜底方案行不通；3.16.1 改为有界 `poll()` + 对 `se->fd` 置
   `O_NONBLOCK` + 处理 `-EAGAIN`。
5. **无 `/dev/fuse`**：OHOS 用户态不提供 FUSE 设备节点，无法真正挂载文件系统，
   上游所有功能测试都无法运行（详见各版本 `notes.md` 的 R51 清点表）。
6. **dl/rt 库**：OHOS 中已集成到 libc，无需额外链接。
7. **udev / util 工具**：`fusermount`、`mount.fuse` 依赖 `/etc/mtab` 与 udev 规则，
   需要 setuid/root，3.x 适配中以 `-Dutils=false` 关闭。

## 经验总结

1. OHOS 的 meson 交叉编译由 Conan `MesonToolchain` 自动生成 cross file，无需手写。
2. `validate()` 必须把 `"OHOS"` 加进接受的操作系统列表，并使用
   `in ("Linux", "OHOS")` 形式（R32）。
3. 库类包必须按 R26 默认静态（`default_library=static`），避免污染设备 `/lib`。
4. test_package 应调用真实的 libfuse API 以验证链接与运行期行为，而不是只打印字符串。
5. 上游 3.x 从未发布过 `3.16.0`，版本确认前应先枚举 GitHub releases/tags。

## 参考资料

- 源码仓库: https://github.com/libfuse/libfuse
- FUSE 协议与内核接口: https://www.kernel.org/doc/html/latest/filesystems/fuse.html
- 知识库: E085（musl 缺 pthread_cancel）、E090（meson host_system 不匹配 harmonyos）
