# DRAFT: MyGUI 3.4.4 Dummy 后端资源注册与无头可验证路径（Path B）

> **Contributor**: junshi_liu | **Team**: 兰州大学DSLab | **Status**: DRAFT
> **Software**: mygui 3.4.4 | **Gate**: W3/conan-verify/test_package headless
> **Date**: 2026-08-29

## 复用问题（可复用问题）

MyGUI 的 Dummy 渲染后端（`MYGUI_RENDERSYSTEM=1`）在 OHOS/HarmonyOS PC 无头环境下：
`addResourceLocation` 为空实现、`getData`/`getDataPath`/`isDataExist`/`getDataListNames`
全部返回空，导致 `ResourceManager::load` 找不到 `MyGUI_Core.xml` 等资源；且其
`DataStream::read()` 返回 `min(size(), _count)` 而非实际读取字节，EOF 后仍返回非 0，
按标准 istream read-until-0 循环读取会无限自旋（CPU 忙循环），在 worker 下被 SIGKILL
（Conan Error 137）。

## error_signature

```
MyGUI_Core.xml not found|addResourceLocation|DummyDataManager|getDataPath
DataStream::read|min\(size\(\), _count\)|Error 137 while executing|Signal 9
data not found|ResourceManager|load resource
```

## root_cause

1. **资源注册缺失**：Dummy 后端 `DummyPlatform/BaseManager::addResourceLocation` 为空、
   `DummyDataManager` 五个 DataManager 虚接口全空返回（上游 Dummy 定位为"无资源"占位），
   与 OpenGL/OpenGLES 后端真实扫描 `mPaths` 的契约不一致。
2. **DataStream 契约陷阱**：`DataStream::read()` 返回 `std::min(size(), _count)`（忽略
   `gcount()`），EOF 后仍返回 size() 非 0；消费方按 `while ((n=read(buf, len)) > 0)` 读取
   会在 EOF 后无限自旋（busy-loop），进程占满 CPU 后被调度层 SIGKILL（Conan Error 137）。

## 修复方案（solution）

1. **资源注册（镜像 OpenGL/OpenGLES 契约）**：给 `DummyDataManager` 增加
   `addResourceLocation(_name, _recursive)` 入 `mPaths`，并实现 `getData`/`getDataPath`/
   `isDataExist`/`getDataListNames` 真实文件解析（`common::scanFolder` 递归 + mask）；
   `BaseManager::addResourceLocation` 接线 `mPlatform->getDataManagerPtr()->addResourceLocation`。
   落盘：`patches/0002-dummy-resource-registration.patch`（3 文件）。
2. **测试消费适配**：test_headless 的 T3 改为按 `st->size()` 一次读取（适配
   `DataStream::read()` 的 `min(size,_count)` 契约，避免 EOF 忙循环）；T4 递归 mask 用
   basename（`scanFolder` 对每层 `d_name` 做 fnmatch，含 `/` 的 mask 无法匹配单层名字）。

## 验证证据（verification）

- Conan G2/G3/G4 PASS、conan-verify PASS（report sha256 `bcff2903…`/`289d3c86…`）；
- test_mygui PASS；**test_headless 14/14 PASS**（`RESULT 14 passed, 0 failed`，
  conan-create.log sha256 `4c3956da…`，正式 Conan runenv）；
- 修复前实测：test_headless 原 T3 在 EOF 后无限自旋（CPU 82–94%），worker 下 SIGKILL
  Error 137；探针 P3 实证 `read()` EOF 后仍返回 size()；
- 13 个上游 GUI UnitTests 实际运行但 `external_blocked: no_legal_display_context`
  （无合法显示/渲染上下文 SIGSEGV 139，非 passing）；UnitTest_GraphView 为 Ogre 条件
  `NOT_BUILT`（UnitTests/CMakeLists.txt 仅 RENDERSYSTEM=3 时 add_subdirectory）。

## 适用边界（reuse scope）

- 适用于 MyGUI 3.4.x Dummy 后端在无头环境（OHOS PC / CI 无显示）的适配与测试；
- DataStream read 契约陷阱适用于依赖 MyGUI `DataStream::read()` 的所有消费测试；
- 不适用：真实渲染/显示上下文场景（需 OpenGLES=8 后端/XComponent+EGL）、Ogre 条件
  GraphView（`external_blocked`/`NOT_BUILT` 分别保留，不计入通过）。

## 查重差异（duplicate check）

- `knowledge/doc`、`knowledge/graph`、`knowledge/graph/index.tsv` 均无
  MyGUI/Dummy DataManager/addResourceLocation/DataStream EOF/busy-loop/
  no-legal-display-context 条目（查重命令 grep -lriE mygui|dummy|…datastream|…
  no.?legal.?display 三处均空；drafts 无 mygui 草稿）。
- 本草稿为唯一同 stem 对，不占用 E### 正式编号（r16 已证 E215 为 LuaRocks 占用，
  r17 禁止创建/修改 E###.md、E###.kv、index.tsv）。

## 关联交付

- 随 mygui 3.4.4 归档同 PR 交付（标题 `【知识库扩展】`），不另建知识库 PR。