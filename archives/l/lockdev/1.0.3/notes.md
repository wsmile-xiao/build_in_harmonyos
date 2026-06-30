# lockdev 1.0.3 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-05
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：从 Debian archive 下载 lockdev_1.0.3.orig.tar.gz
2. 解压源码：tar -xzf lockdev_1.0.3.tar.gz
3. 修改源码：
   - 修改 src/lockdev.c：添加 `#include <sys/sysmacros.h>`，定义 MAJOR/MINOR 宏
   - 修改 Makefile：修改 CC=clang，添加 DESTDIR 支持
4. 编译：
   ```bash
   make basedir=$HOME/usr/local shared static
   ```
5. 安装到 staging：
   ```bash
   make basedir=$HOME/usr/local DESTDIR=$TEST_PREFIX install
   ```
6. 修正共享库命名：将 liblockdev.1.0.3..so 重命名为 liblockdev.so.1.0.3
7. 打包预编译包：ohc-run.py package lockdev 1.0.3

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | MAJOR/MINOR 未定义 | clang 不定义 __GNU_LIBRARY__ | 添加 #include <sys/sysmacros.h>，定义 fallback 宏 |
| 2 | lock filename build missing | 条件编译不支持非 GNU 平台 | 修改条件编译，添加 `|| 1` |
| 3 | 共享库命名错误（两个点） | VER 正则提取了末尾的点 | 手动重命名为规范格式 |
| 4 | install 使用 gcc | Makefile 默认 CC=gcc | 修改 Makefile，CC=clang |
| 5 | 不支持 DESTDIR | Makefile 无 DESTDIR 变量 | 添加 DESTDIR 变量到 Makefile |

## 源码修改

1. **0001-Makefile.patch**:
   - CC: gcc → clang
   - 添加 DESTDIR 支持

2. **0002-src-lockdev.c.patch**:
   - 添加 #include <sys/sysmacros.h>
   - 定义 MAJOR(dev) = major(dev) 和 MINOR(dev) = minor(dev)
   - 修改条件编译支持非 GNU 平台

## 依赖版本

无外部依赖

## 验证结果

```bash
# 验证安装
ls -la ~/usr/local/lib/liblockdev*
# 输出：
# liblockdev.a
# liblockdev.so.1 -> liblockdev.so.1.0.3
# liblockdev.so.1.0.3

# 验证头文件
ls -la ~/usr/local/include/lockdev.h
ls -la ~/usr/local/include/ttylock.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lockdev-1.0.3-ohos-aarch64.tar.gz | 203KB | 预编译包（静态库+共享库+头文件+手册） |
| lockdev-1.0.3-ohos-aarch64-debug.tar.gz | 69KB | 调试符号包 |
| 0001-Makefile.patch | 2.6KB | Makefile 补丁 |
| 0002-src-lockdev.c.patch | 5.5KB | 源码补丁 |

## 注意事项

1. lockdev 是一个简单的 Makefile 项目，没有 configure 脚本
2. G0 干净构建验证会失败（因为没有 configure）
3. 共享库命名需要手动修正（VER 正则问题）
4. 此库用于设备锁定，主要用于 Unix/Linux 系统

---
**编译结束**: 2026-06-05 17:50
**最终状态**: built