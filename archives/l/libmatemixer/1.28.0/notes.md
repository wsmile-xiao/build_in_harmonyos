# libmatemixer 1.28.0 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-02
- 编译器: clang/clang++ (15.0.4)
- 状态: built

## 编译步骤

1. 下载源码: https://pub.mate-desktop.org/releases/1.28/libmatemixer-1.28.0.tar.xz
2. 修复 HMDFS umask 问题: `sed -i 's/umask 077/umask 022/g' configure build-aux/config.guess build-aux/config.sub`
3. 应用 E007 补丁: `perl patch-autotools-ohos.pl build-aux/config.guess build-aux/config.sub`
4. 手动添加 linux-ohos kernel-OS 组合到 config.sub case 语句
5. 手动添加 ohos* 到 OS 列表
6. 设置 PKG_CONFIG_PATH 并执行 configure: `./configure --prefix=$DEFAULT_PREFIX`
7. 执行 make 编译
8. 执行 make install DESTDIR=$TEST_PREFIX

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | GNU config.guess 不包含 HarmonyOS 检测 | E007: 使用 patch-autotools-ohos.pl 补丁 |
| 2 | HMDFS 无法创建临时文件 | umask 077 导致 hmmac 强制访问控制拒绝 | sed -i 's/umask 077/umask 022/g' |
| 3 | "Kernel 'linux' not known to work with OS 'ohos'" | config.sub 缺少 linux-ohos 组合 | 手动添加 linux-ohos*) ;; 到 case 语句 |
| 4 | "OS 'ohos' not recognized" | config.sub OS 列表缺少 ohos* | 手动添加 ohos* 到 OS 列表 |
| 5 | g_libintl_gettext undefined | libintl.so 缺少 g_libintl_* 符号 | 更新 libintl.so 链接指向 proxy-libintl |
| 6 | 缺少 glib-2.0 依赖 | PKG_CONFIG_PATH 未设置 | export PKG_CONFIG_PATH 包含正确路径 |

## 源码修改

- build-aux/config.guess: E007 补丁添加 HarmonyOS 检测 + umask 修复
- build-aux/config.sub: E007 补丁添加 ohos-linux triplet + 手动添加 linux-ohos*) ;; + ohos* 到 OS 列表 + umask 修复
- configure: umask 077 -> umask 022 修复

## 依赖版本

- glib-2.0: 2.84.0
- gobject-2.0: 2.84.0
- gmodule-2.0: 2.84.0

## 验证结果

```bash
# 产物检查
ls $TEST_PREFIX/$DEFAULT_PREFIX/lib/libmatemixer.so.0.0.0
# 输出: libmatemixer.so.0.0.0 (358KB)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libmatemixer.so.0.0.0 | 358KB | 核心库 |
| libmatemixer.a | 705KB | 静态库 |
| libmatemixer-null.so | - | Null 后端模块 |
| libmatemixer.pc | - | pkg-config 文件 |

## 注意事项

- PulseAudio 和 ALSA 模块因缺少依赖未构建，仅构建 Null 模块
- 需要正确设置 PKG_CONFIG_PATH 才能找到 glib
- libintl.so 需使用 proxy-libintl 版本（含 g_libintl_* 符号）
---

**编译结束**: 2026-06-02 10:24
**最终状态**: built
