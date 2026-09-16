# mcfp — OpenHarmony 编译档案

## 软件简介
mcfp（即 libmcfp，作者 Maarten L. Hekkelman，前 GitHub 名 `mhekkel/libconfig`）是一个 **header-only
C++20** 配置收集库：从**命令行参数**与 **INI 风格配置文件**收集配置，经单例 `mcfp::config::instance()`
全程序可见（替代 boost::program_options 一类工作）。许可证 BSD-2-Clause。本次适配上游发布版 **1.4.2**
（tag `v1.4.2`）。产出仅为头文件 + CMake 配置（`find_package(mcfp)` → 目标 `mcfp::mcfp`），无库/无二进制。

## OHOS 适配要点
- CMake (>=3.23) INTERFACE header-only 工程：`add_library(mcfp INTERFACE)` + `mcfp::mcfp` ALIAS，
  C++20。`package_type: header-library`，`validate()` os 白名单 Linux/OHOS（R32）。
- OHOS 下 CMakeToolchain 置 `CMAKE_SYSTEM_NAME=Linux`（Linux-like 目标，同 fast_float 技法）。
- 上游 `test/unit-test.cpp` 需 Catch2 v3.4.0（CPM 从 GitHub clone，OHOS CI 禁网）且仅 top-level 加入 →
  conan 构建 `BUILD_TESTING=OFF`，如实 NOT_RUN；功能验证放 test_package 消费者
  （真实 parse CLI：`-n 7 --text hello` → num=7/text=hello）。
- **关键定位**：mcfp 是 cif-tools 2.0.0 的硬依赖（configure 时 CPM 从 forge.hekkelman.net 拉取，
  除非已预提供 mcfp target；每个 cif-tools 程序链接 `mcfp::mcfp`）。离线 OHOS 构建必须先建本依赖库，
  为 cif-tools 提供 `find_package(mcfp)` + 目标 `mcfp::mcfp`（本仓库依赖优先 §1.9 规则）。

## 依赖关系
- 编译/运行依赖：无（纯标准库 header-only）
- 被依赖：cif-tools（先建本库，再 `requires mcfp/1.4.2` 真实验证）

## 参考资料
- [mcfp 官方主页](https://forge.hekkelman.net/maarten/mcfp)（Forgejo）
- [GitHub 镜像 libmcfp v1.4.2](https://github.com/mhekkel/libmcfp/archive/refs/tags/v1.4.2.tar.gz)
