# SQLCipher

## 软件简介
SQLCipher是一个开源的SQLite扩展，提供透明的256位AES加密数据库文件支持。它是SQLite的一个独立分支，增加了数据库文件加密和其他安全功能。

## 官方网站
https://www.zetetic.net/sqlcipher/

## 许可证
BSD-3-Clause

## 编译说明

### 构建系统
- autosetup

### 关键依赖
- OpenSSL 3.x（SQLCipher 4.16.0+ 需要 OpenSSL 3.0 或更高版本）

### 平台适配
需要修改 autosetup-config.guess 和 autosetup-config.sub 以支持 HarmonyOS 平台识别。

### 编译参数示例
```bash
./configure \
  --prefix=$DEFAULT_PREFIX \
  --with-tempstore=yes \
  CFLAGS="-DSQLITE_HAS_CODEC -DSQLITE_EXTRA_INIT=sqlcipher_extra_init -DSQLITE_EXTRA_SHUTDOWN=sqlcipher_extra_shutdown" \
  LDFLAGS="-L$DEFAULT_PREFIX/lib -lcrypto -lssl"
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 注意事项
1. SQLCipher 4.16.0 及以上版本移除了对 OpenSSL < 3.0 的支持
2. 需要定义 SQLITE_HAS_CODEC, SQLITE_EXTRA_INIT, SQLITE_EXTRA_SHUTDOWN 宏
3. 部分版本可能缺少 install 命令，需要手动安装文件

## 版本索引

### 已编译版本
| 版本 | 状态 | 编译日期 | 说明 |
|------|------|---------|------|
| 4.16.0 | built | 2026-05-20 | 首次编译，支持 HarmonyOS |

### 版本依赖关系
- 4.16.0+ → OpenSSL 3.x（必需）