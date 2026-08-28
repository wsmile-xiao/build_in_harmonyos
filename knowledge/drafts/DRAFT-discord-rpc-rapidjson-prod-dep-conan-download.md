# CMake configure 期 file(DOWNLOAD) 下载的生产依赖改由已发布 Conan 依赖提供

> **Path B 知识草稿**（配对文件: `DRAFT-discord-rpc-rapidjson-prod-dep-conan-download.kv`）
> 关联: discord-rpc 3.4.0 · PR #7045 · delivered commit `4c306374d0`
> 作者: junshi_liu · 兰州大学DSLab · 2026-08-28

## 问题（error signature）

```text
no rapidjson, download
file(DOWNLOAD https://github.com/miloyip/rapidjson/archive/v1.1.0.tar.gz ...)
Configure-time download of production dependency
RAPIDJSON_ROOT must be set
```

上游 CMakeLists 在 configure 期用 `file(DOWNLOAD ...)` 直接把**生产依赖**（rapidjson
v1.1.0）下载到 `thirdparty/` 并解压，使构建强依赖 GitHub 网络；离线/受限 CI 无法
配置，下载不固定版本、无可追溯性。

## 根因（root cause）

上游把生产依赖硬编码为 configure 期 GitHub 下载，而非通过包管理器声明。CMake 的
`file(DOWNLOAD)` 在 configure 阶段执行，任何网络不可达/限流环境都会在配置期失败；
且下载的版本/内容不受版本固定约束。

## 解决方案（rec_approach）

1. **声明依赖**：`conanfile.py` 的 `requirements()` 中
   `self.requires("<dep>/<version>")`（依赖必须已发布到制品仓，未发布先按 R36 适配发布）。
2. **注入依赖根**：`generate()` 中
   `tc.cache_variables["<DEP>_ROOT"] = self.dependencies["<dep>"].package_folder`。
3. **替换下载块**：打补丁把上游 `file(DOWNLOAD ...)` 块改为
   ```cmake
   find_path(<DEP>_INCLUDE NAMES <header> PATHS ${<DEP>_ROOT} PATH_SUFFIXES include)
   ```
   并把消费方 include 指向 `${<DEP>_INCLUDE}`；或改用 `INTERFACE IMPORTED` 目标注入
   `INTERFACE_INCLUDE_DIRECTORIES`。

discord-rpc 实例：`self.requires("rapidjson/1.1.0")` +
`tc.cache_variables["RAPIDJSON_ROOT"] = rj.package_folder` +
补丁 0001（下载块→find_path RAPIDJSON_INCLUDE）+ 补丁 0002（include 指向
RAPIDJSON_INCLUDE）。

## 验证（verification）

- `conan create` 通过，configure 阶段不再有任何 GitHub 下载
- 断网/受限环境可复现构建（离线可复现）
- `conan list <dep>/* -r=ohpcd` 确认依赖已发布
- W3 本地 CI 模拟 1/1 100% 通过
- 实例实测：conan-verify G2 PASS；W3 1/1 100%

## 适用边界（applicability boundary）

仅适用于 CMake 工程在 configure 期下载**生产依赖**（非测试框架）且该依赖已发布到
制品仓的场景。测试框架下载（FetchContent/ExternalProject for test）归 E321-draft，
本条目不覆盖。依赖未发布时需先按 R36 适配发布。

## 查重结论（duplicate-check）

- `grep -ril rapidjson knowledge/` = 1（仅为 discord-rpc 配方源码注释，非条目）
- `grep -rl 'file(DOWNLOAD' knowledge/` = 0
- `grep -rl 'RAPIDJSON_ROOT' knowledge/` = 0
- `knowledge/index.tsv` 无相关
- E321-draft（test-only 下载）场景不同

→ **无重复，差异明确。**

## 既有覆盖排除（existing coverage exclusions，非新增 Path B 内容）

- E103/E104/E187：已覆盖 CMake 4.x policy 兼容（`cmake_minimum_required <3.5` →
  升 3.5 / `CMAKE_POLICY_VERSION_MINIMUM`）——本条目**不**把该机制作为新增内容。
- E092 及 E096/E140/E144/E159/E207/E267：已覆盖 CMake/OHOS 平台识别
  （`System is unknown to cmake` / `CMAKE_SYSTEM_NAME`）——本条目**不**把该机制作为
  新增内容。

本条目只新增「configure 期生产依赖 `file(DOWNLOAD)` → 已发布 Conan 依赖注入」这一
机制，不依赖 r02 基线噪音或 r03 共享框架 W5 问题。

## 来源证据（source evidence）

discord-rpc 3.4.0（PR #7045，delivered commit `4c306374d0`）：上游
`CMakeLists.txt` 37-45 行 `no rapidjson, download` → `file(DOWNLOAD miloyip/rapidjson
v1.1.0)` + tar xzf；修复 = `conanfile.py requires("rapidjson/1.1.0")` +
RAPIDJSON_ROOT cache_variable + 补丁 0001/0002。验证：conan-verify G2 PASS；W3
1/1 100%；registry 已发布 rapidjson/1.1.0。

## 关联

- 知识条目正式编号：**由知识编辑审核后分配**（本草稿不预设编号）
- 配对 KV：`knowledge/drafts/DRAFT-discord-rpc-rapidjson-prod-dep-conan-download.kv`
- 关联 Issue：随 PR #7045 提交的 Path B Issue
