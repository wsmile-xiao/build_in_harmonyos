# DRAFT — OHOS：hnp `-fuse-ld` 产物被加载器拒绝（dlopen Permission denied）+ registry boost 变体缺 libboost_filesystem

- **状态**: 草稿（UNMATCHED，待评审提升为 E 条目）
- **关联库**: collada-dom 2.5.0
- **来源**: r01-r03（dlopen 拒绝 + boost::filesystem 未定义符号）
- **日期**: 2026-08-28

## 错误特征

```
Error loading shared library <lib>.so: Permission denied          # musl 加载器（hnp-ld 产物）
Error relocating <lib>.so: _ZN5boost10filesystem6detail...: symbol not found   # 默认链接器产物，boost 符号缺失
libboost_filesystem not found / undefined symbol boost::filesystem
```

**关键词**: fuse-ld, /data/service/hnp/bin/ld, hnp, dlopen, Permission denied, EACCES, musl loader, libboost_filesystem, boost/1.90.0, boost/1.90.0.1, CMakeDeps, Boost::filesystem, undefined symbol, shared variant

## 根因分析（两段式失败链）

1. **dlopen Permission denied**：配方注入 `-fuse-ld=/data/service/hnp/bin/ld`（GNU ld 2.45，E266 为规避 ohos-sdk lld 缺 libxml2 的修复方案）后，该链接器产出的 `.so` 被 OHOS musl 加载器以 EACCES 拒绝。
   - 对照实验（r02）：同源码、同用户路径，仅链接器不同——`-fuse-ld` 产物 dlopen 失败，默认链接器产物 dlopen 正常；`-z separate-code` / strip / 版本脚本 / 符号规模 / 段 W^X / 文件大小均无法修复该链接器产物。
   - 区别于 E212 的 hmmac 路径安全标签：E212 无法解释"同路径下默认链接器产物可加载而 hnp-ld 产物被拒"的 A/B 对照。
2. **boost::filesystem 未定义符号**：OHOS registry 的 `boost/1.90.0` 为头文件版包——`operations.hpp` 中 detail 文件系统函数（remove_all / create_directories / status / temp_directory_path 等）仅 `BOOST_FILESYSTEM_DECL` 外部声明、无内联实现，包内亦无 `libboost_filesystem`（仅 `libboost_unit_test_framework.a`）；共享变体 `boost/1.90.0.1` 含 `libboost_filesystem.so`。默认链接器产物可映射加载，但 relocation 阶段报 `boost::filesystem::detail::*` symbol not found。

## 解决方案

```python
# conanfile.py generate() —— 删除 -fuse-ld 注入
# （移除 CMAKE_(EXE|SHARED|MODULE)_LINKER_FLAGS = "-fuse-ld=/data/service/hnp/bin/ld"）

# conanfile.py requirements()
self.requires("boost/1.90.0.1")          # 共享变体（含 libboost_filesystem.so）

# top-level CMakeLists.txt（补丁）
find_package(Boost CONFIG REQUIRED COMPONENTS filesystem)
if(NOT TARGET Boost::filesystem)
  message(FATAL_ERROR "boost 无 filesystem 组件")
endif()
set(Boost_FILESYSTEM_LIBRARY Boost::filesystem)
set(Boost_SYSTEM_LIBRARY "")             # Boost.System 1.69+ header-only
```

## 验证证据

- r02 forensics：同源码仅换链接器 A/B 对照；同路径对照库（40K/120K 符号、15MB）均可加载；同依赖对照库可加载；系统/SDK 库 dlopen 正常 → 归因 hnp-ld。
- r03 全量本地验证：`conan create` PASS（Verdict PASS）、test_package 真实运行 `PASS: collada-dom 2.5.0 parsed COLLADA 1.5 doc (elements=11)`、W3 本地 CI Pass rate 100%、`.ci-result.json` exit 0。
- 证据保留于 `archives/c/collada-dom/2.5.0/reports/` 与 worker 日志（历史 r03，非重跑）。

## 适用边界

- 本环境：OHOS PC（HongMeng Kernel aarch64）、hnp clang 15.0.4（aarch64-linux-ohos）、OHOS musl 加载器。
- hnp-ld 被拒在本环境 A/B 实证；CI worker / 其他 OHOS SDK 版本需复核（默认链接器可能在 CI 触发 E266 的 lld-libxml2 问题，需提供 libxml2 到链接器搜索路径或改用可用链接器）。
- boost 变体格局（1.90.0 头文件版 vs 1.90.0.1 共享版）为 registry 现状，若 boost recipe 更新可能变化，需重查。
- 本地官方 GitHub 直连超时属环境网络约束；交付配置保留官方 URL，下载可经已验证镜像。

## 查重差异（dedup）

| 条目 | 差异 |
|------|------|
| E212（hmmac 标签阻止用户路径 dlopen） | 错误面同为 dlopen Permission denied，但根因为 hmmac 路径标签，无法解释同路径 A/B 对照；本条目为链接器产物被加载器拒绝（可修复） |
| E266（lld 缺 libxml2 → 推荐 -fuse-ld） | 本条目是其推荐方案的下游副作用警示（修复链接后产物在加载阶段被拒），是对 E266 方案的重要扩展/边界 |
| E099/E153（BOOST_INCLUDE_LIBRARIES 构建 boost 组件） | b2/构建配置路径，与 registry 变体选择（headers-only vs shared）不同 |
| 无条目 | 覆盖 "registry boost 变体缺失 libboost_filesystem" 与 "hnp-ld 产物加载器拒绝" |

## 禁止做法

- `chmod 777` / `chcon` / `setfattr security.hmmac`：dlopen 拒绝不是 Unix 权限问题（E212 为 hmmac 标签；本条目为链接器产物属性），无效且降安全性。
- `ln -sf` 覆盖系统库、手工替换 .so、缓存路径/临时 `-L` 硬编码：R5 铁律与交付违禁。
