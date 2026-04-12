# musl libc 兼容性知识

鸿蒙系统使用 **musl libc** 而非 Linux 常用的 **glibc**，这种差异会导致某些软件在编译时出现问题。

> **📋 完整文档导航**：
> - **全量接口对比表 (ISO C + POSIX)**: [`musl-glibc-full-comparison-iso-posix.md`](./musl-glibc-full-comparison-iso-posix.md) — 逐接口列出 ISO C89~C23 和 POSIX.1-2008 的支持差异
> - **全量接口对比表 (GNU 扩展 + Linux syscall)**: [`musl-glibc-full-comparison-gnu-linux.md`](./musl-glibc-full-comparison-gnu-linux.md) — 覆盖所有 GNU 扩展头文件/函数和 Linux 特有 syscall 封装
> - **开发者影响分析报告**: [`musl-glibc-developer-impact.md`](./musl-glibc-developer-impact.md) — 编译期/运行期/行为语义/安全/各语言运行时的全面影响分析和迁移最佳实践

## 1. 核心差异对比

| 特性 | glibc | musl libc (鸿蒙) | 影响 |
|------|-------|------------------|------|
| FILE 结构体 | 暴露内部字段（`_IO_read_ptr` 等） | **不透明类型**，内部结构不可访问 | gnulib stdio 扩展模块需要适配 |
| `__freadahead` 函数 | 有 | 无 | 无法直接获取预读数据量 |
| `__freadptr` 函数 | 有 | 无 | 无法直接获取缓冲区指针 |
| stdio_ext.h | 提供完整的扩展函数 | 仅提供 `__fwriting`、`__freading` 等 | 功能受限 |
| 动态链接默认标志 | BIND_LAZY | **BIND_NOW** | 扩展模块需链接主库 |
| 线程局部存储 | 完整支持 | 支持但有差异 | 某些多线程代码需适配 |
| 动态链接器 | ld-linux.so | ld-musl-*.so | 加载器不同 |

<!-- ~~## 2. FILE 结构体差异详解~~ → 已迁移至 graph/E061.kv + doc/E061.md, graph/E062.kv + doc/E062.md -->

<!-- ~~## 3. BIND_NOW 问题~~ → 已迁移至 graph/E078.kv + doc/E078.md -->

## 4. 检测 musl 的方法

### 4.1 编译时检测

```c
#if defined(__linux__) && !defined(__GLIBC__)
  // musl libc 环境
#endif

#if defined(__OHOS__)
  // HarmonyOS（使用 musl）
#endif
```

### 4.2 运行时检测

```bash
# 检查 C 库类型
ldd /bin/sh | grep libc
# glibc: libc.so.6
# musl:  ld-musl-aarch64.so.1

# 或检查可执行文件
file /bin/sh
# glibc: dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2
# musl:  dynamically linked, interpreter /lib/ld-musl-aarch64.so.1
```

## 5. 常见 musl 兼容性问题

<!-- ~~### 5.1 gnulib 假设 glibc FILE~~ → 已迁移至 E061, E062 -->

<!-- ~~### 5.2 缺少 glibc 特有函数~~ → 已迁移至 graph/E051.kv + doc/E051.md -->

<!-- ~~### 5.3 线程局部存储差异~~ → 已迁移至 graph/E026.kv + doc/E026.md -->

## 6. 参考项目

已完成 musl 适配的项目：
- **GNU coreutils 9.10**: `archives/c/coreutils/9.10/`
- 包含 freadahead.c、freadptr.c、freadseek.c 的完整适配方案

## 7. 通用原则

| 变量 | 用途 | 能否包含主库链接？ |
|------|------|-------------------|
| BLDSHARED | 构建主共享库 | ❌ 不能（循环依赖） |
| LDSHARED | 构建插件/扩展 | ✅ 必须（符号解析） |

<!-- ~~## 8. _GNU_SOURCE 宏需求~~ → 已迁移至 graph/E032.kv + doc/E032.md -->

<!-- ~~## 9. _XOPEN_SOURCE_EXTENDED 宏需求~~ → 已迁移至 graph/E033.kv + doc/E033.md -->

<!-- ~~## 10. bash malloc 与 musl 不兼容~~ → 已迁移至 graph/E029.kv + doc/E029.md -->

<!-- ~~## 11. iconv 不支持 glibc 扩展后缀~~ → 已迁移至 graph/E039.kv + doc/E039.md -->