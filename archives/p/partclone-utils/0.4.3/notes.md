# partclone-utils 0.4.3 编译笔记

## 基本信息
- 软件: partclone-utils
- 版本: 0.4.3
- 构建系统: autotools
- 状态: built

## 编译过程
- configure --prefix=$DEFAULT_PREFIX
- 3个补丁: INSTALL, config.h.in, src/imagemount.c (平台适配)
- make -j1: 成功
- make install DESTDIR=$TEST_PREFIX: 成功
- 安装了3个二进制: imagemount, partclone_imageinfo, ntfsclone_imageinfo

## 补丁说明
- 0001-INSTALL.patch: 安装文档更新
- 0002-config.h.in.patch: 配置头文件适配
- 0003-src-imagemount.c.patch: imagemount源码适配HarmonyOS

---
**编译结束**: 2026-06-05
**最终状态**: built
---

**编译结束**: 2026-06-05 11:58
**最终状态**: built
