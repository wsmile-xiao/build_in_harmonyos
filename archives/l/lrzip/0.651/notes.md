# lrzip 0.651 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-11
- 编译器: clang/clang++ (LLVM 15.0.4)
- 状态: built

## 编译步骤

1. **源码获取**: 从 GitHub 下载 lrzip 0.651 tarball
   ```
   https://github.com/ckolivas/lrzip/archive/refs/tags/v0.651.tar.gz
   ```

2. **autoreconf**: 生成 configure 脚本（需设置 PERL5LIB）
   ```
   export PERL5LIB="/storage/Users/currentUser/usr/local/share/automake-1.16:$PERL5LIB"
   autoreconf -if
   ```

3. **configure**: 配置编译选项
   ```
   ./configure --prefix=/storage/Users/currentUser/usr/local \
     LDFLAGS="-L/storage/Users/currentUser/usr/local/lib" \
     CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
   ```

   注意：由于 HMDFS 文件系统权限限制，需修改 config.status 使用本地 TMPDIR。

4. **make**: 编译（-j1）
   ```
   make -j1
   ```

5. **make install DESTDIR**: 安装到 staging 目录
   ```
   make install DESTDIR=/storage/Users/currentUser/test-install-lrzip-0.651
   ```

6. **make check**: 无实际测试用例，跳过

7. **本地安装验证**:
   ```
   make install  # 不带 DESTDIR
   lrzip --version  # 输出: lrzip version 0.651
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake Perl 模块路径错误 | automake 版本不匹配（1.17脚本指向1.16模块） | 设置 PERL5LIB="/storage/Users/currentUser/usr/local/share/automake-1.16" |
| 2 | 缺少 libbz2.so.1.0 软链接 | bzip2 安装缺少软链接 | 创建软链接: ln -s libbz2.so.1.0.8 libbz2.so.1.0 |
| 3 | 缺少 lzo2 库 | lrzip 依赖 lzo2 压缩库 | 手动下载预编译包并安装到 usr/local |
| 4 | 缺少 lz4 库 | lrzip 依赖 lz4 压缩库 | 手动下载预编译包并安装到 usr/local |
| 5 | ltmain.sh 缺失 | autoreconf 需要 libtool 配置文件 | 从 usr/local/share/libtool 复制 |
| 6 | config.status 权限问题 | HMDFS 文件系统限制临时目录创建 | 修改 config.status 使用本地 TMPDIR |
| 7 | SSL 证书问题 | curl 无法验证 HTTPS 连接 | 设置 OPENSSL_CONF=/dev/null 使用 -k 参数 |

## 源码修改

生成的补丁主要是 autotools 构建产物（Makefile.in、config.guess、config.sub 等），非源码修改。

## 依赖版本

- zlib: 1.3.1 (已安装)
- bzip2: 1.0.8 (已安装)
- lzo2: 2.10 (手动安装)
- lz4: 1.10.0 (手动安装)
- autoconf: 2.72
- automake: 1.16.5
- libtool: 2.4.7

## 验证结果

```bash
$ lrzip --version
lrzip version 0.651

$ lrzip -h
lrzip version 0.651

lrzip is a compression program optimised for large files. The compression
ratios and speeds achieved are often significantly better than those achieved
by gzip, bzip2, lzma, xz...
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| lrzip-0.651-ohos-aarch64.tar.gz | 2067282 bytes (约2MB) | 预编译包 |
| lrzip-0.651-ohos-aarch64-debug.tar.gz | 2597282 bytes (约2.6MB) | 含调试符号包 |

## 注意事项

1. lrzip 需要多种压缩库支持（zlib、bzip2、lzo2、lz4）
2. autotools 构建需要正确的 Perl 模块路径
3. HMDFS 文件系统对 config.status 临时目录创建有限制，需使用本地 TMPDIR
4. 预编译包已包含外部依赖 libbz2.so.1.0

---

**编译结束**: 2026-06-11 17:45
**最终状态**: built
---

**编译结束**: 2026-06-12 10:10
**最终状态**: built
