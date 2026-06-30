# inotify-tools

Linux 文件系统事件监控工具集，提供 `inotifywait` 和 `inotifywatch` 两个命令行工具，以及 `libinotifytools` 共享库供程序调用。

## 基本信息

| 项目 | 值 |
|------|-----|
| 版本 | 4.25.9.0 |
| 许可证 | GPL-2.0-or-later |
| 构建系统 | autotools |
| 语言 | C/C++ |
| 依赖 | 无 |
| 源码 | https://github.com/inotify-tools/inotify-tools/archive/refs/tags/4.25.9.0.tar.gz |

## OHOS 平台适配说明

### inotify 功能状态

- ✅ `sys/inotify.h` 存在且 `inotify_init()` 正常工作
- ✅ `inotify_add_watch` / `inotify_rm_watch` / `inotify_read` 正常可用
- ❌ `sys/fanotify.h` 存在但 `fanotify_init()` / `fanotify_mark()` syscall 未实现（E051 类问题）

### 适配修改

1. **禁用 fanotify 功能**：在 `inotifytools.cpp` 中添加 `#elif defined(__OHOS__)` 分支，不定义 `LINUX_FANOTIFY` 宏，避免调用未实现的 fanotify syscall
2. **fanotify 头文件适配**：在 `fanotify.h.in` 中添加 `#elif defined(__OHOS__)` 分支，使用 `<linux/fanotify.h>` 代替同时包含项目自带头文件和 `<sys/fanotify.h>`，避免结构体重复定义
3. **configure umask 修复**：将 `configure` 中 `umask 077` 改为 `umask 002`，解决 HMDFS 文件系统不允许 umask 077 创建临时目录的问题
4. **bootstrapping**：GitHub tag tarball 不含 configure 脚本，需先执行 `autoreconf -fi`

### 测试结果

- 42/45 测试通过，3 个失败为平台权限限制（非代码问题）
- 失败测试：`inotifytools_watch_file("/", IN_CLOSE)` 被安全策略拒绝、`mkdir(TEST_DIR, 0700)` 在 HMDFS 上受限

## 安装产物

| 文件 | 说明 |
|------|------|
| `bin/inotifywait` | 等待文件系统事件（inotify 模式） |
| `bin/inotifywatch` | 统计文件系统事件（inotify 模式） |
| `bin/fsnotifywait` | inotifywait 的软链接（fanotify 模式在 OHOS 上回退到 inotify） |
| `bin/fsnotifywatch` | inotifywatch 的软链接 |
| `lib/libinotifytools.so.0.4.1` | 共享库 |
| `lib/libinotifytools.a` | 静态库 |
| `include/inotifytools/*.h` | 头文件 |

## 使用示例

```bash
# 监控文件修改事件
inotifywait -m /path/to/file

# 监控目录递归
inotifywait -mr /path/to/dir

# 统计事件
inotifywatch -t 60 /path/to/dir
```

## 注意事项

- 内部版本号 4.23.9.0 与发布标签 4.25.9.0 不同，这是上游版本策略
- fanotify 功能在 OHOS 上不可用，fsnotify* 工具回退到 inotify 模式运行