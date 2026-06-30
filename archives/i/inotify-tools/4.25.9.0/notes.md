# inotify-tools 4.25.9.0 适配笔记

## 编译环境
- 构建系统: autotools (需先 autoreconf -fi)
- 编译日期: 2026-06-01
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `autoreconf -fi` — 生成 configure 脚本（GitHub tag tarball 不包含 configure）
2. `./configure --prefix=$DEFAULT_PREFIX` — 需要先移除 configure 和 config.status 中的 umask 077
3. `make -j1` — 编译
4. `make install DESTDIR=$TEST_PREFIX` — staging 安装
5. `make check` — 42/45 测试通过
6. Staging 验证 — 4 binaries + 1 library, 全部可用
7. `ohc-run.py package` — 生成预编译包 526KB
8. `make install` — 安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied (创建临时文件) | HMDFS 不允许 umask 077 创建临时目录 | 将 configure/config.status 中的 `umask 077` 改为 `umask 002` |
| 2 | fanotify 结构体重复定义 (redefinition) | OHOS sys/fanotify.h 存在但 fanotify_init 不工作；软件的 `#elif !defined __ANDROID__` 分支同时包含项目自带头文件和系统头文件 | 在 fanotify.h.in 中添加 `#elif defined(__OHOS__)` 分支，使用 `<linux/fanotify.h>` 代替 |
| 3 | fanotify_init/fanotify_mark 未定义 | OHOS 不实现 fanotify syscall wrapper，但 `LINUX_FANOTIFY` 在 `#elif !defined __ANDROID__` 条件下被定义 | 在 inotifytools.cpp 中添加 `#elif defined(__OHOS__)` 分支，不定义 LINUX_FANOTIFY |
| 4 | make check 3/45 测试失败 | OHOS 权限限制：watch "/" 被拒绝、mkdir 测试目录受限 | 平台限制，非代码问题，记录为 PARTIAL PASS |

## 源码修改

1. **libinotifytools/src/inotifytools/fanotify.h.in** — 添加 `#elif defined(__OHOS__)` 分支，使用 `<linux/fanotify.h>` 而不包含 `<sys/fanotify.h>` 避免结构体重复定义
2. **libinotifytools/src/inotifytools.cpp** — 添加 `#elif defined(__OHOS__)` 分支，不定义 `LINUX_FANOTIFY` 宏，禁用 fanotify 功能（OHOS 不支持 fanotify_init/fanotify_mark syscall）
3. **configure** — 将 `umask 077` 改为 `umask 002`（HMDFS 兼容性）

## 依赖版本

- 无外部依赖

## 验证结果

```bash
$ inotifywait -h
inotifywait 4.23.9.0
Wait for a particular event on a file or set of files.

$ inotifywatch -h
inotifywatch 4.23.9.0
Gather filesystem usage statistics using inotifywatch.

$ ls ~/usr/local/lib/libinotifytools.so*
libinotifytools.so -> libinotifytools.so.0.4.1
libinotifytools.so.0 -> libinotifytools.so.0.4.1
libinotifytools.so.0.4.1 (55616 bytes)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| inotify-tools-4.25.9.0-ohos-aarch64.tar.gz | 526KB | 预编译包 |

## 注意事项

- inotify-tools 是 Linux 特有的文件监控工具，依赖 Linux inotify syscall
- OHOS 支持 sys/inotify.h 且 inotify_init() 正常工作，inotify 核心功能可用
- OHOS 不支持 fanotify（fanotify_init/fanotify_mark syscall 未实现），fanotify 相关功能（fsnotifywait/fsnotifywatch）被禁用
- 内部版本号 4.23.9.0 与发布标签 4.25.9.0 不同，这是上游版本策略

---

**编译结束**: 2026-06-01
**最终状态**: published
---

**编译结束**: 2026-06-01 13:05
**最终状态**: published
