# aspell 0.60.8 适配笔记

## 编译环境
- 构建系统: autotools (configure + make)
- 编译日期: 2026-08-24
- 编译器: clang/clang++ (version 15.0.4, aarch64-unknown-linux-ohos target)
- 状态: built

## 编译步骤

1. 下载源码: `curl -L -o aspell-0.60.8.tar.gz https://ftp.gnu.org/gnu/aspell/aspell-0.60.8.tar.gz`
2. 解压源码到 .work 和 .orig 目录 (init-build 自动完成)
3. 应用 config.guess/config.sub 补丁 (更新到 2022 版本以识别 aarch64-linux-ohos)
4. 修复 configure 脚本中的 `umask 077` → `umask 022` (HMDFS 文件系统兼容)
5. 配置:
   ```bash
   CONFIG_SHELL=/data/service/hnp/bin/bash \
   LDFLAGS="-fuse-ld=bfd -L$PREFIX/lib" \
   CXXFLAGS="-fPIC -O2 -I$PREFIX/include" \
   CFLAGS="-fPIC -O2 -I$PREFIX/include" \
   ./configure --prefix=$PREFIX \
     --enable-curses=ncurses \
     --build=x86_64-unknown-linux-gnu \
     --host=aarch64-linux-ohos
   ```
6. 编译: `make -j1` (HMDFS FIFO jobserver 不支持 -j2)
7. 安装: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | C++ 编译器无法创建可执行文件 | lld 链接器运行时依赖 libxml2.so.16 缺失 (OHOS 系统 /lib 目录无此库) | LDFLAGS 添加 `-fuse-ld=bfd` 使用 bfd 链接器 |
| 2 | configure 报 "cannot run C++ compiled programs" | OHOS 安全模型阻止执行新编译的二进制文件 (Permission denied) | 使用 `--build=x86_64-unknown-linux-gnu --host=aarch64-linux-ohos` 触发交叉编译模式, 跳过运行时测试 |
| 3 | config.status 报 "Permission denied" 创建 subs1.awk | autoconf 2.69 的 config.status 使用 `umask 077` 创建临时目录, HMDFS 文件系统对 drwx------ 目录拒绝文件创建 | 在 configure 脚本中将 `umask 077` 替换为 `umask 022` |
| 4 | config.sub 不识别 aarch64-linux-ohos | 上游 config.sub 为 2014 版本, 不支持 OHOS 平台 | 应用 0002-config.sub.patch 更新到 2022 版本 |
| 5 | make -j2 报 "jobserver mkfifo: Operation not permitted" | HMDFS 文件系统不支持 FIFO 管道 | 使用 `make -j1` |
| 6 | manual/ 子目录编译失败 (缺 makeinfo) | 需要 texinfo 工具, 非关键路径 | 忽略, 库和二进制已成功构建 |

## 源码修改

| 文件 | 修改内容 |
|------|----------|
| config.guess | 更新到 2022-01-09 版本, 支持 aarch64-linux-ohos 平台检测 |
| config.sub | 更新到 2022-01-03 版本, 支持 aarch64-linux-ohos 三元组验证 |
| configure | `umask 077` → `umask 022` (运行时修复, 不作为补丁) |

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| ncurses | 6.6 | Conan 制品仓 (ohpcd remote) |
| clang | 15.0.4 | OHOS SDK |

## 验证结果

```bash
# 库文件
$ ls -la .libs/libaspell.a .libs/libpspell.a
-rw-rw---- libaspell.a (1.4MB)
-rw-rw---- libpspell.a (1KB)

# 二进制文件
$ ls -la aspell word-list-compress prezip-bin
-rwxrwx--- aspell (735KB)
-rwxrwx--- word-list-compress (20KB)
-rwxrwx--- prezip-bin (20KB)

# 头文件
$ ls interfaces/cc/
aspell.h  pspell.h  Makefile.in
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libaspell.a | 1.4MB | 主拼写检查库 (静态) |
| libpspell.a | 1KB | pspell 兼容库 (静态, 重导出 libaspell 符号) |
| aspell | 735KB | 拼写检查 CLI 工具 |
| word-list-compress | 20KB | 词表压缩工具 |
| prezip-bin | 20KB | 预压缩工具 |
| aspell.h | - | C API 头文件 |
| pspell.h | - | pspell 兼容 API 头文件 |

## 注意事项

1. **lld 链接器问题**: OHOS 平台上的 lld 链接器运行时需要 libxml2.so.16, 但该库不在系统默认搜索路径中。使用 `-fuse-ld=bfd` 绕过此问题。
2. **交叉编译模式**: 即使是原生编译, 也需要使用 `--build` ≠ `--host` 来触发交叉编译模式, 因为 OHOS 安全模型阻止执行新编译的二进制文件。
3. **umask 077 修复**: autoconf 2.69 生成的 config.status 使用 `umask 077` 创建临时目录, 在 HMDFS 上会导致权限拒绝。需要在构建前将 configure 脚本中的 `umask 077` 替换为 `umask 022`。
4. **ncurses 依赖**: aspell 的交互式拼写检查器需要 ncurses 库。使用 `--enable-curses=ncurses` 在交叉编译模式下直接设置库引用, 无需运行时检测。
5. **静态构建**: 默认使用静态构建 (shared=False), 避免 OHOS RPATH 解析问题。
---

**编译结束**: 2026-08-25 00:42
**最终状态**: built


