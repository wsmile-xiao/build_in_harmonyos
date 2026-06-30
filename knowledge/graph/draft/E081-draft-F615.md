# E081: LD env var interferes with dlopen/.so loading on OpenHarmony

## 症状

```
Can't load '/path/to/module.so' for module Foo: Error loading shared library /path/to/module.so: Permission denied
```

## 根因

在 OpenHarmony (musl libc) 上，设置 `LD=<value>` 作为环境变量会干扰动态链接器的 `.so` 加载机制。当 `dlopen()` 试图加载共享库时，`LD` 变量的存在导致 "Permission denied" 错误。

这个问题在 Perl XS 模块编译中尤为常见，因为：
1. 编译时需要设置 `CC=cc LD=cc` 来覆盖 Perl 的默认编译器配置
2. 运行时这些环境变量仍然存在
3. `LD=cc` 导致所有 `.so` 加载失败

## 受影响范围

- Perl XS 模块（使用 `dlopen` 加载 `.so`）
- 任何在运行时使用 `dlopen()` 的软件
- 任何设置了 `LD` 环境变量的场景

## 解决方案

### 方案 1（推荐）: 运行时 unset LD

```bash
# 编译时设置 CC=cc LD=cc
export CC=cc LD=cc
perl Build.PL && ./Build

# 运行/测试时 unset
env -u CC -u LD ./Build test
env -u CC -u LD perl -Mmodule -e '...'
```

### 方案 2: 使用 wrapper 脚本

```bash
#!/bin/sh
unset LD CC
exec "$@"
```

## 验证

```bash
# 检查 LD 是否设置
env | grep "^LD="

# 对比测试：有 LD vs 无 LD
LD=cc perl -Mmeta -e 'print "loaded"'    # FAILS
env -u LD perl -Mmeta -e 'print "loaded"'  # WORKS
```

## 禁止做法

- ❌ 永久设置 `export LD=cc`（会破坏所有 `.so` 加载）
- ❌ 在 `.bashrc` 或 `.profile` 中设置 `LD`

## 来源

- 发现于: perl-meta 0.015-r0 编译 (2026-06-17)
- 关联: E002 (类似的环境变量问题)
