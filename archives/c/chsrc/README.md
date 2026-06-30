# chsrc — 全平台换源工具

chsrc 是一个用 C 语言编写的全平台换源工具，支持多种编程语言、操作系统和软件的镜像源切换。

## 基本信息
- 版本: 0.2.4
- 语言: C
- 许可证: GPL-3.0-or-later / MIT
- 网站: https://github.com/RubyMetric/chsrc

## HarmonyOS 适配
- 构建系统: Makefile（非 autotools）
- 需要 4 个补丁: PREFIX 支持、configure wrapper、OS 检测、/tmp 路径修复
- 编译选项: CC=clang CFLAGS="-Iinclude -Ilib -fPIC -O2 -D__OHOS__"