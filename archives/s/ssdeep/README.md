# ssdeep

ssdeep 是 Jesse Kornblum 开发的模糊哈希（context-triggered piecewise hashing, CTPH）工具，
用于计算和比较文件的相似度签名。本项目为 ssdeep 2.8 在 HarmonyOS PC 上的适配。

## 功能概述

- 计算文件/缓冲区的 fuzzy hash 签名（`ssdeep <file>` CLI）
- 相似度比较（`fuzzy_compare`，0-100 分制）
- 提供 libfuzzy 库（公开头 `fuzzy.h`）与 `ssdeep` 命令行两个产物
- 广泛用于恶意软件/取证领域的相似文件检测

## OHOS 适配

- 构建系统：GNU autotools（2012 老工程）
- 适配点：tarball 内 config.guess/config.sub 为 2005 版无法识别 HarmonyOS，
  以 2024 版替换（vendored 于 `patches/autotools/`，`source()` 复制进源码树）
- tarball 未打包 m4/ 宏目录：vendored libtool m4 宏补齐并阻止 maintainer
  规则重生成（参照 babeltrace 1.5.11 配方）
- 上游无测试集（R51 枚举台账见 2.8/notes.md）；专项测试 9/9、消费者验证通过

## 依赖关系

- 无外部 Conan 依赖（纯系统头文件）
- 构建期工具：autoconf/automake/libtool/pkg-config/make

## 参考资料

- 官网: https://github.com/ssdeep-project/ssdeep
- 上游文档: https://ssdeep-project.github.io/ssdeep/