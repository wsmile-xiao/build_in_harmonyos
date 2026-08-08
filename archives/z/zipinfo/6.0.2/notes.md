# zipinfo 6.0 适配笔记

## 编译环境
- 构建系统: makefile（unix/Makefile generic）
- 编译日期: 2026-08-06
- 编译器: clang 15.0.4
- 状态: published

## 编译步骤

```bash
# zipinfo 是 Info-ZIP unzip 套件的一部分（unzip60.tar.gz 源码树）
tar xzf unzip60.tar.gz
cd unzip60
export TMPDIR=/storage/Users/currentUser   # E002: /tmp 只读
make -f unix/Makefile generic CC=clang -j1
# unix/Makefile 的 zipinfo 目标用 `ln unzip zipinfo`，
# HMDFS 不支持硬链接 → rm -f && cp unzip zipinfo（R5）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `ln unzip zipinfo` 报 Operation not permitted | HMDFS 不支持硬链接 | `cp unzip zipinfo` 代替 |
| 2 | make check 中 testsfx 自解压测试失败 | HMDFS 执行权限限制（E046 类平台限制） | 记录为平台限制，不阻塞；zipinfo 主二进制验证通过 |
| 3 | /tmp 只读导致 configure 测试失败 | E002 已知平台限制 | 设置 `TMPDIR` 指向可写目录 |

## 源码修改

无。zipinfo 使用上游源码直接编译，无需补丁（conandata.yml patches: []）。

## 依赖版本

无外部依赖（纯 C，仅系统 libc）。

## 验证结果

```bash
./zipinfo -v          # ZipInfo 3.00 of 20 April 2009 ✅
./zipinfo testmake.zip  # 列出 2 个条目，压缩率 28.5% ✅
# conan-verify G1-G4 全部 PASS；test_package 创建 zip 后 zipinfo 列出验证 ✅
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan 配方（makefile 构建 + OHOS ELF 签名 + TMPDIR） |
| conandata.yml | 源码声明（sha256 校验） |
| test_package/ | 消费者测试（创建 zip → zipinfo 列出 → 验证输出） |
| commands.json | 命令行工具声明（R38） |

## 注意事项

- zipinfo 二进制实际是 unzip 的复制（Unix 上二者行为由 argv[0] 区分）
- ELF 签名依赖 `/data/service/hnp/bin/binary-sign-tool`，本地无此工具时跳过签名（配方中已处理）
---

**编译结束**: 2026-08-06 13:18
**最终状态**: published
