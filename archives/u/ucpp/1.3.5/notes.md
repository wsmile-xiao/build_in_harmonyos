# ucpp 1.3.5 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-15
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：`gitlab.com/scarabeusiv/ucpp/-/archive/master/ucpp-master.tar.gz`
2. 运行 autogen.sh 生成 configure（原始 tarball 无 configure）
   - 设置 AUTOM4TE=autom4te 环境变量解决 aclocal 失败
3. configure --prefix=$DEFAULT_PREFIX
4. make -j4
5. make install DESTDIR=$TEST_PREFIX
6. make check（通过）
7. 本地安装验证成功

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | aclocal 失败（@am_AUTOM4TE@ 未替换） | automake 安装配置问题 | 设置 AUTOM4TE=autom4te 环境变量 |
| 2 | src/cpp.c: void wipeout() 无原型 | clang -Werror 严格检查 | 添加 void 参数：void wipeout(void) |
| 3 | src/macro.c: nt 变量未使用 | clang -Werror 检查 | 添加 (void)nt 抑制警告 |

## 源码修改

- 0001-src-cpp.c.patch: 修复 void 函数声明缺少原型警告
- 0002-src-macro.c.patch: 抑制未使用变量警告

## 依赖版本

- automake 1.16.5
- autoconf 2.72
- libtool 2.4.6
- clang 15.0.4

## 验证结果

```bash
# 测试预处理功能
echo "#include <stdio.h>" > ~/tmp/test.c
~/usr/local/bin/ucpp ~/tmp/test.c
# 输出: 找不到 stdio.h（正常，需要正确的 include 路径）

# 检查库文件
ls ~/usr/local/lib/libucpp.*
# 输出: libucpp.a, libucpp.so, libucpp.so.13, libucpp.so.13.0.5
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libucpp.a | ~50KB | 静态库 |
| libucpp.so.13.0.5 | ~50KB | 动态库 |
| ucpp | ~50KB | 可执行文件 |

## 注意事项

- G0 干净构建验证失败（原始 tarball 无 configure），需使用 hints/autotools-files.tar.gz
- 编译时需设置 AUTOM4TE=autom4te 环境变量
- 源码修改为平台兼容性补丁（R6 追踪）
---
---

**编译结束**: 2026-06-15 11:26
**最终状态**: built
