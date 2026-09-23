# DRAFT-boost1.84-pkg-rename-archive: conan 包名复刻归档五处同步法 + 并行会话 conan 脏缓存修复

> **Contributor**: j669539 | **Status**: Draft（pending editor review）| **Updated**: 2026-09-05
> **Source**: boost1.84 1.84.0 HarmonyOS PC 适配（build_in_harmonyos，archives/b/boost1.84/1.84.0，分支 feat/boost1.84-1.84.0）
> **拟提升编号：由知识库主编确认** —— 本草稿为未提升草稿，尚未分配正式 E 编号

## 场景 A：包名复刻归档（同源码双包名并行）

制品仓已有 `boost/1.84.0`（无点包名），平台任务要求以**新包名 `boost1.84`** 独立归档
`archives/b/boost1.84/1.84.0/`，两个包名并行维护、同源上游（boost_1_84_0.tar.gz，
sha256 一致）。

### 问题

复刻的坑不在编译（配方逻辑照抄底稿 747cbc78ad 即可），而在**元数据一致性**与**两条易漏预检**：

1. conan 对含点号包名仅 WARN 不阻断：
   `WARN: Name containing special chars is discouraged 'boost1.84'`——全链路
   export/create/upload/下游 requires 均正常，无需处理。
2. 五处包名必须同步改（漏改后果）：
   | 位置 | 漏改后果 |
   |---|---|
   | conanfile.py `name`（+类名） | conan create 包名错 |
   | 归档目录 `archives/b/boost1.84/` | CI L0m-4 硬拦截（name↔目录一致门禁） |
   | test_package/MANIFEST.yml `package:` | W4 审计 P2 命名不一致 |
   | docstring（配方+test_package） | W4 审计 P2 |
   | 测试源输出串（std::cout 包名） | W4 审计 P2 |
3. 两条易漏预检：
   - **W0 预检新包名未发布**：`conan download "boost1.84/1.84.0" -r=ohpcd --only-recipe`
     确认 404。若已被他人发布，合并后 upload 撞 409（cnb.cool 不支持同版本多 revision，
     R37 语义），此时应改走版本号后缀策略（X.Y.Z.N）而非新包名。
   - **W3 必须真实重跑**：上游测试结论可复用底稿（同源码同配方逻辑，如 parsers_test
     rc=-11 环境差异），但 `.ci-result.json` 的 log_sha256 绑定**本次**构建日志，
     不可引用旧结果。
4. 两处**无需改**（易误改）：
   - test_package 的 `self.tested_reference_str`——自动引用被测包（新包名），复刻零改动；
   - CMakeLists 的 `find_package(Boost ...)`——走 `cmake_file_name` 属性，与 conan
     包名解耦，保持底稿原样。

### 修复（最小方案）

按上表五处同步 + 两条预检，然后 `finish <新包名> <版本> built` 生成新 .ci-result.json。

## 场景 B：多会话并行 conan create 的脏缓存三连报错

### 问题

多个 OpenDesk 会话各自 worktree 并行 `conan create` 同一大源码包（boost 145MB 级）时，
任一 create 中断（超时被杀/并发清理）会在 `~/.conan2/p/<hash>/` 留下脏状态（s.dirty
标记 + 半解压源码树）。后续 create 复用该缓存条目时三连报错：

```text
ERROR: Unable to delete source folder. Will be marked as corrupted for deletion
OSError: [Errno 39] Directory not empty: '.../.conan2/p/xxx/s/...'
AssertionError: Folder '.../.conan2/p/xxx/s' is already dirty
# 或解压到非空目录: ERROR: Exiting with code: 5
```

**这不是配方错误，是 conan 缓存中毒**——错误信息（source folder/dirty）极易误导为
conanfile 问题，实测中有会话因此误判 G2 失败反复调配方。

### 修复（可复制命令）

```bash
conan remove "包名/*" -c                       # 清理该包全部缓存（含损坏条目）
rm -rf ~/.conan2/p/<hash>/s ~/.conan2/p/<hash>/s.dirty   # 残留兜底
# 重跑 conan create；源码 tarball 在 download cache，无需重新下载
```

注意：`conan remove` 对多份大缓存副本删除需 3-5 分钟，**期间勿再启动新 create**
（会再撞损坏条目）；remove 卡死可直删 `~/.conan2/p/<hash>/` 整目录。

## 复用面

- 场景 A：任何"改名复刻已有归档"任务——积分赛双包名场景、版本线拆包（openssl-X 式）、
  组件包系列共用基座包名。boost1.84 本体与其组件包系列（boost1.84-date_time/
  log_setup/url/serialization/contract）即本模式实例族；组件包
  `self.requires("boost1.84/1.84.0")` 的引用方式是方法论的下游组成。
- 场景 B：所有多会话并行适配共享同一 conan cache 的设备，与具体软件无关；本次
  boost1.84 系列并行适配中实际发生（多个兄弟会话同时在跑）并被修复。

## 与现有条目的关系（查重）

| 条目 | 关系 |
|---|---|
| E068 | b2 不兼容是本配方的**上游原因**（为何绕过 b2），本条不重复 |
| E311 | 同为 conan 缓存/源码隔离主题，但 E311 讲 build 期源复制映射（no_copy_source），本条讲 cache 中毒清理，互补不重叠 |
| E478 | 同为"点号"边界，但对象（版本号 vs 包名）与后果（G4 验证跳过 vs WARN）不同 |
| E437 | 最近的"包名≠源码名"先例（qtcore5compat），但它是单包名场景，本条是双包名并行复刻 |
| E998（申报中，math 组件拆分） | 主题不同：E998 是组件拆分方法论，本条是复刻归档元数据同步 + 环境缓存修复 |

## 验证

- W3 本地 CI 模拟通过（.ci-result.json exit_code=0，integrity_hash=351389224a169a1d）
- conan create 全链路：4 静态库 + 上游测试 15/16（parsers_test rc=-11 与底稿一致）+ test_package 1/1（100% tests passed）
- G1/G2/G3 conan-verify PASS（W4 修复后复验）；pr_lint exit 0；W4 audit verdict=pass（P0/P1 清零）
