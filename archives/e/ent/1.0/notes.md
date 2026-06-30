# ent 1.0 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-04
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码包：`curl -L -k -o ent-1.0.tar.gz https://github.com/psm14/ent/archive/refs/tags/1.0.tar.gz`
2. 解压源码：`tar -xzf ent-1.0.tar.gz`
3. 修改 Makefile：修改编译器为 clang，添加 -fuse-ld=bfd 链接器选项
4. 编译：`make`
5. 签名 ELF：`ohc-run.py sign-elf ent`
6. 测试：`make check`
7. 安装到 staging 目录：`cp ent $TEST_PREFIX$DEFAULT_PREFIX/bin/`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | SSL 证书验证失败下载源码失败 | 鸿蒙环境 SSL 证书配置问题 | 使用 curl -k 禁用 SSL 验证 |
| 2 | make: gcc: No such file or directory | Makefile 默认使用 gcc | 修改 Makefile 中 CC = gcc 为 CC = clang |
| 3 | lld 链接器缺少 libxml2.so.16 | 鸿蒙 SDK 中 lld 工具依赖缺失 | 添加 -fuse-ld=bfd 使用 bfd 链接器 |
| 4 | ./ent: Permission denied | 未签名的 ELF 在鸿蒙上无法执行 | 使用 ohc-run.py sign-elf 签名 |

## 源码修改

- Makefile：修改 CC 从 gcc 到 clang，链接命令添加 -fuse-ld=bfd
- 补丁文件：0001-use-clang-and-bfd-linker.patch

## 依赖版本

- 无外部依赖
- 构建工具：clang (系统自带), make

## 验证结果

```bash
$ cd ~/tmp/ent-1.0-modified
$ make check
sh entest.bat
diff entest.mas entest.bak
# 测试通过，输出与预期一致
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ent-1.0-ohos-aarch64.tar.gz | 待生成 | 预编译包 |

## 注意事项

- 该软件为简单 Makefile 项目，无 configure 阶段
- 链接器问题是鸿蒙常见问题，优先使用 bfd 链接器
- ELF 签名是执行前的必要步骤
---

**编译结束**: 2026-06-04 23:14
**最终状态**: published
