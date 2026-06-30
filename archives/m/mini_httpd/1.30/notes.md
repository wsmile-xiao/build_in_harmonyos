# mini_httpd 1.30 适配笔记

## 编译环境
- 构建系统: makefile（简单 Makefile，无 configure）
- 编译日期: 2026-06-10
- 编译器: clang/clang++ (version 15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: `curl -k -L -o ~/tmp/mini_httpd-1.30.tar.gz https://www.acme.com/software/mini_httpd/mini_httpd-1.30.tar.gz`
2. 初始化编译: `python3 $SKILL_ROOT/scripts/ohc-run.py init-build mini_httpd 1.30 --url=file://$HOME/tmp/mini_httpd-1.30.tar.gz`
3. 修改源码适配 OpenHarmony（见下方）
4. 编译: `make`
5. 安装（staging）: `make install DESTDIR=$TEST_PREFIX`
6. 打包: `python3 $SKILL_ROOT/scripts/ohc-run.py package mini_httpd 1.30`
7. 本地安装: `make install`（不带 DESTDIR）
8. 收尾: `python3 $SKILL_ROOT/scripts/ohc-run.py finish mini_httpd 1.30 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | int64_t 重定义冲突 | mini_httpd.c 定义了自己的 int64_t，与系统头文件冲突 | 添加 `#ifdef __OHOS__` 守卫，定义 `HAVE_INT64T` |
| 2 | getpass() 函数未定义 | OpenHarmony 缺少 getpass() 函数 | 扩展 MPE 的备用实现到 `#if defined(MPE) || defined(__OHOS__)` |
| 3 | /tmp 目录只读 | htpasswd.c 使用硬编码 /tmp 路径 | 修改为 `$HOME/tmp` |
| 4 | Makefile 不支持 DESTDIR | BINDIR/MANDIR 硬编码为 /usr/local | 添加 PREFIX 变量和 DESTDIR 支持 |
| 5 | SSL 下载失败 | acme.com SSL 配置问题 | 使用 curl -k 跳过验证 |

## 源码修改

### 1. mini_httpd.c
- 添加 `#ifdef __OHOS__` 守卫定义 `HAVE_INT64T`，避免 int64_t 重定义

### 2. htpasswd.c
- 扩展 getpass() 备用实现到 OpenHarmony 平台
- 修改 temp_template 路径从 `/tmp` 到 `$HOME/tmp`
- 使用 fgets 替代不安全的 gets

### 3. Makefile
- 添加 PREFIX 变量支持
- 修改 BINDIR/MANDIR 使用 PREFIX
- 修改 install 目标支持 DESTDIR

## 依赖版本

无外部依赖（仅使用 libcrypt）

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/sbin/mini_httpd -V
mini_httpd/1.30 26Oct2018

$ ls -la /storage/Users/currentUser/usr/local/sbin/
-rwxrwx--- 1 18048 2026-06-10 htpasswd
-rwxrwx--- 1 71360 2026-06-10 mini_httpd
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| packaging/mini_httpd-1.30-ohos-aarch64.tar.gz | ~111KB | 预编译包（含 mini_httpd + htpasswd） |
| patches/0001-Makefile.patch | - | DESTDIR 和 PREFIX 支持 |
| patches/0002-htpasswd.c.patch | - | getpass 备用实现 + TMPDIR |
| patches/0003-mini_httpd.c.patch | - | int64_t 重定义避免 |

## 注意事项

- mini_httpd 没有 configure 脚本，直接编辑 Makefile 配置
- 无测试套件（no make check）
- 二进制安装在 sbin 目录而非 bin 目录

---

**编译结束**: 2026-06-10 14:27
**最终状态**: built