# colortest 20110624 适配笔记

## 编译环境
- 构建系统: custom（纯 shell/perl 脚本工具，无编译步骤）
- 编译日期: 2026-09-08
- 编译器: 不适用（无源码编译，仅脚本打包）
- 状态: built

## 编译步骤

colortest 是终端颜色测试脚本工具集（5 个脚本：colortest/256colors2.pl 为 perl，
8colors.sh/16colors.sh 为 sh，colortable16.sh 为 bash），上游无 configure/make，
conan 配方在 package() 中直接安装脚本到 bin/ 并修正 shebang。

1. 上游源码获取：colortest.org 官网已改版（Squarespace）不再提供 tarball，
   改用 Debian 官方 pool 保留的上游 orig 包（权威镜像源，R39 合规）：
   https://deb.debian.org/debian/pool/main/c/colortest/colortest_20110624.orig.tar.gz
2. 语言预检：源码主体为 perl/bash 脚本（无 C/C++ 主体），按实际语言 perl 判定匹配
   （任务总纲要求适配，参照仓库已合入纯脚本工具先例 abcde/aurpublish/abcselect）
3. conan 配方：package_type=application，package() 安装 5 个脚本 + README 文档

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 默认语言预检判 env_unsupported | 任务语言默认 cpp，colortest 源码为 perl/bash 纯脚本 | 按实际语言 perl 重新预检匹配；参照仓库已合入纯脚本先例（abcde/aurpublish/abcselect） |
| 2 | colortest.org 官网 tarball 失效 | 官网改版为 Squarespace 站点，不再提供源码下载 | 改用 Debian 官方 pool 的 orig 包（权威镜像源） |
| 3 | OHOS 无 /usr/bin/perl 与 /bin/bash | 解释器不在标准路径 | 修正 shebang 为 #!/usr/bin/env perl / #!/usr/bin/env bash（E037 范式，同 abcselect 先例）；sh 脚本保留 #!/bin/sh（OHOS 存在） |
| 4 | 构建目录初始在系统临时目录 | SKILL init-build 默认 TMPDIR=/data/storage/el2/base/temp | 设置 TMPDIR=$HOME/tmp 重建，避免系统清理丢失产物 |

## 源码修改

无补丁。脚本 shebang 修正发生在 conan 配方 package() 阶段（打包时动态修改，
不修改上游源码文件）。

## 依赖版本

- 无编译依赖。运行时依赖：perl（colortest/256colors2.pl）、bash（colortable16.sh）、
  sh（8colors.sh/16colors.sh）

## 验证结果

```bash
# 本机实测（$HOME/tmp/builds/colortest-20110624.work）
perl colortest        # exit=0，输出 256Color Test Chart
sh 8colors.sh         # exit=0，输出 8 色表
bash colortable16.sh  # exit=0，输出 16 色表
# test_package 冒烟测试（conan-verify 执行）：17 项断言
#   5 脚本存在且可执行 + 3 shebang 检查 + 5 语法检查（perl -c/sh -n/bash -n）+ 4 实际输出校验
```

## 上游测试说明

上游源码仅 5 个脚本 + README，无 Makefile/ctest/pytest 等任何测试框架，
上游测试用例数为 0。test_package 自研 17 项断言覆盖脚本存在性、可执行位、
shebang 正确性、语法检查与实际运行输出。

## 交付物

| 文件 | 说明 |
|------|------|
| archives/c/colortest/20110624/conanfile.py | 纯脚本打包配方 |
| archives/c/colortest/20110624/conandata.yml | 源码 URL + sha256 |
| archives/c/colortest/20110624/test_package/ | 17 断言冒烟测试 |
| archives/c/colortest/commands.json | 命令行工具声明（R38） |

## 注意事项

- colortest 运行时依赖 perl 与 bash 解释器，两者在 OHOS 上经 PATH 提供
  （/data/service/hnp/bin/perl、/data/service/hnp/bin/bash）
- license 为混合许可：README/8colors.sh/16colors.sh/256colors2.pl 为 MIT-X11，
  colortable16.sh 为 GPL-3+，colortest 为 Public-Domain（Debian copyright 声明）
---

**编译结束**: 2026-09-09 01:37
**最终状态**: built
