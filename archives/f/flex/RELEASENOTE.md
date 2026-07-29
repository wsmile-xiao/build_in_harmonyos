# flex — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf flex-2.6.4-ohos-aarch64.tar.gz -C ~/usr/local

cd flex-2.6.4-ohos-aarch64 && sh install-flex-2.6.4.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.6.4 | built | 6 |

## 当前版本 (2.6.4) 详情

### 包内容
- 二进制: flex (可执行文件)
- 库: libfl.a (静态库)
- 头文件: FlexLexer.h
- 包大小: 647.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-po-Makefile.in.patch — 添加 po/Makefile.in (gettext 支持)
- 0002-src-stage1scan.c.patch — 添加 stage1scan.c (引导扫描器)
- 0003-doc-stamp-vti.patch — 更新 doc/stamp-vti 日期
- 0004-doc-version.texi.patch — 更新 doc/version.texi 日期
- 0005-po-POTFILES.patch — 添加 po/POTFILES (翻译文件清单)
- 0006-configure-fix-hmdfs-tmpdir.patch — HMDFS 临时目录兼容性修复

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
