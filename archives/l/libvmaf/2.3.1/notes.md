# libvmaf 2.3.1 适配笔记

## 编译环境
- 构建系统: meson
- 编译日期: 2026-05-21
- 编译器: clang-15 (LLVM 15.0.4)
- 状态: building

## 编译步骤

1. **构建系统识别**: meson（在 libvmaf 子目录）
2. **meson 配置**: `meson setup build --prefix=$DEFAULT_PREFIX --buildtype=release --default-library=static -Denable_float=true -Dbuilt_in_models=false`
3. **ninja 编译**: `ninja -C build -j 2`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | xxd --include 不支持 | toybox xxd 缺少 vim xxd 的 --include 选项 | 禁用 built_in_models（-Dbuilt_in_models=false） |
| 2 | cc 编译器找不到 | HMDFS 软链接权限问题，cc 是指向 shell 脚本的软链接 | 修改 build.ninja，直接使用 clang-15 可执行文件 |
| 3 | M_PI 未定义 | meson 在 ohos 系统上使用 -D_POSIX_C_SOURCE=200112L | 在 ciede.c 中添加 M_PI 条件定义 |
| 4 | strsep 未声明 | strsep 是 BSD/GNU 扩展，在 POSIX 源定义下不可用 | 在 cli_parse.c 中添加 _GNU_SOURCE 定义 |

## 源码修改

**修改 1: ciede.c 添加 M_PI 定义**

文件: `libvmaf/src/feature/ciede.c`

```c
#include <errno.h>
#include <math.h>
#include <stddef.h>
#include <string.h>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

#include "feature_collector.h"
```

**修改 2: cli_parse.c 添加 _GNU_SOURCE 定义**

文件: `libvmaf/tools/cli_parse.c`

```c
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <assert.h>
#include <getopt.h>
...
```

## 依赖版本

- meson: 1.11.1
- ninja: 1.12.1
- clang: 15.0.4

## 验证结果

```bash
$ vmaf --version
f266167

$ ls -la ~/usr/local/lib/libvmaf.a
-rw-r----- 1 file_manager 612280 2026-05-21 17:07 libvmaf.a

$ ls -la ~/usr/local/bin/vmaf
-rwxr-x--- 1 file_manager 432640 2026-05-21 17:08 vmaf
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libvmaf-2.3.1-ohos-aarch64.tar.gz | 2464KB | 预编译包（包含 bin/vmaf, lib/libvmaf.a, include/libvmaf/*.h） |
| 0001-libvmaf-src-feature-ciede.c.patch | 794B | M_PI 条件定义补丁 |
| 0002-libvmaf-tools-cli_parse.c.patch | 374B | _GNU_SOURCE 定义补丁 |

## 注意事项

- libvmaf 的 meson.build 在 libvmaf 子目录，不在根目录
- 根目录的 Makefile 是包装器
- 系统识别为 ohos，meson 使用 POSIX 源定义而非 GNU 源定义
- 需要在源码中处理 M_PI 等非标准常量
- C++ 标准库（libc++）需要显式链接
- HMDFS 软链接权限问题需要手动处理编译器路径
**质量门禁**: G0-PASS G1-PASS G2-PASS G3-PASS G4-PASS
**备注**: 所有质量门禁通过，预编译包已生成并可用
---

**编译结束**: 2026-05-21 18:16
**最终状态**: built
