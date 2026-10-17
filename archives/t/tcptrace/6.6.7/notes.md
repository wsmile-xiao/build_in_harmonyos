# tcptrace 6.6.7 适配笔记

## 编译环境
- 构建系统: autotools (Autoconf 2.52)
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 目标平台: aarch64-unknown-linux-ohos (OpenHarmony)

- 状态: built
- 安装路径: /storage/Users/currentUser/usr/local

## 编译步骤

1. `init-build` 下载并解压源码
2. 替换 `config.guess`/`config.sub` 为 automake-1.17 版本（识别 `aarch64-unknown-linux-ohos`）
3. 修改 `tcpdump.c`：将 `pcap_offline_read` 替换为 `pcap_dispatch`（现代 libpcap 已移除内部 API）
4. 修改 `configure`：`umask 077` → `umask 007`（HarmonyOS SGID 权限冲突）
5. 修改 `Makefile.in`：install/install-man 目标添加 `DESTDIR` 支持、移除 `-o/-g`、`BINDIR`/`MANDIR` 使用 `@prefix@`
6. 设置 `TMPDIR=$HOME/tmp` 解决 `/tmp` 只读问题
7. `./configure --prefix=$DEFAULT_PREFIX && make -j1 && make install DESTDIR=$TEST_PREFIX`
8. `make install` 本地安装验证
9. `package` 生成预编译包
10. `finish tcptrace 6.6.7 published`

## 遇到的问题与解决方案

| # | 问题 | 错误模式 | 根因 | 解决方案 |
|---|------|---------|------|----------|
| 1 | config.guess 无法识别平台 | E007 | 2001年旧版不支持 HarmonyOS | 替换为 automake-1.17 版本 |
| 2 | config.status 创建临时文件失败 | E002 + E082 | /tmp 只读 + umask 077 | TMPDIR=$HOME/tmp + umask 077→007 |
| 3 | pcap_offline_read 未定义 | E081 | 现代 libpcap 已移除内部 API | 替换为 pcap_dispatch |
| 4 | make install 失败 | E083 | 硬编码路径 + -o/-g 参数 | DESTDIR + @prefix@ + 移除 -o/-g |
| 5 | 压缩 pcap 文件只读 | 运行时发现 | gunzip 在 /tmp 创建临时文件 | 先解压再分析或设置 TMPDIR |

## 源码修改（共5处）

1. `config.guess` — 替换为 automake-1.17 版本
2. `config.sub` — 替换为 automake-1.17 版本
3. `configure` — umask 077 → umask 007（行 5512, 5517）
4. `Makefile.in` — BINDIR/MANDIR 使用 @prefix@、install 添加 DESTDIR + 移除 -o/-g
5. `tcpdump.c` — 移除 pcap_offline_read extern 声明，替换调用为 pcap_dispatch

> 注：原 0005-0007 号 bison/flex 生成文件补丁已移除，改为在 conanfile.py 中设置 YACC=bison -y 和 LEX=flex 环境变量，让 Makefile 在构建时用 bison 3.8.2 + flex 2.6.4 重新生成。

## 依赖
- libpcap（预编译包已安装在 /storage/Users/currentUser/usr/local/）

## 预编译包交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| tcptrace-6.6.7-ohos-aarch64.tar.gz | 675KB | 预编译包 |
| tcptrace-6.6.7-ohos-aarch64-debug.tar.gz | 120KB | 调试符号包 |

## 注意事项
- tcptrace 不支持 `--version` 参数，版本信息通过运行命令或 `-hargs`/`-hconfig` 获取
- tcptrace 无测试套件（`make check`/`test` 不存在）
- 分析压缩的 pcap 文件（.gz）时需先解压，或设置 `TMPDIR` 到可写目录再分析
- pcap_offline_read 是 libpcap 内部函数，在 1.x 版本中已移除，使用 pcap_dispatch 替代
- **环境变量**: 使用时需设置 `TMPDIR=$HOME/tmp`

---

**编译结束**: 2026-07-24
**最终状态**: built
hed
