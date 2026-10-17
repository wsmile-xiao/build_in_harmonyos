# TinySVM

TinySVM 是一个小型 C++ 支持向量机（SVM）库和命令行工具集，用于分类与回归。

## 功能概述

- 提供 `libtinysvm` C++ API，可加载模型并对稀疏特征向量分类。
- `svm_learn` 训练分类、回归或 one-class SVM 模型。
- `svm_classify` 对带标签的数据集分类并报告准确率、精确率和召回率。
- `svm_model` 查看模型的支持向量数、间隔、损失等信息。

## OHOS 适配

- 为上游 2002 年版 `config.guess` / `config.sub` 增加
  `aarch64-unknown-linux-ohos` 原生三元组识别；不向 configure 注入
  `--build`、`--host` 或 `--target`。
- 修正旧式 `getopt()` 非原型声明与 HarmonyOS Clang 系统头中 POSIX 原型的冲突。
- 上游仅生成静态 `libtinysvm.a`，与其原始 libtool 构建结果一致。

## 依赖关系

无第三方依赖。运行时仅依赖 C/C++ 标准库和系统数学库 `libm`。

## 参考资料

- [TinySVM 官方主页](http://www.chasen.org/~taku/software/TinySVM/)
- [NetBSD pkgsrc 归档](https://cdn.netbsd.org/pub/pkgsrc/distfiles/TinySVM-0.09.tar.gz)

