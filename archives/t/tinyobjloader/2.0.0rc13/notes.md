# tinyobjloader 2.0.0rc13 适配笔记

## 编译环境
- 构建系统: custom (header-only)
- 编译日期: 2026-09-01
- 编译器: clang 15.0.4
- 目标平台: OHOS armv8
- 状态: built

## 编译步骤

使用 Conan 2.29.1 和 `ci/conan/profiles/ohos-aarch64` 执行 `conan create`。
库为 header-only 单文件（`tiny_obj_loader.h`），配方将头文件安装到 `include/`，
不产生库文件；消费者在单一翻译单元定义 `TINYOBJLOADER_IMPLEMENTATION` 内嵌实现。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|---|---|---|
| 1 | GitHub 直连下载超时 | 官方 tarball 域名直连不可达 | 经 gh-proxy.com 镜像下载；conandata.yml 保留官方 URL + SHA-256，CI 镜像 fallback 机制覆盖 |
| 2 | header-only 链接 | 单文件库需在单一 TU 定义实现宏 | test_package 源码首行 `#define TINYOBJLOADER_IMPLEMENTATION` |

## 源码修改

无。使用官方 tag `v2.0.0rc13`（commit `2945a967c5303b2c8c14174117c45f3302591150`），
tarball SHA-256 `0feb92b838f8ce4aa6eb0ccc32dff30cb64a891e0ec3bde837fca49c78d44334`。

## 依赖版本

无外部依赖（仅 C++ STL）。

## 验证结果

- Conan `conan create`（ohos-aarch64 profile）通过。
- 消费者测试 `test_tinyobjloader`：`tinyobj::LoadObj` 解析内置 `cube.obj`，
  校验 shape/顶点/索引计数，编译并运行通过。
- HarmonyOS 专项测试：见 `archives/t/tinyobjloader/2.0.0rc13/` 下 ohos 专项用例记录。
- W4 独立审计: PASS（P0/P1/P2/P3 均为 0）

## 注意事项

header-only 库通过 `TINYOBJLOADER_IMPLEMENTATION` 宏在单一翻译单元启用实现；
仅包含头文件不会产生链接库，`cpp_info.libs` 必须为空。
---

**最终状态**: built
---

**编译结束**: 2026-09-01 10:31
**最终状态**: built
