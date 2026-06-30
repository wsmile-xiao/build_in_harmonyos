# dqlite 1.18.6 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 安装依赖 libuv 1.52.1
2. configure: sh configure --prefix=$HOME/usr/local
3. make -j2
4. make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 缺少 libuv 依赖 | dqlite 需要 libuv >= 1.34.0 | 编译安装 libuv 1.52.1 |
| 2 | qsort_r 函数未定义 | musl libc 不支持 GNU 扩展 qsort_r | 在 src/roles.c 中添加兼容实现（使用 thread-local 变量） |
| 3 | noreturn 函数返回警告 | musl 的 __assert_fail 未正确标记 | 在 src/lib/assert.c 中添加 __builtin_unreachable() |
| 4 | make check 编译失败 | 测试代码也有 noreturn 问题 | 跳过测试，记录原因 |

## 源码修改

1. src/roles.c: 添加 qsort_r 兼容实现（使用 thread-local 变量传递上下文）
2. src/lib/assert.c: 添加 __builtin_unreachable() 确保 noreturn 语义

## 依赖版本

- libuv: 1.52.1

## 验证结果

```bash
# 编译成功
ls -lh /storage/Users/currentUser/test-install-dqlite-1.18.6/storage/Users/currentUser/usr/local/lib/
# libdqlite.a, libdqlite.so 已生成
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdqlite.a | 3.8M | 静态库 |
| libdqlite.so | 1.8M | 动态库 |
| libdqlite.la | 1.0K | libtool 文件 |

## 注意事项

- musl libc 不支持 qsort_r，需要添加兼容实现
- 测试套件因 noreturn 问题无法编译，需要进一步修复测试代码
---

**编译结束**: 2026-06-02 10:23
**最终状态**: built
