# FASTBuild

> High performance build system with caching and network distribution (fbuild/fbuildworker).

## 简介

FASTBuild 是面向游戏工作室等大型 C/C++ 项目的高性能构建系统，支持高度可扩展的编译、
对象缓存与网络分发。本配方将上游 v1.02 源码（任务版本 1.2）在 HarmonyOS aarch64 上
构建为 `fbuild` 与 `fbuildworker` 两个命令行工具。

## OHOS 适配要点

- 工具包：仅发布 `fbuild` / `fbuildworker` 二进制（application 包，R38）。
- 上游用 FASTBuild 自举构建（.bff 文件），需要预置 fbuild 二进制，而上游不提供
  Linux ARM 自举包（Homebrew 也因此仅限 x86_64）；本配方直接用 OHOS clang 复刻
  上游 Linux/Clang 构建（相同源文件集合、`-D__LINUX__`、C++11、unity 分块编译）。
- 内嵌 LZ4（External/LZ4/lz4-1.9.2）随源码树编译，无外部 conan 依赖。
- 上游测试 CoreTest（18 组）与 FBuildTest（34 组非 Windows）在 `build()` 中从源码根
  真实运行，汇总解析后输出 `HMBS_UPSTREAM_TEST_RESULT`。

## 功能验证

```bash
fbuild -version        # 打印 v1.02
fbuild -config hello.bff  # 编译最小 C 工程（见 test_package）
```

## 参考

- [官网](https://fastbuild.org)
- [源码仓库](https://github.com/fastbuild/fastbuild)
