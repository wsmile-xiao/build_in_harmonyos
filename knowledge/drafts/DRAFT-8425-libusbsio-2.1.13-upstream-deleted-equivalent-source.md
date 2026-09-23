# DRAFT-8425-libusbsio-2.1.13-upstream-deleted-equivalent-source — 上游仓库被删除：产物级等价源判定四步法（PyPI whl 内嵌 so MD5 对照）

- 触发事件：libusbsio 2.1.13 适配（PR #10258），任务指定上游 github.com/Intronics/libusbsio 已删除（404）
- 路径：Path B（知识库扩展）
- 编号：DRAFT-8425

## 现象

任务指定的上游 URL `https://github.com/Intronics/libusbsio`（tag v2.1.13）返回
HTTP 404；`api.github.com/users/Intronics` 账号仍存在但公开仓库数为 0（仓库被
删除或私有化）。官方下载渠道（NXP 官网）旧版本已下架，仅剩最新版且需账号登录。
所有常规镜像渠道（SWH/Wayback/发行版缓存/Gitee/GitCode）均无该精确版本源码。

## 根因

上游仓库删除/私有化是外部永久事件，任何网络环境都无法恢复精确 tag。但被适配
软件的**版本号语义**可能存在两条线：**包发布版本**与**内嵌二进制的库修订版本**
（如 NXP libusbsio：PyPI 包版本 2.1.x 是 Python wrapper 版本，内嵌 C 库独立用
v2.1a–v2.1e 字母修订）。若目标平台的产物在多个包版本间逐字节相同（库未变更），
则"精确 tag 消失"不等于"目标平台产物源码消失"——等价源可用。

## 四步产物级等价源判定法（可复用）

1. **版本语义拆解**：`strings` 提取官方各版本发行物（PyPI whl/sdist 内嵌的
   .so/.dll）的库版本串，建立"包版本 → 库修订"演进表。
   例：libusbsio 2.1.10/11/12/13 的 linux so 均为 "NXP LIBUSBSIO v2.1c"，
   只有 Windows dll 走到 v2.1e。
2. **MD5 字节级对照**：目标平台（linux_x86_64/linux_aarch64）产物在哪些包版本
   间 MD5 相同。相同 = 该平台 C 库源码从未变更。
   例：2.1.13 whl 与 2.1.11 的 linux so 逐字节相同。
3. **快照源核验**：找同库版本串的公开源码快照（社区镜像仓库/发行版打包仓），
   核验源码内 `g_LibVersion` 宏与目标版本串一致 + API 导出面 `nm -D` 全对应
   （LPCUSBSIO_* 11 + HIDAPI_* 8 函数）。
4. **证据链落档**：conandata URL 用快照仓库 pinned commit + sha256；notes.md
   与 PR 正文完整记录上述证据（这是审核时"为什么不用官方源"的答辩材料）；
   平台差异（如 Windows v2.1e）如实声明不影响目标平台。

## 排查过的无效渠道（避免重复劳动）

- GitHub fork 搜索（匿名 API 对 fork:false 的手动快照不敏感，搜 "repo fork" 可能为 0）
- Software Heritage origin search / Wayback Machine（可能无归档或网络不可达）
- NXP 官网直链（downloads/en/libraries/*.zip 全版本 404；新下载走 Azure B2C 登录墙）
- 发行版缓存（Debian/Ubuntu 无此包；Arch/nixpkgs 有但指向同一失效官方直链）

## 失败兜底

- 官方渠道需登录 → 申请账号下载历史版本
- 全渠道无等价源 → result.json 报 upstream_issue 止损，附完整渠道清单

## 验证

- CI 构建：#48457（PR #10258，libusbsio/2.1.13 conan create 全绿 + test_package 6/6）
- 交叉核验：快照源码编译产物与官方 whl 内嵌 so 的 API 面/版本串一致
