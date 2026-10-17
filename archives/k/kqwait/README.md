# kqwait — OpenHarmony 编译档案

## 软件简介
kqwait 是一个 BSD 系统上的命令行工具，等待文件或目录的变化事件（kqueue EVFILT_VNODE），事件发生后打印变化的路径并退出。

## 功能概述
- `kqwait <file>` — 等待文件被写入，打印文件路径
- `kqwait <dir>` — 等待目录内容变化，打印 dirinfo 前后差集（`+ path/name` / `- path/name`）
- `-d` 调试输出 / `-v` 版本 / `-h` 帮助

## OHOS 适配要点
- **平台能力**：OHOS（HongMeng 内核 + musl libc）无 kqueue/kevent/EVFILT_VNODE（sysroot 无 `sys/event.h`，libc 无相关符号），不可编译期 shim、不可运行期模拟 —— 唯一忠实路径是 inotify 重写
- **适配方式**：`patches/kqwait-ohos-inotify-port.patch` 将事件源替换为 inotify，语义映射：
  - `NOTE_WRITE` → `IN_MODIFY|IN_CREATE|IN_DELETE|IN_MOVED_FROM|IN_MOVED_TO`
  - `NOTE_DELETE` → `IN_DELETE_SELF`（watch 路径自身被删）
  - `NOTE_RENAME` → `IN_MOVE_SELF|IN_MOVED_FROM|IN_MOVED_TO`
  - **注意**：inotify `IN_DELETE` 是目录内子项被删，走 dirinfo-diff 分支，不等于 kqueue `NOTE_DELETE`
- **额外修复**：上游 `getopt()` 返回值存 `char`，unsigned-char 平台（aarch64）死循环 → 改 `int`
- **版本注记**：上游 tag 内 `version.h` 为 `v1.0.2-1-g0425-dirty`（打包失误），构建时覆写为 `v1.0.3`
- CLI、stdout 格式、退出码与上游逐字节一致

## 依赖关系
- 无外部依赖（仅 libc）

## 测试
- 上游：`make test` = `prove -v t/kqwait.pl`（15 项断言，依赖 perl IPC::Run）→ 按 SPEC 3.3 豁免，断言 1:1 移植为 `t/run_upstream_tests.sh`，conanfile build() 执行，**15/15 PASS**（OHOS aarch64 真机）
- test_package：--help/-v 冒烟 + 单文件写等待 + OHOS 专项（目录 delete/create → dirinfo diff 断言）

## 参考资料
- [kqwait GitHub](https://github.com/sschober/kqwait)
- [kqueue(2) man page](https://man.freebsd.org/cgi/man.cgi?query=kqueue)
- [inotify(7) man page](https://man7.org/linux/man-pages/man7/inotify.7.html)
