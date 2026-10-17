# TinySVM 0.09 适配笔记

## 上游概况

TinySVM 0.09 是 Taku Kudo 发布的 C++ 支持向量机库，包含静态库
`libtinysvm.a` 以及 `svm_learn`、`svm_classify`、`svm_model` 三个工具。
官方发布包采用 Autotools/libtool，无第三方依赖。

源码使用 NetBSD pkgsrc 的 HTTPS 官方归档镜像，SHA256 为
`e377f7ede3e022247da31774a4f75f3595ce768bc1afe3de9fc8e962242c7ab8`。

## OHOS AArch64 适配

### 1. 原生构建三元组识别

2002 年版 `config.guess` 无法识别 `aarch64:HarmonyOS`，`config.sub` 也不接受
`aarch64-unknown-linux-ohos`。补丁 0001 和 0002 分别增加系统探测、CPU 与 OS
后缀识别。configure 最终得到
`build == host == aarch64-unknown-linux-ohos`，未使用禁止的
`--build`、`--host` 或 `--target` 参数。

### 2. getopt 原型冲突

上游 `src/getopt.h` 在非 glibc 分支声明 `extern int getopt();`。HarmonyOS
Clang 的系统头提供 POSIX 参数原型，两个声明在 C++ 编译中冲突。补丁 0003
将该分支改为相同的 POSIX 原型，不引入平台宏，也不改变实现。

### 3. 静态库输出

上游旧 libtool 在原始 Linux 基线和 HarmonyOS 上均只生成静态库；配方保留
此行为并发布 `libtinysvm.a`，同时安装上游全部公开头文件和三个 CLI。
HarmonyOS 的 HMDFS 不支持 GNU make jobserver 使用的命名管道，因此目标端
固定 `make -j1`；其他系统仍按可用 CPU 数并行构建。

## 测试

上游 `tests/Makefile.am` 精确列出 5 个测试脚本：

| 测试 | 覆盖内容 |
|---|---|
| `test.sh` | 默认 RBF 分类训练、分类和模型读取 |
| `test2.sh` | 二次多项式核分类 |
| `test3.sh` | 线性回归 |
| `test4.sh` | 二次多项式核回归 |
| `test5.sh` | 900/990/998/500 样本增量模型更新 |

配方在可运行目标上强制执行 `make check`，5/5 必须通过。额外的
`test_package` 包含两个 HarmonyOS 安装后场景：

1. 通过三个已安装 CLI 训练六样本模型、完成 2/2 正确分类并读取模型信息；
2. CMake 消费者通过 `tinysvm::tinysvm` 链接安装后的库，使用公开
   `TinySVM::Model` API 读取模型并验证正负样本分类（9 个断言）。

最终验证命令：

```bash
conan create archives/t/tinysvm/0.09 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

## 依赖

无 Conan 第三方依赖；静态库消费者由配方传递系统数学库 `libm`。

**编译结束**: 2026-09-20
