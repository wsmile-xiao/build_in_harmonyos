# srs-state (srs-state-threads)

SRS 维护的 State Threads 协程库 fork（libst）：基于 SGI/Netscape Portable Runtime 的
用户态线程，提供协程调度、epoll 事件集成与非阻塞 TCP 原语，是 SRS 流媒体服务器的
调度底座。

- 上游: https://github.com/ossrs/state-threads/
- 版本: 1.9.5（tag v1.9.5）
- 许可: GPL-2.0-or-later OR MPL-1.1
- 构建系统: 纯 Makefile（linux-optimized / linux-debug-utest）
- 产物: libst.a / libst.so.1.9（SONAME libst.so.1）+ st.h
- 依赖: 仅 libc（无 Conan 依赖）

## OHOS 适配要点（详见 1.9.5/notes.md）

- OHOS `uname -r` 返回含空格字符串，TARGETDIR 须命令行覆盖（LINUX_OHOS_OPT/DBG）。
- clang 链接须用 `-Wl,-soname,libst.so.1` 替代上游裸 `-soname=`。
- aarch64 上下文切换汇编由上游 md_linux2.S 原生提供，无需改动。
