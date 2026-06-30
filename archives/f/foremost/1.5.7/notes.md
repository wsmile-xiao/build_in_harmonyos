# foremost 1.5.7 适配笔记

## 编译环境
- 构建系统: makefile（纯 Makefile，无 configure 脚本）
- 编译日期: 2026-05-21
- 编译器: clang/clang++ (15.0.4)
- 平台: HarmonyOS (aarch64)
- 状态: built

## 编译步骤

foremost 是纯 Makefile 项目，无 configure 脚本。编译步骤如下：

1. `ohc-run.py init-build foremost 1.5.7 --url=https://foremost.sourceforge.net/pkg/foremost-1.5.7.tar.gz`（SSL 下载失败，需 curl -k 手动下载后使用 file:// URL）
2. 源码修改（4 个文件）→ 解决 HarmonyOS 平台适配和 duplicate symbol 问题
3. `make RAW_CC=clang PREFIX=$DEFAULT_PREFIX -j1`
4. `make RAW_CC=clang PREFIX=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX install`（DESTDIR 模式 staging）
5. R7 安全弹窗验证 → `foremost -V` 通过
6. `ohc-run.py package foremost 1.5.7`
7. `make install`（不带 DESTDIR，安装到 ~/usr/local）
8. `~/usr/local/bin/foremost -h` 验证可用
9. 功能测试（11 个用例全 PASS）
10. `ohc-run.py finish foremost 1.5.7 built`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 下载失败 | 源码 URL 使用 HTTPS，证书验证失败 | `curl -kL` 手动下载，使用 `file://` URL 传入 init-build |
| 2 | `uname -s` 返回 "HarmonyOS"，Makefile 无对应 target | Makefile 用 `$(shell uname -s)` 检测系统类型，HarmonyOS 不在列表中 | 添加 SYS_RAW 变量 + ifeq 条件映射 HarmonyOS → linux |
| 3 | ld.lld duplicate symbol 错误（__progname, wildcard, search_spec, signal_caught, dirlist, dl） | 头文件中全局变量未加 extern，clang/lld 不支持 GCC "common" 符号扩展 | 头文件声明改为 extern，main.c 添加实际定义；ole.h struct DIRECTORY 与变量声明分离 |
| 4 | Makefile 无 PREFIX/DESTDIR 支持 | 纯 Makefile 硬编码 BIN/MAN/CONF 路径，install 无 DESTDIR | 添加 `PREFIX ?= /usr/local` 和 `DESTDIR ?=`，BIN/MAN/CONF 引用 PREFIX，install 添加 DESTDIR 和目录创建 |
| 5 | RAW_CC 硬编码为 gcc | 环境变量 CC=clang，但 Makefile 使用 RAW_CC=gcc | 改为 `RAW_CC ?= gcc` 支持环境变量覆盖 |

## 源码修改

### 补丁列表（4 个）

| 补丁文件 | 修改文件 | 说明 |
|----------|----------|------|
| 0001-Makefile.patch | Makefile | SYS 映射 HarmonyOS→linux；RAW_CC 改为 ?=；添加 PREFIX/DESTDIR；install 支持 DESTDIR |
| 0002-main.c.patch | main.c | 添加全局变量定义（__progname, wildcard, search_spec, signal_caught, dirlist, dl） |
| 0004-main.h.patch | main.h | 全局变量声明改为 extern（__progname, wildcard, search_spec, signal_caught） |
| 0003-ole.h.patch | ole.h | struct DIRECTORY 定义与变量声明分离；变量声明改为 extern |

### 知识沉淀

- **E105 草稿**: 记录 clang/lld duplicate symbol 因头文件全局变量无 extern 的问题和解决方案
- 关键发现：HarmonyOS uname 返回 "HarmonyOS" 需映射到 "linux"

## 依赖版本

- 无外部依赖，仅依赖 libc.so

## 验证结果

11 个功能测试用例全部 PASS，详见 reports/test-report.md：
- T1-T2: 基础功能（版本号、帮助信息）
- T3-T6: 文件恢复（JPEG、GIF、PDF、多类型）
- T7-T8: 模式测试（快速模式、审计模式）
- T9: 配置文件测试
- T10-T11: 二进制完整性、安装文件检查

```bash
~/usr/local/bin/foremost -V    # 输出 1.5.7 版本信息
~/usr/local/bin/foremost -h    # 输出完整帮助信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| foremost-1.5.7-ohos-aarch64.tar.gz | 112KB | 预编译包（ELF 已签名，已 strip） |
| foremost-1.5.7-ohos-aarch64-debug.tar.gz | 61KB | 调试符号包 |
| 0001-Makefile.patch | 5KB | Makefile 平台适配补丁 |
| 0002-main.c.patch | 3KB | 全局变量定义补丁 |
| 0004-main.h.patch | 5KB | extern 声明补丁 |
| 0003-ole.h.patch | 1KB | ole.h 结构体分离补丁 |

## 注意事项

1. foremost 配置文件安装到 ~/usr/local/etc/foremost.conf（239 行），使用 -c 参数指定
2. 纯 Makefile 项目无 configure，G0 clean-verify 的 configure 步骤会失败（已知限制）
3. "foremost: : No such file or directory" 是首次运行时的无害警告（配置文件路径搜索）
4. stdin 模式（管道输入）在 HMDFS 上可能受限制，建议用 -i 文件模式

---
**编译结束**: 2026-05-25 16:09
**最终状态**: built