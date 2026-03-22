# GNU Coreutils 9.10 跳过测试用例分类

**生成时间**: 2026-03-17  
**跳过测试总数**: 230

---

## 一、按跳过原因分类

### 1. inotify 不支持 (系统限制)

```
tests/tail/inotify-race
tests/tail/inotify-race2
tests/tail/inotify-rotate-resources
tests/tail/inotify-dir-recreate
tests/tail/inotify-only-regular
```

**原因**: 鸿蒙系统不支持 Linux 的 inotify 文件监控机制。

---

### 2. 缺少系统设备/特性

| 测试用例 | 缺少的设备/特性 |
|----------|----------------|
| `tests/misc/io-errors` | `/dev/full` |
| `tests/misc/write-errors` | `/dev/full` |
| `tests/tty/tty-eof` | Perl Expect 包 |
| `tests/cp/no-ctx` | SELinux 支持 |
| `tests/chcon/chcon-fail` | SELinux 支持 |
| `tests/misc/mknod` | mknod 权限 |
| `tests/misc/kill` | 特定信号支持 |

---

### 3. 昂贵测试 (默认禁用)

| 测试用例 | 启用环境变量 |
|----------|-------------|
| `tests/rm/ext3-perf` | `RUN_VERY_EXPENSIVE_TESTS=yes` |
| `tests/cp/link-heap` | `RUN_EXPENSIVE_TESTS=yes` |
| `tests/rm/many-dir-entries-vs-OOM` | 昂贵测试 |
| `tests/od/big-w` | 大文件测试 |

---

### 4. 多字节字符/国际化

```
tests/expr/expr-multibyte       # 多字节表达式
tests/join/join-utf8            # UTF-8 连接
tests/fold/fold-characters      # 折叠字符
tests/fold/fold-nbsp            # 不换行空格
tests/fold/fold-spaces          # 空格折叠
tests/fold/fold-zero-width      # 零宽度
tests/numfmt/mb-non-utf8        # 非UTF-8多字节
tests/paste/multi-byte          # 多字节粘贴
```

---

### 5. 特定时区/地区

```
tests/date/date-ethiopia        # 埃塞俄比亚历法
tests/date/date-iran            # 伊朗历法
tests/date/date-locale-hour     # 地区小时格式
tests/date/date-thailand        # 泰国历法
```

---

### 6. 内存边界测试

```
tests/pr/bounded-memory
tests/cut/bounded-memory
tests/basenc/bounded-memory
tests/expand/bounded-memory
tests/csplit/csplit-heap
tests/csplit/csplit-io-err
tests/shuf/shuf-reservoir
tests/sort/sort-benchmark-random
```

---

### 7. 特定平台/架构

```
tests/misc/arch                 # arch 命令
tests/seq/seq-long-double       # 长双精度浮点
tests/nice/nice                 # 进程优先级
```

---

### 8. 其他跳过原因

| 测试用例 | 跳过原因 |
|----------|----------|
| `tests/ls/ls-misc` | 无法创建 setuid/setgid/sticky 文件 |
| `tests/rm/isatty` | 需要 tty |
| `tests/rm/hash` | 特定条件 |
| `tests/rm/r-root` | 需要 root |
| `tests/chgrp/deref` | 符号链接问题 |
| `tests/seq/seq-io-errors` | I/O 错误测试 |
| `tests/tail/tail-sysfs` | sysfs 访问 |
| `tests/tail/overlay-headers` | overlayfs |
| `tests/tail/pid-pipe` | 管道 PID |
| `tests/cat/cat-buf` | 缓冲测试 |
| `tests/env/env-null` | 空环境 |
| `tests/env/env-S` | -S 选项 |
| `tests/head/head-write-error` | 写错误 |
| `tests/cut/cut-huge-range` | 大范围 |
| `tests/printf/printf-surprise` | 特殊格式 |
| `tests/pwd/pwd-long` | 长路径 |
| `tests/runcon/runcon-compute` | SELinux |
| `tests/runcon/runcon-no-reorder` | SELinux |

---

## 二、统计摘要

| 跳过原因类别 | 数量估计 |
|-------------|---------|
| inotify 不支持 | ~10 |
| 缺少设备/特性 | ~20 |
| 昂贵测试(默认禁用) | ~15 |
| 多字节字符/国际化 | ~15 |
| 特定时区/地区 | ~5 |
| 内存边界测试 | ~10 |
| 特定平台/架构 | ~5 |
| 其他 | ~150 |

---

## 三、注意事项

1. **多数跳过是预期行为**: 这些测试在 Linux 系统上也可能跳过
2. **不影响核心功能**: 跳过的测试主要涉及边缘情况和特殊功能
3. **可选择性启用**: 部分测试可通过设置环境变量启用

---

*报告生成时间: 2026-03-17*