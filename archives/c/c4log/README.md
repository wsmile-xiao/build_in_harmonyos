# c4log for HarmonyOS

## 概述

c4log 是 biojppm 出品的轻量 C++ 类型安全日志库，基于 c4core 的格式与类型系统，提供线程局部 DumpBuf 与可替换 logpump 接口。适用于需要低开销、类型安全日志的 C++ 项目。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | c4log |
| 版本 | 1.0.0 (上游 master 23e9bdba) |
| 许可证 | MIT |
| 上游仓库 | https://github.com/biojppm/c4log |
| 依赖 | c4core (已捆绑 vendor，無需外部) |
| 构建系统 | CMake |

## 鸿蒙适配要点

- 上游依赖 `biojppm/cmake` 的 c4Project 宏，需递归子模块；适配中用最小 CMake 重写，避免网络拉取。
- c4core 源码 (9 个 cpp) 随 c4log 一起编译为静态库 `libc4core.a`，c4log 链接 c4core。
- 默认静态库 (`shared=False`)，C++17。

## 验证

```bash
conan create . --user=ohpcd --channel=stable -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

test_package 验证 `set_logpump/get_logpump` 与 `DumpBuf`。

## 参考
- https://github.com/biojppm/c4log
- https://github.com/biojppm/c4core
