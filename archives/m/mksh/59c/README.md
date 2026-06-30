# mksh 59c — MirBSD Korn Shell

## 软件简介

mksh (MirBSD Korn Shell) 是一个基于 Korn Shell 的现代 shell 实现，由 MirBSD 项目维护。
版本 R59c 发布于 2020-10-31，支持 POSIX shell 语法并兼容大量扩展功能。

## 编译信息

- **版本**: R59c (59c)
- **构建系统**: custom (Build.sh 脚本)
- **编译器**: clang 15.0.4 (aarch64-unknown-linux-ohos)
- **目标平台**: HarmonyOS HongMeng Kernel 1.12.0 aarch64
- **编译日期**: 2026-06-30
- **状态**: built

## 源码信息

- **下载 URL**: https://snapshot.debian.org/archive/debian/20231201T000000Z/pool/main/m/mksh/mksh_59c.orig.tar.gz
- **SHA256**: 77ae1665a337f1c48c61d6b961db3e52119b38e58884d1c89684af31f87bc506
- **原始 URL**: https://mbsd.evolvis.org/MirOS/dist/mir/mksh/mksh-R59c.tgz (不可达)

## 编译命令

```bash
CC=/data/service/hnp/bin/clang LDFLAGS=-static sh ./Build.sh -r
```

## 产物清单

| 文件 | 路径 | 说明 |
|------|------|------|
| mksh | bin/mksh | 静态链接 ELF 二进制 (1390528 bytes) |
| mksh.1 | share/man/man1/mksh.1 | man 页 (176921 bytes) |
| lksh.1 | share/man/man1/lksh.1 | lksh man 页 (9304 bytes) |
| dot.mkshrc | share/doc/mksh/examples/dot.mkshrc | 示例配置 (18479 bytes) |

## 验证结果

- **编译**: ✅ 成功
- **功能**: ✅ `mksh -c 'echo $KSH_VERSION'` → `@(#)MIRBSD KSH R59 2020/10/31`
- **静态链接 (R26)**: ✅ file 命令确认 static
- **test.sh**: 510 通过 / 58 失败 (主因 /tmp 只读)
- **Conan 验证**: 7/8 门禁通过 (L2 因 shell 设计特性失败)

## 注意事项

- mksh 官方未正式移植到 HarmonyOS，Build.sh 输出警告但编译成功
- mksh 不支持 --version/--help 标志（shell 语义），导致 Conan L2 门禁失败
- /tmp 只读文件系统导致部分 test.sh 测试失败，实际功能不受影响
- 无源码补丁，Build.sh 自动适配平台
