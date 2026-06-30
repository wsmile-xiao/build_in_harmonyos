# Inform 6

## 简介

Inform 6 是交互式小说（Interactive Fiction）编译器，将Inform 6源码语言编译为Z-machine/Z-code故事文件（.z5/.z8格式），供Frotz等Z-machine解释器运行。

## OHOS 适配

- inform6使用纯Makefile构建，没有configure脚本
- 需手动修改Makefile支持DESTDIR模式（R20铁律）：将DESTDIR变量融入BINDIR/SHAREDIR/MANDIR路径
- TEMPDIR原硬编码为/tmp（鸿蒙只读），改为 `TEMPDIR ?= /tmp` 以尊重$TMPDIR环境变量（R10铁律）
- uname -s返回"HarmonyOS"而非"Linux"，但Makefile的else分支已正确处理，-DUNIX标志正确应用
- 无外部编译依赖，完全独立编译

## 排除与替代

不适用。inform6是独立编译器。

## 依赖

- 无编译依赖
- 无运行依赖

## 功能验证

```bash
inform --version
# Inform 6.44 for Unix (11th September 2025)
```

## 参考

- 源码: https://ifarchive.org/if-archive/infocom/compilers/inform6/source/old/inform-6.44-r3.tar.gz
- 文档: 源码包内含README.md和docs/目录
- Inform标准库: 源码包内含std/目录