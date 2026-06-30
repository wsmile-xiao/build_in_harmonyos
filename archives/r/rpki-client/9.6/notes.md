# rpki-client 9.6 适配笔记

## 编译环境
- 构建系统: custom（手动编译）
- 编译日期: 2026-06-11
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

由于 HMDFS 文件系统限制导致 configure/config.status 无法创建临时文件，采用手动编译流程：

1. **创建 config.h**：手动定义 HAVE_* 宏和路径配置
2. **编译源文件**：
   ```bash
   clang -c src/*.c -I. -I./include -I./compat -I~/usr/local/include
   clang -c compat/*.c（选择需要的兼容函数）
   ```
3. **链接**：
   ```bash
   clang *.o -L~/usr/local/lib -lfts -ltls -lssl -lcrypto -lexpat -lz -lpthread -ldl -o rpki-client
   ```
4. **安装**：复制到 ~/usr/local/sbin/ 和 ~/usr/local/etc/rpki/

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | HMDFS 临时文件限制 | HarmonyOS 分布式文件系统不支持 shell 脚本临时文件创建 | 手动创建 config.h，绕过 configure |
| 2 | 缺少 libtls | rpki-client 需要 LibreSSL（非 OpenSSL）的 libtls | 编译 LibreSSL 3.9.2，使用 CMAKE_SYSTEM_NAME=Linux |
| 3 | BIO_sock_init 符号缺失 | LibreSSL CMake 未识别为 UNIX，未编译 b_posix.c | 重新配置 CMAKE_SYSTEM_NAME=Linux |
| 4 | fts_open 符号缺失 | OpenHarmony 缺少 fts 文件树遍历函数 | 编译 musl-fts 静态库 |
| 5 | setgroups 类型冲突 | include/unistd.h 与系统头文件重复声明 | 移除 setgroups 声明 |
| 6 | 字节序函数缺失 | htobe16/be16toh 等宏未定义 | 创建 endian.h 兼容性头文件 |

## 源码修改

| 补丁 | 文件 | 说明 |
|------|------|------|
| 0001-include-unistd-harmony.patch | include/unistd.h | OpenHarmony 兼容性 shim，移除 setgroups 冲突 |
| 0002-include-endian-harmony.patch | include/endian.h | 字节序转换宏定义 |
| 0003-config-h-manual.patch | config.h | 手动配置文件，定义 HAVE_* 宏 |

## 依赖版本

| 软件 | 版本 | 说明 |
|------|------|------|
| LibreSSL | 3.9.2 | 提供 libcrypto, libssl, libtls（静态链接） |
| musl-fts | 1.2.1 | 文件树遍历函数（静态链接） |
| expat | 2.6.4 | XML 解析（动态链接） |
| zlib | 1.3.1 | 压缩库（静态链接） |
| rsync | 3.3.0 | RPKI 数据同步工具 |

## 验证结果

```bash
$ ~/usr/local/sbin/rpki-client -V
rpki-client-portable 9.6

$ file ~/usr/local/sbin/rpki-client
ELF shared object, 64-bit LSB arm64, dynamic

$ ldd ~/usr/local/sbin/rpki-client
libexpat.so => /storage/Users/currentUser/usr/local/lib/libexpat.so
libc.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rpki-client-9.6-ohos-aarch64.tar.gz | 2.0 MB | 预编译包（包含二进制+配置） |
| rpki-client | 2.3 MB | 可执行文件 |

## 注意事项

1. **HMDFS 限制**：configure 无法在 HMDFS 挂载点创建临时文件，后续编译需使用手动方式
2. **LibreSSL 必需**：rpki-client 依赖 LibreSSL 的 libtls，不能使用 OpenSSL
3. **静态链接**：LibreSSL 和 musl-fts 需静态链接到二进制中
4. **RIR TAL 文件**：安装时需复制 5 个 RIR 的 TAL 文件到 /usr/local/etc/rpki/
