# falcosecurity-libs

Falco Security Libraries 是 Falco 项目的用户态事件采集、解析和过滤库集合。

## 功能概述

- 提供 libscap 和 libsinsp 用户态库。
- 支持 savefile 解析、事件表、过滤表达式和插件相关接口。
- 上游包含面向 Linux driver/BPF 的能力；本版本在 OHOS 仅启用用户态实现。

## OHOS 适配

本版本使用 CMake 在 HarmonyOS PC aarch64 上构建，保留 libscap/libsinsp 用户态测试，关闭依赖 Linux kernel driver、modern BPF 和 live driver 的目标。构建时对 CMake ExternalProject 的固定源码归档和上游 scap fixture 做 checksum-bound Conan 预取与 staging，具体版本记录见 `0.25.4/notes.md`。

## 依赖关系

上游 bundled 依赖包括 zlib、oneTBB、jsoncpp、RE2 和 valijson；OHOS 测试使用 ohpcd 发布的 gtest/1.17.0。

## 参考资料

- 上游仓库：https://github.com/falcosecurity/libs
- 官网：https://falco.org/
