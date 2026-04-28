# mandoc 1.14.6 适配笔记

## 编译环境
- 构建系统: custom (configure.local)
- 编译日期: 2026-04-23
- 编译器: clang
- 状态: published

## 编译步骤
```bash
# configure.local:
#   PREFIX=/usr/local
#   LN=cp -f  # HMDFS 不支持硬链接
#   CFLAGS="-g -W -Wall -Wmissing-prototypes -Wstrict-prototypes -Wwrite-strings -Wno-unused-parameter"
#   STATIC="-static"
#   LDADD="-lz"
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 不支持硬链接 | 文件系统限制 | LN=cp -f 替代 ln -f |
| 2 | UTF-8 测试部分失败 | 环境 locale 不可用 | 非关键，跳过 |

## 源码修改
- 0001-Makefile.local.patch: LN=cp -f 替代硬链接
- 0002-configure.local.patch: PREFIX=/usr/local

## 验证结果
- 基础测试: 565 + 28 + 244 tests passed
- mandoc --version 正常 ✅

## 交付物
- mandoc, man, apropos, whatis, demandoc, soelim, makewhatis
- libmandoc.a（静态库）

## 注意事项
- 无动态库，仅静态库
- 使用 configure.local 配置，非标准 autotools
