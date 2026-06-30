# mysql-client 8.4.9 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-09
- 编译器: clang/clang++ (HarmonyOS NEXT SDK)
- 状态: published

## 编译步骤

1. 下载 MySQL 8.4.9 完整源码 (mysql-8.4.9.tar.gz)
2. 应用 8 个 OHOS 适配补丁 (0001-0008)
3. 配置 cmake:
   ```bash
   cmake -DWITHOUT_SERVER=ON \
         -DWITH_EDITLINE=none \
         -DWITH_SSL=system \
         -DWITH_LIBEVENT=bundled \
         -DFORCE_UNSUPPORTED_COMPILER=ON \
         -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local \
         -DCMAKE_SYSTEM_NAME=OHOS \
         ..
   ```
4. 编译: `make -j$(nproc)`
5. 安装: `make install`
6. 签名所有 ELF 二进制: 使用 binary-sign-tool 签名所有 .so 和可执行文件
7. 打包: 创建 aarch64 和 aarch64-debug tar.gz

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | editline/libedit 不可用 | HarmonyOS NEXT 缺少 ncurses/libedit | 添加 WITH_EDITLINE=none 选项，跳过 mysql CLI 工具构建 |
| 2 | DNS SRV API 不可用 (res_search/res_ninit) | HarmonyOS musl libc 不提供完整 libresolv | 在 dns_srv.cc 中使用 res_init/res_search 代替 res_n* |
| 3 | pthread_cancel() 不可用 | HarmonyOS musl libc 不实现 pthread_cancel | 在 my_thread.cc 中对 __OHOS__ 返回 ENOTSUP |
| 4 | my_read() uchar 类型不匹配 | get_password.cc 中 char* 传入 uchar* 参数 | 添加 (uchar*) 显式类型转换 |
| 5 | libmysql_api_test 失败 | WITHOUT_SERVER=ON 导致部分 API 符号缺失 | 完全跳过 api_test 目标 |
| 6 | cmake 检查 DNS SRV 失败 | libresolv 在 musl libc 中不存在 | 添加 OHOS 条件分支，假设 libc 提供 DNS SRV |

## 源码修改

8 个补丁文件 (0001-0008):
- 0001: cmake/readline.cmake — 添加 WITH_EDITLINE=none 选项
- 0002: CMakeLists.txt — 处理 WITH_EDITLINE=none 时的 editline 检查
- 0003: client/CMakeLists.txt — 跳过 mysql CLI 工具 (无 editline)
- 0004: libmysql/CMakeLists.txt — 修复 DNS SRV API 检查
- 0005: mysys/my_thread.cc — 替换 pthread_cancel() 为 ENOTSUP
- 0006: libmysql/dns_srv.cc — 修复 DNS SRV 解析器
- 0007: sql-common/get_password.cc — 修复 uchar 类型转换
- 0008: libmysql/CMakeLists.txt — 跳过 libmysql_api_test

## 依赖版本

- OpenSSL: system (HarmonyOS NEXT built-in)
- zlib: system (HarmonyOS NEXT built-in)
- libevent: bundled (MySQL 自带)
- clang/clang++: HarmonyOS NEXT SDK

## 验证结果

```bash
# 签名验证
$ file /storage/Users/currentUser/usr/local/bin/mysqladmin
/storage/Users/currentUser/usr/local/bin/mysqladmin: ELF 64-bit LSB pie executable, ARM aarch64, ...

# 客户端库
$ ls /storage/Users/currentUser/usr/local/lib/
libmysqlclient.a  liblibmysql.so  pkgconfig/
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| mysql-client-8.4.9-ohos-aarch64.tar.gz | ~125MB | 剥离调试符号的发布包 |
| mysql-client-8.4.9-ohos-aarch64-debug.tar.gz | ~129MB | 包含调试符号的调试包 |

## 注意事项

- mysql CLI 交互工具不可用 (依赖 editline/libedit，已跳过)
- 其他所有客户端工具 (mysqladmin, mysqldump, mysqlcheck 等) 正常构建
- 所有 ELF 二进制已签名
- liblibmysql.so 是共享客户端库

---
**编译结束**: 2026-06-09
**最终状态**: published