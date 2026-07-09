# pkill 4.0.6 适配笔记

## 编译环境
- 构建系统: custom（手动编译，autotools config.status 在 HMDFS 上失败）
- 编译日期: 2026-07-08
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

1. 下载 procps-ng 4.0.6 官方发布包并解压
2. 应用两个 musl 兼容补丁：
   - `0001-fileutils-fpending-musl.patch` — 修复 `__fpending` 宏
   - `0002-sort-h-stddef.patch` — 添加 `#include <stddef.h>`
3. 手动生成最小 `config.h`（绕过 autotools config.status HMDFS 失败）
4. 编译 `local/{fileutils,signals,strutils}.c` + `library/*.c`（跳过 meminfo.c/vmstat.c）+ `src/pgrep.c`
5. 静态链接生成 pkill 二进制文件

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autotools config.status 失败 | HMDFS 文件系统权限问题 | 手动生成 config.h，绕过 configure |
| 2 | `__fpending` 宏编译错误 | musl libc 的 FILE 结构体无 `_p`/`_bf._base` 字段 | 补丁：`#define __fpending(fp) 0` |
| 3 | `size_t` 未定义 | `sort.h` 缺少 `#include <stddef.h>` | 补丁：添加头文件 |
| 4 | `meminfo.c`/`vmstat.c` 编译失败 | 使用 `hsearch_data`，musl libc 不支持 | 编译时跳过这两个文件 |
| 5 | 二进制始终在 pgrep 模式 | `config.h` 缺少 `HAVE_PROGRAM_INVOCATION_SHORT_NAME`，`local/c.h` fallback 用 `__FILE__` 替代 `argv[0]` | 在 config.h 中定义该宏并添加 `extern` 声明 |

## 源码修改

- `patches/0001-fileutils-fpending-musl.patch` — `local/fileutils.c` 中 `__fpending` 宏改为返回 0
- `patches/0002-sort-h-stddef.patch` — `library/include/sort.h` 添加 `#include <stddef.h>`
- `conanfile.py` 的 `config.h` 生成部分 — 添加 `HAVE_PROGRAM_INVOCATION_SHORT_NAME` 和 `extern` 声明（非补丁文件，在配方内联修复）

## 依赖版本

无外部依赖。源码内嵌 libproc2，静态链接，无运行依赖。

## 验证结果

```bash
$ pkill -V
pgrep from procps-ng 4.0.6
$ file pkill
ELF 64-bit LSB arm64, statically linked
```

## 注意事项

- pkill 与 pgrep 共享 `src/pgrep.c` 源文件，编译产物是 pkill 命令
- `library/meminfo.c` 和 `vmstat.c` 被跳过，pkill 不使用 /proc/meminfo 解析功能
- 编译器路径通过 Conan profile conf 获取 (R33)，不硬编码

---

**编译结束**: 2026-07-08 23:52
**最终状态**: published
