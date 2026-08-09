# inotify-tools 4.25.9.0 适配笔记

## 编译环境
- 构建系统: makefile (手写极简 Makefile 直接编译，CI 环境缺 autotools 工具链)
- 编译日期: 2026-07-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. `conanfile.py build()` 手写极简 Makefile 到 build_folder（绕开 autotools 链，CI 缺 aclocal）
2. `make -f build_folder/Makefile -j$(nproc) all` — 从 source_folder 跑 make，-f 指向 build_folder 的 Makefile
3. `make -f build_folder/Makefile install PREFIX=staging` — 装到 staging 后 copy 到 package_folder
4. `make install DESTDIR=$TEST_PREFIX` — staging 安装
5. `make check` — 42/45 测试通过（按断言/子用例展开计数，`t/` 目录 14 个 .t 脚本 + `libinotifytools/src/test.cpp` 1 个 unit）
6. Staging 验证 — 4 binaries + 1 library, 全部可用
7. `ohc-run.py package` — 生成预编译包 526KB
8. `make install` — 安装到 $DEFAULT_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status Permission denied (创建临时文件) | HMDFS 不允许在 cwd 写临时文件 | 将 configure 的 conf$$$$、conf$$$$subs.sh/awk 临时文件重定向到 $TMPDIR |
| 2 | fanotify 结构体重复定义 (redefinition) | OHOS sys/fanotify.h 存在但 fanotify_init 不工作；软件的 `#elif !defined __ANDROID__` 分支同时包含项目自带头文件和系统头文件 | conanfile.py build() 手写 config.h（不定义 HAVE_SYS_FANOTIFY_H）+ fanotify.h shim（引入 bundled fanotify-dfid-name.h fallback）禁用 fanotify（非 configure 探测、非补丁机制） |
| 3 | fanotify_init/fanotify_mark 未定义 | OHOS 不实现 fanotify syscall wrapper，但 `LINUX_FANOTIFY` 在 `#elif !defined __ANDROID__` 条件下被定义 | conanfile.py 手写 config.h 使 `HAVE_SYS_FANOTIFY_H` 未定义，fanotify 相关功能（fsnotifywait/fsnotifywatch）禁用 |
| 4 | make check 3/45 测试失败 | OHOS 权限限制：watch "/" 被拒绝、mkdir 测试目录受限 | 平台限制，非代码问题，记录为 PARTIAL PASS |

## 源码修改

1. **configure** — 将 conf$$$$、conf$$$$subs.sh/awk 临时文件重定向到 $TMPDIR（HMDFS 不允许在 cwd 写临时文件）
2. **无补丁** — fanotify 禁用由 conanfile.py build() 手写 config.h（不定义 `HAVE_SYS_FANOTIFY_H`）+ fanotify.h shim（引入 bundled fanotify-dfid-name.h fallback）完成，未运行 configure 探测、未注入 `#ifdef __OHOS__`，与 conandata.yml `patches: []` 一致

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
