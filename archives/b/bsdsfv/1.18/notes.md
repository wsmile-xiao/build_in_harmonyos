# bsdsfv 1.18 适配笔记

## 编译环境
- 构建系统: Makefile（单文件 C，bsdsfv.c）
- 编译日期: 2026-09-05
- 编译器: clang 15.0.4 (aarch64-linux-ohos)
- 状态: built

## 上游身份与源码源
- 软件: bsdsfv（命令行 SFV 校验工具，基于 pdsfv，作者 webbie@ipfw.org）
- 源码: `$Revision: 1.18$` 确认版本 1.18
- 源码源: SourceForge 官方项目（https://downloads.sourceforge.net/project/bsdsfv/bsdsfv/1.18/bsdsfv-1.18.tar.gz，实测 2026-09-05 可下载，13,301B，sha256=577245da...88495）
- 说明: 官方 tarball 内 bsdsfv.c 为 `$Id: bsdsfv.c,v 1.18 2003/10/05 ...`，$Revision 1.18 一致；GitHub 镜像（code.google.com 导出）与其仅 Id/Copyright 元信息差异，代码主体一致

## 编译步骤
1. 获取源码（SourceForge 官方 1.18 tarball，13KB）
2. `make CC=clang CFLAGS="-Wall -O2"` → 生成 bsdsfv 可执行文件
3. 鸿蒙 ELF 签名三步：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -inFile -outFile -selfSign 1` → `chmod +x`
4. make install 缺 `/usr/bin/install`：手动 cp 至 staging

## 源码修改（见 patches/，两处）

| # | 问题 | 根因 | 修复 |
|---|------|------|------|
| 1 | 运行必现 Usage（getopt 死循环） | `char ch` 接收 `getopt()` int 返回值，aarch64 char 无符号，`-1`(EOF) 转 255 后 `ch != -1` 恒真，落入 default→usage | `char ch` → `int ch` |
| 2 | CRC 高位为 1 的文件校验误判 BAD | `SFVTABLE.crc` 为有符号 `int`，`sscanf("%X")` 读入 0xF20B1EEB 变负值，与 64 位 `unsigned long mycrc` 比较符号扩展不等 | `int crc` → `unsigned int crc` |

## 功能验证（完整闭环）
- 创建 SFV：`bsdsfv -c -a check.sfv alpha.txt beta.txt` → CRC 正确输出（0x02EB2270 / 0xF20B1EEB）
- 校验：`-T` 全 OK（含 CRC 高位为 1 的 beta）
- 篡改：alpha 篡改后 `-T` 报 1 BAD（RC=1）
- 缺失：删除 beta 后 `-T` 报 1 MISSING；`-m` 统计缺失 1 (RC=0/2)

## 产物
- bsdsfv 可执行（ELF arm64, strip 后 18KB）
- 无外部依赖（纯 C，仅 libc+musl）

## 特性说明（关闭的选项）
- 无 configure/option；功能全量保留（-c 创建 / -t 单文件测试 / -T 全 SFV 测试 / -m 缺失统计 / -a 全文件模式 / -l banner / -w win-sfv 兼容 / -d 时间戳 / -g glftpd 模式）
---

**编译结束**: 2026-09-05 12:14
**最终状态**: built
