# openfortivpn 1.24.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-05-28
- 编译器: clang/clang++
- 状态: published

## 编译步骤

### 步骤1：使用TMPDIR workaround
由于HMDFS文件系统限制config.status在源码目录创建临时文件，本次使用TMPDIR workaround方案：
- 将源码解压到$TMPDIR/build-openfortivpn-1.24.1
- 在TMPDIR中执行configure和编译
- 避免在HMDFS上创建临时文件

### 步骤2：修复automake Perl模块问题
- 设置PERL5LIB="/storage/Users/currentUser/usr/local/share/automake-1.16:$PERL5LIB"
- 设置AUTOCONF="/data/service/hnp/bin/autoconf"
- 运行autoreconf -fi生成configure脚本

### 步骤3：修复E011问题
- 修改configure脚本中的umask 077为umask 022
- 命令：sed -i 's/umask 077/umask 022/g' configure

### 步骤4：修复E051问题
- 修改configure.ac，移除pthread_cancel的检查
- 修改src/io.c，使用#ifdef __OHOS__守卫跳过pthread_cancel调用

### 步骤5：编译和安装
```bash
export DEFAULT_PREFIX="$HOME/usr/local"
export PKG_CONFIG_PATH="$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH"
./configure --prefix=$DEFAULT_PREFIX
make -j2
make install DESTDIR=$TEST_PREFIX
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | automake Perl模块找不到 | automake模块路径不在Perl @INC中 | 设置PERL5LIB环境变量包含automake-1.16目录 |
| 2 | configure Permission denied | HMDFS umask 077导致临时目录不可写 | 修改configure中的umask 077为umask 022 (E011) |
| 3 | pthread_cancel not found | HarmonyOS不支持pthread_cancel syscall | 使用#ifdef __OHOS__守卫跳过pthread_cancel调用 (E051) |

## 源码修改

### configure.ac
- 移除pthread_cancel的AC_CHECK_FUNCS检查
- 位置：configure.ac第130行

### src/io.c
- 添加#ifdef __OHOS__守卫，跳过pthread_cancel调用
- 位置：src/io.c第718-743行
- 在鸿蒙平台上，线程取消功能不可用，使用pthread_join等待线程自然结束

### configure
- 修改umask 077为umask 022
- 位置：configure脚本多处

## 依赖版本

- openssl: 3.5.6
- pkg-config: 0.29.2
- automake: 1.16.5
- autoconf: 2.72

## 验证结果

```bash
$ openfortivpn --version
1.24.1
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| openfortivpn-1.24.1-ohos-aarch64.tar.gz | 281K | 预编译包 |

## 注意事项

- 本次编译使用TMPDIR workaround，必须在$TMPDIR中构建，不能在默认的builds目录构建
- 这是绕过HMDFS权限限制的关键方案
- pthread_cancel在鸿蒙平台不可用，该功能已禁用，可能影响VPN连接断开时的线程清理效率