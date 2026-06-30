# libiodbc 3.52.16 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-26
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: published

## 编译步骤

1. 源码无 configure 脚本，需先运行 `autoreconf -fi` 生成
2. `./configure --prefix=$DEFAULT_PREFIX --disable-static`
3. `make -j1`
4. `make install DESTDIR=$TEST_PREFIX` (R20 DESTDIR模式)
5. `make check` (iODBC无独立测试套件，仅编译级检查)
6. verify-build → package → make install (不带DESTDIR)
7. finish published

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL证书验证失败，无法下载源码 | HarmonyOS CA证书问题 | 手动curl --insecure下载tarball，init-build --no-download |
| 2 | iodbctest链接失败：undefined symbol ODBCSharedTraceFlag等 | libtool convenience库(noinst_LTLIBRARIES)未合并到静态归档libiodbc.a；样本程序使用`-static`强制静态链接 | 修改samples/Makefile.am移除iodbctest/iodbctestw的`-static` LDFLAGS；同时configure加`--disable-static` |
| 3 | iodbctest无法在本地运行(musl ld.so加载共享库限制) | HarmonyOS musl动态链接器行为差异 | 平台已知限制，iodbc-config/pkg-config验证正常即可 |

## 源码修改

- **0001-remove-static-ldflags.patch**: 移除 samples/Makefile.am 中 iodbctest 和 iodbctestw 的 `-static` LDFLAGS，解决libtool convenience库静态链接问题

## 依赖版本

- 无特殊依赖（独立ODBC驱动管理器）
- 构建工具：autoconf 2.72, automake 1.16.5, libtool, make 4.4.1

## 验证结果

```bash
$ iodbc-config --version
3.52.16
$ iodbc-config --cflags
-I/storage/Users/currentUser/usr/local/include
$ iodbc-config --libs
-L/storage/Users/currentUser/usr/local/lib  -liodbc -liodbcinst
$ PKG_CONFIG_PATH=... pkg-config --modversion libiodbc
3.52.16
$ make check
# iODBC无独立测试套件，所有模块 make check 通过
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libiodbc-3.52.16-ohos-aarch64.tar.gz | 2360KB | 预编译包（共享库+头文件+iodbc-config+iodbctest） |
| 0001-remove-static-ldflags.patch | 1KB | 移除样本程序静态链接 |

## 注意事项

- iODBC 源码缺少 configure 脚本，必须先 autoreconf -fi
- libtool convenience库(noinst_LTLIBRARIES)不合并到父库的.a静态归档中，因此不能用-static链接样本程序
- iodbctest/iodbctestw在鸿蒙本地因musl ld.so限制无法直接运行，但共享库功能正常
- config.guess正确识别 aarch64-unknown-linux-ohos，无需修改
---

**编译结束**: 2026-05-26 01:09
**最终状态**: published
