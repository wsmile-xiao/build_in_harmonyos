# E999: autogen.sh 缺少 ltmain.sh 文件

## 错误现象

```
configure.ac:8: error: required file './ltmain.sh' not found
autoreconf: error: automake failed with exit status: 1
```

## 根因分析

autogen.sh 运行时调用 libtoolize，libtoolize 尝试复制 ltmain.sh 到源码目录，但由于：
1. 目录结构计算错误（相对路径）
2. libtool 版本不匹配
3. configure.ac 使用过时的 AC_PROG_LIBTOOL 宏

导致 ltmain.sh 无法正确复制到源码目录。

## 受影响范围

- autotools 项目
- 使用 AC_PROG_LIBTOOL 的旧版本 configure.ac
- libtool 2.4.x 版本

## 解决方案

手动复制 libtool 的 ltmain.sh 文件到源码目录：

```bash
cp $HOME/usr/local/share/libtool/build-aux/ltmain.sh .
./autogen.sh
```

## 验证方法

```bash
ls -la ltmain.sh
test -x configure
```

## 相关软件

- libxdg-basedir 1.2.3

## 贡献者

BD24 (2026-06-05)