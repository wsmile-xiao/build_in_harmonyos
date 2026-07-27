# picat 3.9.7 适配笔记

## 编译环境
- 构建系统: makefile (自定义 Makefile)
- 编译日期: 2026-07-15
- 编译器: clang 15.0.4 / clang++ 15.0.4 (Target: aarch64-unknown-linux-ohos)
- 平台: aarch64-unknown-linux-ohos (OpenHarmony, musl libc)
- 状态: built

## 编译步骤

picat 使用自定义 Makefile，不支持标准 autotools/configure。编译步骤：

1. 创建 Makefile.ohos（基于 Makefile.linux64，适配 clang 和 OpenHarmony）
2. `cd emu && make -f Makefile.ohos` 编译生成 picat 二进制
3. 手动安装到 staging 目录：
   - picat → $DEFAULT_PREFIX/bin/picat
   - lib/*.pi → $DEFAULT_PREFIX/share/picat/lib/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `struct _IO_FILE` incomplete type error | musl libc 不暴露 FILE 内部结构，picat 直接访问 fdes->_fileno | 改用标准 POSIX fileno() 函数，添加 `__OHOS__` 守卫（R8准则） |
| 2 | 无 Makefile 适配 OpenHarmony/clang | picat 只提供 linux64/mac64 等平台 Makefile | 创建 Makefile.ohos，使用 clang 替代 gcc/g++，添加 -fPIC 和 -D__OHOS__，保留 -DGCC 和 -DM64BITS |

## 源码修改

1. **emu/file.c** (0001-emu-file.c.patch): 在 `get_socket_fd()` 函数中，将 `fdes->_fileno` 改为 `fileno(fdes)`，使用 `__OHOS__` 守卫（R8准则）
2. **emu/Makefile.ohos** (0002-emu-Makefile.ohos.patch): 新建 Makefile，CC/CPP 改为 clang/clang++，添加 -fPIC 和 -D__OHOS__，保留 -DGCC 和 -DM64BITS

## 依赖版本

无外部依赖（picat 自包含，内嵌 espresso/kissat/fann）

## 验证结果

### 版本号确认
```
$ picat --version
Picat version 3.9#7
```

### 基本算术运算
```
$ picat test_picat.pi
hello_picat
7
[1,2,3,4,5]
15
```

## 注意事项

- picat 需要 PICATPATH 环境变量指向 lib 目录，才能加载非预加载模块
- -DGCC 宏必须保留（启用 computed goto 等 GCC 扩展，clang 兼容）
- -DM64BITS 宏必须保留（64-bit 类型定义）
- -D__OHOS__ 宏启用 OpenHarmony 平台守卫代码
- musl libc 不暴露 FILE 内部结构，所有 `_fileno`/`_file` 直接访问需改为 `fileno()`
- make check 不可用（picat 无标准测试套件）
---

**编译结束**: 2026-07-15 23:14
**最终状态**: built
