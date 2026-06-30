# t1utils 1.42 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-12
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. `./configure --prefix=$DEFAULT_PREFIX`（需修改 config.guess/config.sub 和 configure 中的 umask 临时目录创建代码）
2. `make -j1`
3. `make install DESTDIR=$TEST_PREFIX`
4. `make check`（无测试套件，仅确认构建成功）
5. staging 验证：6个二进制全部 `--version` 正常
6. `ohc-run.py package` 打包
7. `make install`（本地安装验证）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别平台 | 旧版 config.guess（2020-08-17）不包含 __OHOS__ 检测 | 替换为已包含 ohos 支持的 2023 版 config.guess |
| 2 | config.status 创建临时目录失败 (Permission denied) | HMDFS 继承父目录 setgid，`umask 077 && mktemp -d` 创建 2700 权限目录导致无法写入文件 | 修改 configure 中临时目录创建逻辑：去掉 umask 077，改用 `mktemp -d` + `mkdir -m 0770` |

## 源码修改

- 0001-config.guess.patch: 替换为含 __OHOS__ 检测的版本（+711/-575）
- 0002-config.sub.patch: 替换为含 ohos 支持的版本（+217/-102）
- 0003-configure.patch: 修改临时目录创建逻辑，去掉 umask 077（+2/-2）

## 依赖版本

无外部依赖（t1utils 是纯 C 命令行工具）

## 验证结果

```bash
$ t1ascii --version
t1ascii (LCDF t1utils) 1.42
$ t1binary --version
t1binary (LCDF t1utils) 1.42
$ t1asm --version
t1asm (LCDF t1utils) 1.42
$ t1disasm --version
t1disasm (LCDF t1utils) 1.42
$ t1unmac --version
t1unmac (LCDF t1utils) 1.42
$ t1mac --version
t1mac (LCDF t1utils) 1.42
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| t1utils-1.42-ohos-aarch64.tar.gz | 510KB | 预编译包（6个二进制 + man pages） |
| t1utils-1.42-ohos-aarch64-debug.tar.gz | - | 调试符号包 |

## 注意事项

- HMDFS 平台上 `umask 077 && mkdir` 创建的目录权限为 2700（setgid 无组写），即使 owner 也无法在其中创建文件。必须使用 `mkdir -m 0770` 或不带 umask 的 `mktemp -d`。
- 此 HMDFS 临时目录问题为 L1 级平台真理，可能影响所有 autotools 软件。
---

**编译结束**: 2026-06-12 04:27
**最终状态**: published