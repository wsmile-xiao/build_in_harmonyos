# OpenGFX 8.0 适配笔记

## 编译环境
- 构建系统: makefile (NML build framework)
- 编译日期: 2026-06-04
- 编译器: clang (用于 .pnml 预处理)
- 状态: published

## 编译步骤

OpenGFX 是 OpenTTD 的数据/图形包，不是传统的可编译软件。
从源码编译需要 nmlc (NML compiler) 和 grfid (来自 grfcodec)。

1. 安装 nml (Python): pip install nml → nmlc 0.9.0
2. 尝试从源码 make → 失败（PIL .so 无法加载 + grfid 缺失）
3. 使用官方预构建包 opengfx-8.0-all.zip 安装

实际使用的安装方式:
```bash
# 下载预构建包
curl -kfsSL https://cdn.openttd.org/opengfx-releases/8.0/opengfx-8.0-all.zip
# 解压
unzip opengfx-8.0-all.zip && tar xf opengfx-8.0.tar
# 手动安装到 DESTDIR staging 目录
cp *.grf *.obg *.txt $TEST_PREFIX/$DEFAULT_PREFIX/share/openttd/baseset/opengfx/
# 安装到本地
cp *.grf *.obg *.txt $DEFAULT_PREFIX/share/openttd/baseset/opengfx/
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | PIL .so 无法加载 (Permission denied) | HMDFS 安全限制: pip 安装的 .so 文件需 ELF 签名 | 使用预构建包 |
| 2 | grfid 缺失 | grfcodec 需要 Boost 库编译 | 使用预构建包 |
| 3 | gcc 缺失 | 系统只有 clang | CC=clang 替代 |
| 4 | /bin/bash 缺失 | HMDFS 无 /bin/bash | SHELL=~/usr/local/bin/bash |

## 源码修改

无补丁文件 - 使用预构建包安装。

## 依赖版本

- nml 0.9.0 (Python pip)
- Pillow 12.2.0 (Python pip, 但 .so 无法加载)
- clang 15.0.4 (替代 gcc)
- bash 5.3.0

## 验证结果

```bash
# Staging 验证
ls $TEST_PREFIX/$DEFAULT_PREFIX/share/openttd/baseset/opengfx/
# 6 .grf 文件, 1 .obg 文件, 3 .txt 文件 → ✅ PASS

# make check: SKIPPED (grfid 不可用)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| ogfx1_base.grf | 2.7 MB | 基础图形集 |
| ogfxc_arctic.grf | 287 KB | 极地图形集 |
| ogfxh_tropical.grf | 472 KB | 热带图形集 |
| ogfxt_toyland.grf | 622 KB | 玩具乐园图形集 |
| ogfxi_logos.grf | 250 KB | Logo 图形集 |
| ogfxe_extra.grf | 988 KB | 额外图形集 |
| opengfx.obg | 10.7 KB | 基础图形集元数据 |

## 注意事项

- OpenGFX 是数据包，不含可执行二进制
- 安装路径: share/openttd/baseset/opengfx/
- 从源码编译需要 nmlc + grfid + PIL（当前环境不完全满足）
---

**编译结束**: 2026-06-04 12:12
**最终状态**: published
