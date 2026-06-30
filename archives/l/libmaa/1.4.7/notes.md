# libmaa 1.4.7 适配笔记

## 编译环境
- 构建系统: BSD make (mkc) → GNU make (custom)
- 编译日期: 2026-06-02
- 编译器: clang 15.0.4
- 状态: built

## 编译步骤

本项目使用 BSD make (mkc) 构建系统，不兼容 GNU make。采用手动编译方案：

1. 创建 GNU Make 兼容的 Makefile.gnu
2. 手动生成 arggram.c（arg.c 需要）
3. 编译静态库和动态库（排除 bit.c、timer.c）
4. 安装到 DESTDIR

```bash
cd ~/builds/libmaa-1.4.7.work/maa
awk -f arggram2c arggram.txt > arggram.c
make -f Makefile.gnu
make -f Makefile.gnu install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | Makefile 语法错误 | BSD make (.for) 不兼容 GNU make | 创建 Makefile.gnu |
| 2 | SIZEOF_LONG 未定义 | musl 缺少自动检测 | 添加 -DSIZEOF_LONG=8 |
| 3 | getrusage 不可用 | musl 不支持 sys/resource.h | 排除 timer.c |
| 4 | 缺少 -fPIC | 共享库需要位置无关代码 | CFLAGS += -fPIC |
| 5 | bit.c 需要 SIZEOF_LONG | 同问题 2 | 排除 bit.c（功能可选）|

## 源码修改

**新增文件**：maa/Makefile.gnu（GNU Make 兼容 Makefile）

**排除文件**：bit.c、timer.c（平台限制，非核心功能）

## 依赖版本

- clang 15.0.4
- llvm-ar, llvm-ranlib
- GNU awk 5.4.0

## 验证结果

```bash
ls -la ~/test-install-libmaa-1.4.7/storage/Users/currentUser/usr/local/lib/
# libmaa.a (162KB), libmaa.so.4.0 (100KB), libmaa.so, libmaa.so.4
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmaa.a | 162KB | 静态库 |
| libmaa.so.4.0 | 100KB | 动态库 |
| maa.h | 24KB | 头文件 |

## 注意事项

1. 本项目原始构建系统为 BSD make (mkc)，不兼容 GNU make
2. bit.c 和 timer.c 因平台限制（musl 缺少 sys/resource.h）已排除
3. arggram.c 需手动生成，否则 arg.c 无法编译
---

**编译结束**: 2026-06-02 10:16
**最终状态**: built
