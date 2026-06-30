# rgb 1.1.1 适配笔记

## 编译环境
- 构建系统: autotools
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载源码 rgb-1.1.1.tar.gz 从 xorg.freedesktop.org
2. 修补 config.guess/config.sub 以支持 HarmonyOS (E007)
3. 修补 configure 中 umask 077 → umask 022 (E011)
4. 设置 PKG_CONFIG_PATH 包含 ~/usr/local/share/pkgconfig 和 ~/usr/local/lib/pkgconfig
5. ./configure --prefix=$DEFAULT_PREFIX
6. make -j2
7. make install DESTDIR=$TEST_PREFIX
8. make check (无测试套件，正常通过)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 HarmonyOS | E007: GNU config.guess 不含 HarmonyOS 检测分支 | 用 patch-autotools-ohos.pl 修补 config.guess 和 config.sub |
| 2 | configure 失败: Permission denied 创建临时目录 | E011: HMDFS umask 077 导致临时目录不可写 | sed -i 's/umask 077/umask 022/g' configure |
| 3 | configure 失败: No package 'xproto' found | PKG_CONFIG_PATH 未包含 ~/usr/local/share/pkgconfig | 设置 PKG_CONFIG_PATH |

## 源码修改

| 文件 | 修改原因 | 修改方式 |
|------|---------|----------|
| config.guess | E007: HarmonyOS 平台识别 | patch-autotools-ohos.pl |
| config.sub | E007: ohos-linux 三元组 | patch-autotools-ohos.pl |
| configure | E011: HMDFS umask 权限 | sed 替换 umask 077 → umask 022 |

## 依赖版本

- xproto 7.0.33 (已预装在 ~/usr/local/share/pkgconfig/)
- util-macros 1.20.2 (已预装在 ~/usr/local/share/pkgconfig/)

## 验证结果

```bash
$ showrgb --version
rgb 1.1.1

$ showrgb red
255     0       0       red
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| rgb-1.1.1-ohos-aarch64.tar.gz | 99KB | 预编译包（stripped） |
| rgb-1.1.1-ohos-aarch64-debug.tar.gz | 27KB | 预编译包（含 debug symbols） |

## 注意事项

- 必须设置 PKG_CONFIG_PATH 包含 ~/usr/local/share/pkgconfig 才能找到 X.Org proto 包
- rgb 软件本身很小，只有一个 showrgb 可执行文件和 rgb.txt 数据文件
---

**编译结束**: 2026-06-09 20:20
**最终状态**: built
