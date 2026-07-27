# heirloom-doctools 191015 适配笔记

## 编译环境
- 构建系统: makefile (自定义 configure)
- 编译日期: 2026-05-22
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **初始化**: `ohc-run.py init-build heirloom-doctools 191015`
   - 源码下载: https://github.com/n-t-roff/heirloom-doctools (通过 ghproxy.net 镜像)
   - 解压到: /data/storage/el2/base/cache/builds/heirloom-doctools-191015.work

2. **Configure**: 项目使用自定义 configure 脚本（非 autotools）
   - 自动检测 flex、lex、strlcpy、strlcat 等功能
   - 生成 cfg.mk 配置文件

3. **编译**: `make` 在各子目录执行
   - 编译组件: eqn, neqn, tbl, pic, grap, vgrind, refer, troff, nroff, dpost, dhtml 等
   - 无标准 Makefile，顶层使用小写 `makefile` 驱动子目录

4. **安装**: `make install` (直接安装到 ~/usr/local)
   - 注意: 此项目不支持 DESTDIR 模式，直接安装到 PREFIX
   - 安装路径: ~/usr/local/ucb (二进制), ~/usr/local/ucblib (库/数据), ~/usr/local/share (手册)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | eqn/neqn.d, checkeq.d 缺少 eqn.1 | Makefile 假设 eqn.1 在当前目录 | 手动复制 eqn/eqn.d/eqn.1 到各目录 |
| 2 | font/devps 缺少 charlib | Makefile 路径错误 (`../devpost/charlib`) | 手动复制 devpost/charlib 到 devps |
| 3 | refer/papers/runinv 权限错误 | HMDFS 限制执行权限 | 跳过此步骤，不影响核心功能 |
| 4 | ELF 签名缺失 | 鸿蒙系统要求签名 | 使用 `ohc-run.py sign-elf` 签名所有二进制 |

## 源码修改

已生成 16 个补丁文件:
- 0001-eqn-checkeq.d-Makefile.mk.patch
- 0002-eqn-neqn.d-Makefile.mk.patch
- 0003-eqn-yyval.sed.patch
- 0004-ptx-ptx.c.patch
- 0005-refer-Makefile.mk.patch
- 0006-refer-glue4.c.patch
- 0007-refer-hunt2.c.patch
- 0008-refer-inv5.c.patch
- 0009-refer-refer1.c.patch
- 0010-refer-refer5.c.patch
- 0011-refer-sortbib.c.patch
- 0012-troff-n5.c.patch
- 0013-troff-nroff.d-terms.d-Makefile.mk.patch
- 0014-troff-troff.d-devaps-Makefile.mk.patch
- 0015-troff-troff.d-dpost.d-path.h.patch
- 0016-troff-troff.d-font-Makefile.mk.patch

## 依赖版本

- flex: 已预装
- clang: 15.0.4
- 无外部库依赖

## 验证结果

```bash
# 二进制已安装并签名
ls ~/usr/local/ucb/troff ~/usr/local/ucb/nroff ~/usr/local/ucb/tbl ~/usr/local/ucb/pic

# 测试运行 (需签名后)
~/usr/local/ucb/troff  # 输出 PostScript 初始化信息
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| heirloom-doctools-191015-ohos-aarch64.tar.gz | 50MB | 预编译包 |

## 注意事项

1. 此项目不支持 DESTDIR，需直接安装到 PREFIX
2. 安装时会尝试执行 runinv 脚本（在 HMDFS 上可能失败）
3. 二进制文件需要 ELF 签名才能在鸿蒙系统上运行
4. troff/nroff 不支持 --version 选项，需通过其他方式验证

---

**编译结束**: 2026-07-15 23:01
**最终状态**: built
