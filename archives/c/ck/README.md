# ck

Concurrency Kit (ck) — 并发原语、安全内存回收与非阻塞数据结构的 C 库
（BSD-2-Clause）。上游 http://concurrencykit.org 。

- 上游: https://github.com/concurrencykit/ck
- 版本目录: 0.7.2/（静态/动态库 libck；无命令行工具）
- 平台适配: configure 的 `uname -s` 白名单补入 HarmonyOS（知识库 E160 类），
  详见 0.7.2/notes.md 与 patches/0001-configure.patch
