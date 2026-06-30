# musl libc 兼容性快速参考

鸿蒙使用 **musl libc**（非 glibc），部分软件需适配。

> 完整接口对比见 `musl-glibc-full-comparison-*.md` 系列，开发者影响分析见 `musl-glibc-developer-impact.md`。

## 1. 核心差异对比

| 特性 | glibc | musl (鸿蒙) | 影响 |
|------|-------|-------------|------|
| FILE 结构体 | 暴露内部字段 | **不透明类型** | gnulib stdio 扩展需适配 |
| `__freadahead`/`__freadptr` | 有 | 无 | 无法获取预读/缓冲区指针 |
| stdio_ext.h | 完整扩展函数 | 仅 `__fwriting`/`__freading` 等 | 功能受限 |
| 动态链接默认 | BIND_LAZY | **BIND_NOW** | 扩展模块需链接主库 |
| 线程局部存储 | 完整 | 支持有差异 | 部分多线程代码需适配 |
| 动态链接器 | ld-linux.so | ld-musl-*.so | 加载器不同 |

## 2. 检测 musl 的方法

### 编译时

```c
#if defined(__linux__) && !defined(__GLIBC__)
  /* musl libc 环境 */
#endif
#if defined(__OHOS__)
  /* HarmonyOS（使用 musl） */
#endif
```

### 运行时

```bash
ldd /bin/sh | grep libc          # glibc: libc.so.6 / musl: ld-musl-aarch64.so.1
file /bin/sh                     # 看 interpreter 路径
```

## 3. 参考项目

- **GNU coreutils 9.10**（`archives/c/coreutils/9.10/`）：含 freadahead.c、freadptr.c、freadseek.c 完整 musl 适配方案。

## 4. 共享库构建变量

| 变量 | 用途 | 能否包含主库链接？ |
|------|------|-------------------|
| BLDSHARED | 构建主共享库 | ❌ 不能（循环依赖） |
| LDSHARED | 构建插件/扩展 | ✅ 必须（符号解析） |

---

*文档版本: 2.0 · Conan 体系适配*
