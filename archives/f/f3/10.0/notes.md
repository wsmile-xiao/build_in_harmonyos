# f3 10.0 适配笔记

## 编译环境
- 构建系统: makefile (plain Makefile, no configure)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

1. 构建 argp-standalone 1.5.0（HarmonyOS 缺少 argp.h）
   - 下载 argp-standalone 源码
   - 创建 config.h（含 dgettext 宏桩、UNUSED 宏）
   - 编译 9 个源文件为 .o
   - 用 llvm-ar 创建 libargp.a
   - 安装 argp.h 和 libargp.a 到临时目录

2. 构建 f3 主目标
   ```bash
   make OS=Linux CFLAGS="-fPIC -O2 -I<argp_dir>/include" LDFLAGS="-L<argp_dir>/lib -largp" -j1
   ```
   - OS=Linux 跳过 Makefile 的 argp 路径逻辑
   - CFLAGS 被 Makefile 的 `+=` 追加 -std=c17 -Wall 等
   - 仅构建 f3write 和 f3read（主目标）

3. 安装
   ```bash
   make install PREFIX=/usr/local DESTDIR=<staging_dir>
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | argp.h not found | HarmonyOS libc 不含 GNU argp | 内联构建 argp-standalone 1.5.0 |
| 2 | dgettext 未声明 | libintl.h 存在但 dgettext 未导出 | config.h 中定义 dgettext 宏桩 |
| 3 | UNUSED 宏未定义 | config.h 缺少 GCC 属性定义 | 添加 HAVE_GCC_ATTRIBUTE 和 UNUSED 宏 |

## 依赖版本

- argp-standalone 1.5.0 (内联构建)
- clang 15.0.4
- make 4.4.1

## 验证结果

```bash
$ ./build/f3write --version
F3 Write 10.0
$ ./build/f3read --version
F3 Read 10.0
```

## 注意事项

- f3probe/f3brew 需要 libudev，f3fix 需要 libparted，当前未适配
- argp-standalone 需在 conanfile.py build() 中内联构建
---

**编译结束**: 2026-07-15 23:42
**最终状态**: built
