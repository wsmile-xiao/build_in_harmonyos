# 滚动 URL 且含非自由子集的数据包：钉死 Debian dfsg 重打包 orig 归档为 conan 源

- **草稿 ID**: DRAFT-ldraw-parts-free-2602-debian-dfsg-repack-pinned-source
- **来源**: ldraw-parts-free 2602 HarmonyOS PC 适配（LDraw 零件库 DFSG 自由子集）
- **分类**: conan / recipe / sourcing / licensing / debian
- **状态**: 本地草稿（路径 B 知识库扩展申请中，位于 knowledge/drafts/）

## 问题 / 错误签名

- **滚动 URL**：上游发布 URL 为 `library.ldraw.org/updates?latest`（每次更新覆写），任何时刻下载的 complete.zip 内容都不同，无法取固定版本 sha256。
- **非自由子集**：库内约 3200 个零件/子零件及 4 个样例模型仍为 CC-BY-2.0-only 或双许可（DFSG 非自由），整体导入即合规问题；而 conan sources 需要「固定版本 + 可校验 sha256 + 内容合法」三者同时成立。
- **可观测特征**：滚动 URL 快照 sha256 写死后，下次 conan create 时 get() 校验失败；或防漂移计数断言随上游更新随机挂。

## 根因

1. 上游（LDraw.org）只提供滚动发布，无按版本归档；
2. 发行内容混合 CC-BY-4.0 与 CC-BY-2.0/CCAL 许可，不能整体进入自由发行；
3. Debian 维护者已解决该问题：`repack.sh` 提取 mklist 工具源码、`gendfsgsrc.py` 按「首个 `0 !LICENSE` 生效行精确匹配 CC BY 4.0」+「依赖图祖先剔除」过滤出自由子集，产出独立源码包 **ldraw-parts-free 2602+dfsg-1**，其 orig.tar.xz 在 Debian main 池按版本号永久留存、sha256 记于同名 .dsc。

## 最小修复方案

conandata.yml 直接钉死 dfsg 归档 + 双镜像：

```yaml
sources:
  url:
    - "https://mirrors.ustc.edu.cn/debian/pool/main/l/ldraw-parts-free/ldraw-parts-free_2602+dfsg.orig.tar.xz"
    - "https://mirrors.aliyun.com/debian/pool/main/l/ldraw-parts-free/ldraw-parts-free_2602+dfsg.orig.tar.xz"
  sha256: "2011f947f924073aec4d05035ffc994ead627e6cafe22c73e43c907abd14e761"  # 与 2602+dfsg-1.dsc 记录一致
```

要点：

- sha256 必须取自同名 `.dsc` 的 Checksums-Sha256 字段（Debian 官方记录），绝不取自滚动 URL 当前快照；
- url 主 + 备镜像成对（USTC / aliyun 均实测可达）；
- **顶层目录下钻**：dpkg-source 生成的条目带 `./` 前缀（`./ldraw-parts-free-2602/...`），conan `get(strip_root=True)` 的 commonpath 顶层判定遇 `./` 不剥离（真机 2.29.1 实证：b/ 下仍为整目录、build() 报 missing files）——`get()` 原样解压，配方 `_src_root()` 按固定顶层目录名显式下钻，行为确定；
- 配方 build() 按 dfsg 重打包清单做防漂移校验（目录精确计数 + 被剔内容负向断言：textures 整类、car/pyramid 样例、被剔著名零件）；
- **package() 整树 `copy("*")` + excludes pattern 列表**（excludes 必须是列表，逗号串整体当作单个 fnmatch pattern 不生效）；禁止目录级 `copy(self, "<目录>", ...)`——conan 2 真机实证是空操作（2.29.1 包目录只剩根文件、消费者探针目录计数全红）。

回退方案（Debian 无对应 dfsg 包时）：下载官方滚动归档 → 按上游许可清单自行过滤非自由子集 → 生成自有固定版本归档上传至可钉死地址；过滤口径必须在 MR 正文/notes 写明，过滤逻辑可复现（脚本留存）。

## 验证结果

| 环境 | 结果 |
|------|------|
| 本机（Windows）· curl 双镜像 | 200 OK，sha256 与 .dsc 记录一致（55053344 字节） |
| 本机（Windows）· Python 全树扫描 | 32387 文件清单 + 许可/引用/剔除三不变量全部实证 |
| HarmonyOS PC aarch64 真机 · 第一轮 | G2 FAIL：`get(strip_root=True)` 不剥离 `./` 前缀顶层目录 → build() 报 missing files（本条 forbid_2 实证来源） |
| HarmonyOS PC aarch64 真机 · 第二轮 | G2 FAIL：目录级 `copy()` 空操作 → 包目录只剩根文件（本条 forbid_3 实证来源） |
| HarmonyOS PC aarch64 真机 · 第三轮（修复后） | 55.1MB USTC 下载成功；八门禁全过，消费者测试执行器 7 用例 `TEST SUMMARY: 7 passed, 0 failed`，EXIT=0 |
| HarmonyOS PC aarch64 真机 · 第四轮（执行器化 + 渲染管线端到端复验） | 八门禁全绿（G0-G4 PASS，L2/L4/L5 跳过），消费者端到端用例实测装配图 10 文件 / 25 引用 / 三角 16 + 四边形 46 |

## 禁止策略

- 禁止直接用滚动 URL 作 sources.url（sha256 留空或写死快照值）——前者违反 L0b、丧失可复现性，后者必然漂移，防漂移断言随机挂。
- 禁止依赖 `get(strip_root=True)` 剥离 dpkg-source 顶层目录后直接按 `self.source_folder` 寻文件——`./` 前缀使 strip 不生效（真机 2.29.1 实证），build() 必报 inventory drift；应原样解压 + 显式下钻。
- 禁止用目录级 `copy(self, "<目录>", ...)` 逐目录复制——conan 2 真机实证是空操作，包产物缺整个子树；必须 `copy("*")` + excludes 列表。
- 禁止整体导入含非自由子集的官方归档并靠改 license 字段回避——审查者抽查任一 .dat 的许可行即可发现，合规不通过。
- 禁止把 dfsg 重打包的「过滤口径」当作实现细节略写——子集边界（哪些被剔、为什么）是审查与复现的核心，必须在 notes/MR 正文写明。

## 相关

- 相似条目：E112（固定版本源选择视角）。
- 关联经验：姊妹包 ldraw-parts 2602（完整库）走 Ubuntu 2602+ds orig（仅剔 mklist 工具 4 文件）；本条目为「滚动 URL + 非自由子集 → dfsg 自由子集」的更复杂变体。
