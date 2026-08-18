# coturn 4.7.0 适配笔记

## 编译环境
- 构建系统: autotools（自写 configure 脚本 + Makefile）
- 编译日期: 2026-08-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
export TMPDIR=/storage/Users/currentUser/tmp
export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
export CPPFLAGS="-I/storage/Users/currentUser/usr/local/include"
export LDFLAGS="-L/storage/Users/currentUser/usr/local/lib"
./configure --prefix=$DEFAULT_PREFIX \
  --with-mysql=no --with-postgresql=no --with-mongodb=no --with-hiredis=no \
  --disable-dependency-tracking
make -j1
make install DESTDIR=$TEST_PREFIX
make check
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 报 `can't create /tmp/__test__ccomp__.c: Read-only file system`，无法探测编译器 | coturn 自写 configure 将编译器探测临时 C 文件写入 /tmp，而 OHOS 的 /tmp 是只读挂载 | 补丁 0001：configure 优先使用可写 $TMPDIR 环境变量，否则回退 /var/tmp→/tmp→当前目录 |
| 2 | turnadmin 是符号链接（`ln -s turnserver turnadmin`） | OHOS 用户存储不允许符号链接 | conanfile.py package() 中把 bin/ 下真实文件复制进包，turnadmin 变为普通文件 |
| 3 | configure 报 `Library option -lcrypto cannot be used` / `ERROR: OpenSSL Crypto development libraries are not installed properly in required location.` | coturn 自写 configure 探测 OpenSSL 时用裸 `${CC} ${OSCFLAGS} ${OSLIBS} -lcrypto`（不读 LDFLAGS），且 pkg-config 按 `libcrypto`/`libssl` 模块名查询，而 conan openssl 包只提供 `openssl.pc`（配方未设 pkg_config_name）→ 两个探测都失败 | conanfile.py build() 设置 configure 文档化的覆盖变量：`SSL_CFLAGS=-I<openssl include>`、`SSL_LIBS=-L<openssl lib> -lcrypto -lssl`，configure 走 "Private SSL Library option" 分支直接采用并写入生成的 Makefile |

## 源码修改

- `configure`：TMPDIR 选择逻辑支持可写环境变量（0001-configure-writable-tmpdir.patch）

## 依赖版本

- libevent 2.1.12（预编译包）
- openssl 3.5.6（预编译包）
- sqlite3 3.49.1（预编译包）
- zlib 1.3.1（openssl 依赖）

## 验证结果

```bash
$ ./bin/turnserver --version
4.7.0
$ make check
RFC 5769 message fingerprint test(0) result: success
... (14 个 RFC 5769 测试全部 success)
oauth token A128GCM:OK
oauth token A256GCM:OK
```

## 交付物

bin/ 下可执行文件：turnserver（含 turnadmin 副本）、turnutils_natdiscovery、turnutils_oauth、turnutils_peer、turnutils_rfc5769check、turnutils_stunclient、turnutils_uclient；静态库 lib/libturnclient.a；头文件 include/turn/。

## 注意事项

- libevent 发布包未含 event_openssl 功能时，TLS/DTLS 监听器可能不可用（参考 4.15.0 处理方式，本次以 --version 与 RFC 5769 测试为验证标准）。
- Prometheus 支持默认关闭（无 libprom/libmicrohttpd）。
---

**编译结束**: 2026-08-17 11:52
**最终状态**: built
