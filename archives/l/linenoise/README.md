# linenoise - HarmonyOS 编译记录

## 概述

linenoise 是一个极简、零配置、BSD 许可的 readline 替代品（作者 antirez），提供行编辑、历史记录、补全提示等功能，广泛用于嵌入式与命令行场景。

**编译状态**: ✅ 成功（conan-verify 全部门禁通过，可发布）

## 编译环境

| 项目 | 值 |
|------|-----|
| 系统 | HarmonyOS PC (OHOS) aarch64 |
| 编译器 | clang 15.0.4 |
| 三元组 | aarch64-linux-ohos |
| 构建系统 | Makefile（适配为 CMake 覆盖模式） |

## 版本

| 版本 | 状态 | 说明 |
|------|------|------|
| 2.0 | built | 首次适配（上游 tag 2.0，conan-verify 通过） |

## 说明

- 上游发行站 waterlan.home.xs4all.nl 已失效，源码取自官方 GitHub 仓库 antirez/linenoise tag 2.0
- 上游 Makefile 无 configure/install 目标，配方内嵌 CMakeLists.txt 构建静态库
- 上游测试 linenoise-test 为 VT100 交互测试（需真实 TTY），test_package 以消费者 API 冒烟测试替代
