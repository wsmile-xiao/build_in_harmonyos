# ECM KDEMetaInfoPlatformCheck 按 metainfo.yaml 平台白名单硬性 FATAL，未收录平台（HarmonyOS/OHOS）须显式设 KF_IGNORE_PLATFORM_CHECK=ON

- 形态：knowledge/drafts 条目草稿（最终编号 Exxx 由知识库主编确认）
- 配套 kv：`knowledge/drafts/DRAFT-kf-metainfo-platform-whitelist-ignore-flag.kv`
- 申报路径：B【知识库扩展】（L2 跨库工程模式层：配方树 113 个 conanfile.py 同模式实践 ≥3 处门槛；阻塞面为真实 configure FATAL 探针）
- 来源 run：libkomparediff2-26.04.0（权威 CI PASS，BUILD_TESTING=ON 上游 2/2 ctest + test_package 1/1）

## 1. 一句规则

ECM 的 `KDEMetaInfoPlatformCheck` 把源码 `metainfo.yaml` 的 `platforms:` 清单
按硬编码映射（Linux/FreeBSD/OpenBSD/Windows/macOS/Android/iOS/All）与
`CMAKE_SYSTEM_NAME` 比对，未收录平台（HarmonyOS/OHOS）直接 `FATAL_ERROR`
终止 configure；应在配方/命令行显式设 `KF_IGNORE_PLATFORM_CHECK=ON`（或同名
环境变量），而不是改 ECM 模块或伪装系统名。

## 2. 机理链（每环有独立可复现证据）

1. **开关面**：`KDEMetaInfoPlatformCheck.cmake:23`
   `option(KF_IGNORE_PLATFORM_CHECK ... OFF)`；`:24-28` 同名环境变量置 ON 亦可
   （触发时打 WARNING "KF_IGNORE_PLATFORM_CHECK set to ON from the environment"）。
2. **白名单解析**：`:32 file(STRINGS metainfo.yaml)` 读源码目录 metainfo.yaml，
   逐行匹配 `name:` 子串并按硬编码平台映射比对（`:39-70`）。探针实证一个解析
   quirk：注释行 `#- name: Android` 也被计入候选清单（`platforms is
   'Linux;FreeBSD;Windows;Android'`，含 WARNING "Found platform not recognized"）。
3. **失败点**：libkomparediff2 26.04.0 的 metainfo.yaml 实际声明
   Linux/FreeBSD/Windows；`CMAKE_SYSTEM_NAME=HarmonyOS`（Conan OHOS profile 映射，
   同 E092 的系统名注入）不命中任何映射 → `:79 FATAL_ERROR "Your current
   platform 'HarmonyOS' is not supported..."`，configure 终止，探针退出码 1。
4. **能力面澄清（态度审计）**：该门禁是上游**发行策略声明**，不是技术能力
   探测——同一设备上 clang/ECM/KF6 全链路可用，libkomparediff2 放行后
   BUILD_TESTING=ON 上游 2/2 ctest + test_package 1/1 全过。因此"开关放行 +
   PR 披露"属于 P-BUILD-001 语义下的合规降级，而非绕过技术限制。

## 3. 推荐修复（配方两行）

```python
# conanfile.py generate() / CMakeToolchain
tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
```

或 `cmake -DKF_IGNORE_PLATFORM_CHECK=ON`、`env KF_IGNORE_PLATFORM_CHECK=ON`。
配方树实测 **113 个 conanfile.py** 同模式（`grep -rl KF_IGNORE_PLATFORM_CHECK
archives --include=conanfile.py`，accessibility、alkimia、akonadi、attica 等），
L2 第二实例远超 ≥3 门槛；官方开关是 producer 无需改动的泛化解法。

## 4. fallback（诚实权衡）

- **`-DCMAKE_SYSTEM_NAME=Linux` 降名**：让白名单命中，但所有平台相关检测
  （Platform 模块加载链、E383 的 SONAME flag 缺失面、系统 API 探测）都会按
  Linux 进行，问题归因难度上升；仅个别上游检测确需"视为 Linux"时局部使用，
  并在 PR 披露伪装面。

## 5. 反模式

1. **改 ECM/KDEMetaInfoPlatformCheck.cmake 或注释掉上游检查**：污染共享
   conan cache（多 run 共享状态）与上游判定面；ECM 升级即丢失；官方开关
   本就是为此场景提供的正解。
2. **只设开关、无真实构建与上游测试证据即宣称已适配**：放行 ≠ 可用；
   证据基线 = 真实构建 + 全量上游测试（本 run 2/2 + 1/1）。

## 6. 去重与关系

- **E092**（CMake 不识别 HarmonyOS 平台）：记录 `System is unknown to cmake,
  create Platform/HarmonyOS` 的**诊断 WARNING**（平台模块缺失面，不终止
  configure、无开关语义）；本条是 ECM/KDE 层的**发行白名单 FATAL 门禁**，
  机理与修复位（KF_IGNORE_PLATFORM_CHECK）均不同。探针日志中两者同现，
  恰好可对照区分。
- **E090**（Meson host_system == 'linux' 不匹配 HarmonyOS）：同属"平台探测
  白名单"族但构建系统不同（Meson vs CMake/ECM）、修复位不同
  （meson host_system vs KF_IGNORE_PLATFORM_CHECK）。
- **E383**（Platform/HarmonyOS.cmake 缺失 → 共享库缺 DT_SONAME）与
  **E537**/`DRAFT-cmake-harmonyos-platform-soname-flag`：同根因（平台模块
  缺失）的**链接语义**后果面；本条与链接语义无关，是 configure 期的声明
  门禁，互补不重复。
- **确认去重证据**：2026-09-14 设备实测——`grep -ril KF_IGNORE_PLATFORM_CHECK
  knowledge/`、`grep -ril KDEMetaInfoPlatformCheck knowledge/` 在
  knowledge/graph（540 条 E*.kv）与 knowledge/drafts（1273 文件）均 **0 命中**；
  平台探测族检索命中 E092/E090/E144/E146/E147/E292/E383/E504/E508，逐项差异
  如上。检索词：KF_IGNORE_PLATFORM_CHECK / KDEMetaInfoPlatformCheck /
  metainfo / platform whitelist。

## 7. 原则挂钩

`P-BUILD-001`（平台限制必须降级而非绕过——本条的开关放行之所以合规，是因
为被放行的是上游声明面且保留了真实能力证据链，属"识别限制类型后选择对应
方案"）；`P-ENV-001`（构建系统语义与环境变量/开关的交互——同名环境变量
与 cmake 变量双入口的语义一致性）。

## 8. 五项质量门槛自检

1. 规则式标题 + 问题类 slug（`kf-metainfo-platform-whitelist-ignore-flag`，
   无库名-版本命名；库名仅进 source_event 当案例）——✔
2. rec + fallback（含诚实权衡）+ 2 条 forbid（reason+consequence）——✔
3. verification_cmd 自包含（printf + 真实 metainfo.yaml + 真实 ECM 模块 +
   双向退出码，新 shell 可跑；不依赖本 run 日志路径，日志仅作归档引用）——✔
4. principles 挂钩（P-BUILD-001/P-ENV-001）、affected_scope 泛化句式、
   similar_to 链 E092/E090/E383——✔
5. 本 run 配额 2/2：本条为主条（L2，113 处第二实例）；
   `DRAFT-kf-skip-po-processing-gettext-toolchain` 为次条——✔
