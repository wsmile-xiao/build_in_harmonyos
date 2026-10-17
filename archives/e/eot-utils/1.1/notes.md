# eot-utils 1.1 适配笔记

## 编译环境
- 构建系统: autotools (autoconf 2.68)
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 编译参数: `-fPIC -O2`
- 状态: built (Conan 适配完成)

## 编译步骤

1. 初始化: `ohc-run.py init-build eot-utils 1.1 --url=https://www.w3.org/Tools/eot-utils/eot-utilities-1.1.tar.gz`
2. 修复 configure 脚本 umask 问题: `sed -i 's/umask 077/umask 007/g' configure`
3. 运行配置: `./configure --prefix=/storage/Users/currentUser/usr/local`
4. 编译: `make -j1`（HMDFS 不支持 jobserver FIFO，必须用 -j1）
5. 暂存安装: `make install DESTDIR=$TEST_PREFIX`（R20 DESTDIR 模式）
6. 测试检查: `make check`（无测试套件，exit 0）
7. 预编译包制作: `ohc-run.py package eot-utils 1.1`
8. 本地安装: `make install`（模拟用户部署）
9. 收尾: `ohc-run.py finish eot-utils 1.1 published`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报错 "can't create ./confXXXX/subs1.awk: Permission denied" | autoconf 2.68 的 config.status 使用 `umask 077` 创建临时目录，在 HMDFS 上进程 uid (20020082) ≠ 文件 owner uid (20001006)，导致无法写入 owner-only 权限目录 | `sed -i 's/umask 077/umask 007/g' configure`（改为 umask 007 允许组写入） |
| 2 | make -j2 报错 "jobserver mkfifo: Operation not permitted" | HMDFS 文件系统不支持 mkfifo 创建命名管道 | 使用 `make -j1` 替代 `-j2` |
| 3 | make 自动触发 autoconf 重生成报错 "cannot find config.guess config.sub" | configure 被 sed 修改后时间戳变化，触发 Makefile 的自动重生成规则，重生成的新 configure 需要 config.guess/config.sub 但源码未包含 | `touch` 修正时间戳顺序: configure.in < configure < config.status < Makefile |

## 源码修改

- **0001-configure.patch**:
  - 主要目的: 修改 configure 脚本中所有 `umask 077` 为 `umask 007`
  - 副作用: autoconf 自动重生成将 configure 从 2.68 升级到 2.72（+2255/-1762 行）
  - 实际生效的修改: umask 077 → umask 007（2 处）

## 功能测试结果

使用系统字体 `/system/fonts/FTAeroSans-Regular.ttf` 进行端到端测试：

- **mkeot 生成 EOT**: 成功将 TTF 字体转换为 EOT 格式（12058 字节）
- **eotinfo 解析 EOT**: 正确输出 EOT 头部信息（FamilyName: FT AeroSans, Weight: 400, fsType: no-subsetting 等）
- **eotinfo stdin 模式**: 管道输入正常工作
- **mkeot 多 URL**: 多个 URL 正确嵌入 RootString 字段
- **错误处理**: 无效输入/文件不存在均给出明确错误信息和正确的退出码

详细测试报告见 `reports/test-report.md`（17 项测试全部通过）。

## 依赖版本

无依赖（纯 C 工具，仅依赖 musl libc，readelf -d 显示无外部库依赖）。

## 验证结果

```
$ file bin/eotinfo  → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
$ file bin/mkeot     → ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)
$ readelf -h bin/eotinfo → Machine: AArch64, Type: DYN (PIE)
$ readelf -d bin/eotinfo → 无 NEEDED 条目（无外部库依赖）
```

## 交付物

| 文件 | 大小 | SHA256 | 说明 |
|------|------|--------|------|
| eot-utils-1.1-ohos-aarch64.tar.gz | 162KB | dcb30e39...dc515 | 预编译包（bin/eotinfo, bin/mkeot, man pages） |
| eot-utils-1.1-ohos-aarch64-debug.tar.gz | — | 61c9380a...b5dc9 | 调试符号包 |
| 0001-configure.patch | — | — | umask 077→007 平台适配补丁 |

## 注意事项

- eotinfo 和 mkeot 没有 `--version` 或 `--help` 标志（2010 年版本的预期行为）
- eotinfo 从 stdin 或文件参数读取 EOT 字体数据
- mkeot 第一个参数为 OTF/TTF 字体文件，后续参数为 URL 列表
- 二进制为 PIE（Position-Independent Executable），无外部库依赖
---

**编译结束**: 2026-08-06 09:08
**最终状态**: built
