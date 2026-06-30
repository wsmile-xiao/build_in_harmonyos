# cmatrix 2.0-r2 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-03
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `autoreconf -fi` — 从 configure.ac 生成 configure 脚本及辅助文件
2. 复制 automake 版 config.guess/config.sub，识别 `aarch64-unknown-linux-ohos` (E007)
3. 修补 config.status：HMDFS 上 `umask 077 && mktemp -d "./confXXXXXX"` 创建的临时目录权限为 700，导致子目录内文件写入失败。修改为使用 `$TMPDIR/confXXXXXX` 并移除 umask 077
4. `./configure --prefix=$DEFAULT_PREFIX` — 检测到 ncurses 库
5. `make -j2` — 编译 cmatrix.c 生成 cmatrix 可执行文件
6. `make install DESTDIR=$TEST_PREFIX` — staging 安装
7. `make install` — 本地安装到 $DEFAULT_PREFIX（模拟用户部署）
8. ELF 签名 + 打包

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | GitHub 下载超时 | 网络限制 | 使用 ghfast.top 镜像下载 |
| 2 | config.guess/config.sub 缺失 | 项目源码中无这些文件 | autoreconf -fi 后从 automake 复制 |
| 3 | config.status 创建临时文件 Permission denied | HMDFS 上 umask 077 创建的 700 权限目录内无法写入文件 | 修改 config.status 使用 $TMPDIR 并移除 umask 077 |

## 源码修改

- config.guess: 从 automake-1.16 复制（支持 aarch64-unknown-linux-ohos）
- config.sub: 从 automake-1.16 复制（支持 linux-ohos 三元组）
- config.status: HMDFS umask 077 workaround（使用 $TMPDIR，移除 umask 077）

## 依赖版本

- ncurses: 6.4 (--without-shared)
- clang: 15.0.4
- automake: 1.16.5

## 验证结果

```bash
/storage/Users/currentUser/usr/local/bin/cmatrix -V
CMatrix version 2.0 (compiled 11:52:56, Jun  3 2026)
Email: abishekvashok@gmail.com
Web: https://github.com/abishekvashok/cmatrix
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| cmatrix-2.0-r2-ohos-aarch64.tar.gz | 317KB | 预编译包 |

## 注意事项

- cmatrix 是终端 screensaver，需要 ncurses 库
- configure 中的字体/consolechars 警告不影响核心功能
- HMDFS umask 077 限制：此 workaround 需记录为通用平台知识

---

**编译结束**: 2026-06-03 11:57
**最终状态**: published
---

**编译结束**: 2026-06-03 12:10
**最终状态**: built
