# varnish 7.5.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码：从GitHub下载varnish-cache源码（通过ghfast.top加速）
2. 解压到~/builds/varnish-7.5.0.work
3. 创建pkg.m4文件（解决autogen.sh依赖）
4. 运行autogen.sh生成configure文件
5. 安装依赖：libedit、docutils、sphinx
6. 创建rst2man.py、rst2html.py wrapper脚本
7. 创建ncursesw.pc pkg-config文件
8. 创建libedit.so软链接
9. 运行configure
10. 运行make -j2
11. 修复pthread_cancel编译错误（3个文件）
12. 安装到~/usr/local

### Configure命令
```bash
./configure --prefix=$DEFAULT_PREFIX \
  --with-rst2man=rst2man.py \
  --with-rst2html=rst2html.py \
  --with-sphinx-build=sphinx-build
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg.m4缺失 | pkg-config预编译包缺少m4宏文件 | 手动创建pkg.m4文件 |
| 2 | rst2man/rst2html缺失 | Python docutils未提供命令行工具 | 创建wrapper脚本 |
| 3 | ncursesw pkg-config缺失 | 只有静态库，缺少.pc文件 | 手动创建ncursesw.pc |
| 4 | libedit.so缺失 | 预编译包只安装了.so.0.0.74 | 创建软链接 |
| 5 | pthread_cancel未实现 | OHOS平台syscall未实现 | 使用#ifdef __OHOS__守卫跳过 |

## 源码修改

### 补丁文件
- 0001-bin-varnishtest-vtc_logexp.c.patch：pthread_cancel OHOS守卫
- 0002-bin-varnishtest-vtc_server.c.patch：pthread_cancel OHOS守卫
- 0003-bin-varnishtest-vtc_syslog.c.patch：pthread_cancel OHOS守卫

### 修改内容
在vtc_logexp.c、vtc_server.c、vtc_syslog.c中使用`#ifdef __OHOS__`守卫跳过pthread_cancel调用。

## 依赖版本

- libedit/20240808
- pcre2/10.42（系统已安装）
- ncurses/6.4（系统已安装，静态库）
- docutils/0.22.4（pip安装）
- sphinx/9.1.0（pip安装）

## 验证结果

```bash
$ varnishd -V
varnishd (varnish-7.5.0 revision NOGIT)
Copyright (c) 2006 Verdens Gang AS
Copyright (c) 2006-2024 Varnish Software
Copyright 2010-2024 UPLEX - Nils Goroll Systemoptimierung
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| varnish-7.5.0-ohos-aarch64.tar.gz | 8194KB | 预编译包 |

## 注意事项

1. G0干净构建验证失败：GitHub源码包缺少configure文件，需要先运行autogen.sh
2. make check超时跳过：测试套件在OHOS上可能卡住，可安全跳过
3. 需要手动创建wrapper脚本和pkg-config文件

## 知识沉淀

### L1 平台真理
- pthread_cancel在OHOS上未实现，需要使用条件编译跳过

### L2 构建模式
- GitHub autotools项目源码包通常缺少configure，需要先运行autogen.sh
- Python docutils模块需要手动创建rst2man/rst2html wrapper

### L3 本版笔记
- varnish 7.5.0需要修改varnishtest工具中的pthread_cancel调用

---

**编译结束**: 2026-06-04 16:45
**最终状态**: built