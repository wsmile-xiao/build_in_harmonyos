# SQLite 3.46.0 适配笔记

## 编译环境
- 构建系统: Makefile.fallback (非标准 autotools)
- 编译日期: 2026-05-28
- 编译器: cc/clang++
- 状态: built

## 编译步骤

由于 HMDFS 文件系统限制,标准 configure 流程无法在源码目录创建临时文件。
采用 Makefile.fallback 进行编译:

1. 修改 config.guess 和 config.sub 以支持 HarmonyOS/OHOS 平台识别
2. 使用 Makefile.fallback 替代 configure 生成的 Makefile
3. 修改 Makefile.fallback: CC=cc, CFLAGS=-O2
4. 编译: make -j1
5. 安装到本地: 手动复制到 ~/usr/local

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别系统 | 不支持 HarmonyOS | 添加 HarmonyOS case 分支,返回 aarch64-unknown-linux-ohos |
| 2 | config.sub 验证失败 | 不识别 ohos 操作系统 | 添加 ohos* 到 OS 白名单,添加 linux-ohos* 到 kernel-os 白名单 |
| 3 | configure 无法创建临时文件 | HMDFS 文件系统限制 | 使用 Makefile.fallback 直接编译 |
| 4 | make 使用 gcc | Makefile.fallback 默认使用 gcc | 修改 Makefile: CC=cc |

## 源码修改

- config.guess: 添加 HarmonyOS 识别
- config.sub: 添加 OHOS 支持
- Makefile: 基于 Makefile.fallback,修改编译器为 cc

## 依赖版本

无外部依赖(仅需要系统 zlib)

## 验证结果

```bash
$ sqlite3 --version
3.46.0 2024-05-23 13:25:27 96c92aba00c8375bc32fafcdf12429c58bd8aabfcadab6683e35bbb9cdebf19e (64-bit)
```

## 交付物

- sqlite3 可执行文件 (1.3M)
- sqlite3.h 头文件
- sqlite3ext.h 头文件

## 注意事项

1. 由于使用 Makefile.fallback,未生成共享库(.so),仅生成可执行文件
2. 编译选项中禁用了线程安全和动态扩展加载
3. 如需标准 autotools 流程,需要在非 HMDFS 目录(如 /tmp)运行 configure
---

**编译结束**: 2026-05-28 10:43
**最终状态**: built
