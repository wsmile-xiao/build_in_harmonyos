# inotify-tools — OpenHarmony 编译档案

## 软件简介
inotify-tools 是一个 C 语言库和一套命令行程序，用于提供 Linux inotify 文件系统事件监控接口。

## 功能概述
- inotifywait：等待文件系统事件
- inotifywatch：统计文件系统事件的频率
- libinotifytools：C 语言库，简化 inotify 接口使用

## OHOS 适配要点
- conanfile.py build() 手写极简 Makefile 直接编译（CI 缺 aclocal，上游 autotools 链不可用），未运行上游 configure
- 依赖 Linux inotify 内核接口，OHOS 内核兼容
- **已知限制**：OHOS 上 fanotify_init()/fanotify_mark() syscall 未实现（E051 类问题），fanotify 功能已由 conanfile.py 手写 config.h（不定义 HAVE_SYS_FANOTIFY_H）+ fanotify.h shim（bundled fallback）禁用（非 configure 探测、非补丁机制）。上游仅提供 inotifywait/inotifywatch 两个工具（无 fsnotifywait/fsnotifywatch），fanotify 特有监控能力（如 FAN_OPEN_PERM 权限事件）不可用。

## 依赖关系
- 无外部依赖（仅依赖 libc）

## 参考资料
- [inotify-tools GitHub](https://github.com/inotify-tools/inotify-tools)
- [inotify(7) man page](https://man7.org/linux/man-pages/man7/inotify.7.html)
