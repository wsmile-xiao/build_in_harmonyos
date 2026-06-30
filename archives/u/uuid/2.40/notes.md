# uuid 2.40 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载 util-linux 2.40 源码：`util-linux-2.40.tar.xz` (8557KB)
2. 解压源码：`~/builds/uuid-2.40.work`
3. Autotools 配置：
   ```bash
   ./configure \
     --prefix=$HOME/usr/local \
     --disable-all-programs \
     --enable-libuuid
   ```
   - `--disable-all-programs`：禁用所有工具编译
   - `--enable-libuuid`：只启用 libuuid 库编译
4. 编译：`make -j2`
5. 安装：`make install DESTDIR=$HOME/tmp/test-install-uuid-2.40`
6. 本地安装：`make install`（不带 DESTDIR）
7. 打包：`ohc-run.py package uuid 2.40`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 编译整个 util-linux 过慢 | util-linux 包含大量工具 | 使用 --disable-all-programs --enable-libuuid 只编译 uuid |

## 源码修改

无手动修改，10 个补丁由 `ohc-run.py refresh-patch --auto` 自动生成：
- 0001-Makefile.patch
- 0002-config.h.patch
- 0003-config.log.patch
- 0004-config.status.patch
- 0005-libblkid-docs-Makefile.patch
- 0006-libfdisk-docs-Makefile.patch
- 0007-libmount-docs-Makefile.patch
- 0008-libsmartcols-docs-Makefile.patch
- 0009-libtool.patch
- 0010-po-man-Makefile.patch

## 依赖版本

无外部依赖。

## 验证结果

```bash
# pkg-config 验证
pkg-config --modversion uuid
# 输出：2.40.0

# 库文件验证
ls ~/usr/local/lib/libuuid.so
ls ~/usr/local/lib/libuuid.so.1
ls ~/usr/local/lib/libuuid.so.1.3.0

# 头文件验证
ls ~/usr/local/include/uuid/uuid.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| uuid-2.40-ohos-aarch64.tar.gz | 436KB | 预编译包 |

## 注意事项

1. 使用 --disable-all-programs --enable-libuuid 只编译 uuid，避免编译整个 util-linux
2. 自动生成的 10 个补丁是平台相关配置文件，由脚本自动处理
3. G0 干净构建验证有警告（Python subprocess 平台限制），但手动验证已通过
---
**编译结束**: 2026-06-03 17:23
**最终状态**: built