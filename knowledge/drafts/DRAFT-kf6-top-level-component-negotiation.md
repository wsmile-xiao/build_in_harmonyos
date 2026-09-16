# DRAFT-kf6-top-level-component-negotiation：KF6 顶层依赖协商（版本地板放宽 + 缺失组件 OPTIONAL + 消费者目录门控）

> Contributor: AtomCode/oh-executor | Status: Draft | Updated: 2026-09-06
> Source: baloo 26.04.3（upstream frameworks 6.25.0）HarmonyOS PC 适配
> 对应：knowledge/drafts/DRAFT-kf6-top-level-component-negotiation.kv

## 现象

baloo 上游顶层 CMakeLists：

```cmake
set(KF_VERSION "6.25.0")
set(KF_DEP_VERSION "6.25.0")
find_package(Qt6 6.9.0 REQUIRED NO_MODULE COMPONENTS Core DBus Widgets Qml Quick Test)
find_package(KF6 ${KF_DEP_VERSION} REQUIRED COMPONENTS CoreAddons Config DBusAddons I18n IdleTime Solid FileMetaData Crash KIO)
```

在 ohpcd 上直接 configure 失败：KF_DEP_VERSION=6.25.0 高于 ohpcd 已发布 KF 基线下限，
且 KIO 未发布。CI 实测（round-1 authoritative CI 日志）：

```text
-- Could NOT find KF6KIO (missing: KF6KIO_DIR)
-- Could NOT find KF6KIO: found neither KF6KIOConfig.cmake nor kf6kio-config.cmake
-- Found KF6: success (found suitable version "6.14.0", minimum required is "6.14.0") found components: CoreAddons Config I18n Solid FileMetaData Crash missing components: KIO
...
-- The following OPTIONAL packages have not been found:
 * Qt6Qml
 * KF6KIO (required version >= 6.14.0)
```

## 根因

- ohpcd 的 KF6 发布线是混合的：kcoreaddons/kconfig/ki18n 到 6.26.0，但
  solid/kfilemetadata/kcrash 只到 6.14.0（conan list -r ohpcd 实测矩阵）。
- 上游把 `KF_DEP_VERSION` 与 `KF_VERSION` 绑在同一版本号（release scripts 维护），
  没有为"依赖地板"单独设可发布面。
- KIO 整体未发布（`kio/*` 0 匹配），DBusAddons/IdleTime 只在索引服务
  （kded/kioworkers/extractor）等本次被裁剪的消费方使用。
- 若保留 REQUIRED COMPONENTS 里的 KIO，`find_package(KF6 6.25.0 REQUIRED ...)`
  永不通过 → configure 失败。

## 方案

在平台适配补丁（本 run：`patches/0001-relax-kf6-and-qt6-requirements.patch`）里做
三层协商，全部以 CMake 探测结果门控、不硬编码平台名：

1. **版本地板放宽**：
   `set(KF_DEP_VERSION "6.14.0")`（注释：floor lowered to published KF baseline），
   `KF_VERSION`（项目版本）仍为 6.25.0。
2. **组件可选化**：
   ```cmake
   find_package(KF6 ${KF_DEP_VERSION} REQUIRED COMPONENTS CoreAddons Config I18n Solid FileMetaData Crash
                             OPTIONAL_COMPONENTS KIO)
   ```
   DBusAddons/IdleTime 因消费方（kioworkers/kded、file/extractor）不在最小集而被移除
   （带注释）；KIO 改 OPTIONAL_COMPONENTS。
3. **消费者目录门控**（src/CMakeLists.txt）：
   ```cmake
   if (TARGET Qt6::Qml)                     # qml 模块需 qtdeclarative
       add_subdirectory(qml)
   endif()
   if (BUILD_KINOTIFY AND KF6_KIO_FOUND)    # kioworkers 是唯一 KIO 消费者
       add_subdirectory(kioworkers)
   endif()
   ```

Qt6 组件同步裁剪为 `Core DBus Test`（Widgets/Qml/Quick 无使用者）。

## 验证

- `conan list 'kio/*' -r ohpcd` → 0 匹配（KIO 未发布，Builder/Scout 探针）。
- CI 日志：KIO 落入 "OPTIONAL packages have not been found"；
  configure 完成（Configuring done 10.8s）；KF6 各组件以 6.14/6.26 线找到。
- 构建/测试闭环：conan create RC=0；ctest 21/21；test_package 1/1
  （round-1 authoritative CI PASS，日志 build9-aci-round1.log）。

## 与现有知识的关系（查重证据）

- **E487 / E542**（Qt6LinguistTools 消费/发布 provider）：主题是
  `tool_requires` + `Qt6LinguistTools_DIR` + provider 复用父模块制品，不含顶层
  KF6 组件协商。
- **E537**（Conan cache 绝对 DT_NEEDED/SONAME）：链接/打包层，不同主题。
- **kpackage-6.18.0.2-ohos-adaptation-patterns**（drafts）：karchive 传递依赖
  `find_dependency(ZLIB)` 路径注入，属"传递依赖可发现性"，非顶层组件协商。
- **DRAFT-baloo-kf6-ohpcd-cmake-toolchain-cppstd**：同 run 姊妹条目（cppstd 时序）。
- 检索证据：curation-report §5 检索词 B) KIO|kioworkers、I) KF_DEP_VERSION|KF6、
  Auditor §6 独立检索 KF_DEP_VERSION/KIO/OPTIONAL_COMPONENTS → 均 0 命中等价条目
  → gap 成立。

## 适用边界

- 任何顶层 `find_package(KF6 <ver>)` 高于 ohpcd 已发布最低 KF 线、或 REQUIRED
  组件未在 ohpcd 全发布的 KF6/KDE 库（baloo 为首个 KIO 缺席实例）。
- 不适用：无 KF6 顶层依赖的库；组件全部随发布线提供的库（无需可选化）。

## 恢复条件

ohpcd 发布缺失组件（KIO 等）后，可把对应组件从 OPTIONAL 收回 REQUIRED 并去掉目录
门控（保持上游行为）；KF_DEP_VERSION 可随发布线逐步回升。若某库存在无法裁剪的
REQUIRED 组件消费者，按"依赖缺口-部分适配"另行记录，不强行放行。

---
*created: 2026-09-06 · builder/path-update baloo-26.04.3 · evidence round-1 CI + curation/audit*
