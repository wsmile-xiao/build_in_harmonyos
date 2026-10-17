# DRAFT-ohos-dt-needed-bare-name-normalization: 消费端配方内 DT_NEEDED 裸名归一化与分级卫生断言

> **Contributor**: GoliWie | **Status**: Draft | **Updated**: 2026-09-18
> **申报域**: 链接（八分类）｜**机理分层**: L2 跨库工程模式（6 配方同模式实例 + 2 run 独立命中）
> **拟提升编号：由知识库主编确认（不自行编号）**

## 规则（一句话）

消费端配方必须在打包期把产物内路径形 DT_NEEDED——兄弟库 `../bin/` 前缀案与 SONAME-less 依赖绝对路径案——等长 NUL 填充改写为裸 basename 并按 E077 重签，再用分级卫生断言（打包库只允许裸名、测试二进制绝对项必须可解析）守护。

## 问题

mauikit 4.0.2 适配首轮权威 CI：编译、链接与 3 项测试全部通过，test_package 的 DT_NEEDED 卫生断言却拦截了测试二进制：`unresolvable DT_NEEDED entries: ['/storage/.../.conan2/p/kcore.../p/lib/libKF6CoreAddons.so']`。检查发现打包库 `libMauiKit4.so` 携带 4 处绝对路径 NEEDED（libKF6CoreAddons/libKF6Notifications/libKF6I18n/libQt6Multimedia），QML 插件再带 1 处——离开本机构建 cache 即整体不可加载。

## 根因（引 E537，不复述）

已发布 kcoreaddons/ki18n/knotifications/qtmultimedia 包的 `.so` **不带 DT_SONAME**（真机 `readelf -d` 实证：SONAME 计数=0），lld 链接时按输入原样记录绝对包路径（机理详见 E537）；兄弟构建库则以 `../bin/` 相对形态进入。musl 对含 `/` 的 NEEDED 按字面路径解析、无搜索回退（DRAFT-musl-relative-soname-downstream-cwd 同族）。**本条只沉淀消费端修复模式**——机理条目以 E537 为准，不重复申报。

## 修复模式（rec）

`package()` 内对自有 `lib/**.so*` 两案归一化，字节级**等长**（新 basename + NUL 填满原串长度，`.dynstr` 原位截断、不移动偏移）；绝对路径案匹配收紧到已知 SONAME-less 家族名（`libKF6*`/`libQt6*`）防误伤；改写后必须重签（`llvm-objcopy --remove-section .codesign` → `binary-sign-tool -selfSign 1`）。配套**分级卫生断言**：

| 对象 | 断言级别 | 语义 |
|---|---|---|
| 打包库（随包分发的制品） | strict | 只允许裸 soname，任何 `/` 条目 fatal |
| 测试二进制（链接自已发布包） | resolved | 绝对项必须 isfile 可解析（cache-root 桥接保证）；相对项（`./`、`../`）任何情况下 fatal |

诚实边界：分级不是放水——分发面 strict 保持不放松（本可整体放宽为"可解析"却未）；只对不随包分发的测试二进制按 musl 加载语义放宽。

## 退路（fallback，含诚实权衡）

1. **依赖侧 SONAME 重建**（治本）：依赖配方补 `-Wl,-soname` 或平台 soname flag（见 DRAFT-cmake-harmonyos-platform-soname-flag；kio patch 0015、accessibility/26.04.3 先例）并重发家族包。权衡：治本但需改依赖配方并全家族重发，消费端单库 run 无法独立完成；重发前消费端仍需 rec 兜底。
2. **cache-root 桥接**（加载面）：为烘焙的 `~/.conan2` 绝对路径在消费端重建 symlink 指向真实 package_folder（kio 6.14.0 test_package `_bridge_cache_roots` 同源；PR worker `~/.cache/conan2` 布局时必需）。权衡：**掩盖而非修复**——产物仍带绝对路径、依赖特定 cache 根布局，仅作测试环境退路，家族 SONAME 重建后移除（kio 同源注释已声明）。

## 反模式（forbid）

1. **改写不重签 / 以"CI 通过"判定改写安全**：签名失配 → dlopen Permission denied（E517；DRAFT-ohos-signed-so-inplace-rewrite-dlopen-denied 判别实验坐实），失败只在运行期暴露。后果：构建机"测试通过"、下游整体不可加载的假阳性交付。
2. **断言整体放宽为"当前构建机可解析即可"**：绝对项指向本机 cache 布局是巧合，换机即失效；与 build-chain-pitfalls「lld 隐式闭包静默跳过」同型。后果：同一配方在不同 worker 上结论相反，问题延后到下游运行期。

## 验证（自包含探针）

见同名 .kv `verification_cmd`：① 已发布 libKF6CoreAddons.so 无 SONAME（`grep -c '(SONAME)'` = 0）；② 未归一化消费产物含 `.conan2` 路径形 NEEDED；③ `grep -rln '_normalize_ohos_needed_names' archives/ | wc -l` = 6（L2 门槛 ≥3：kirigami/6.18.0、kiconthemes/6.18.0.1、kiconthemes/6.26.0、kjobwidgets/6.18.0、kirigami-addons/1.13.0、mauikit/4.0.2）；④ 归一化后打包产物无路径形 NEEDED；⑤ 改写未重签负判别 dlopen Permission denied。

本 run 闭环证据：归一化 4+1 处后，attempt2 全过——L0/L1/L2/L4/L5 pass，ctest 3/3（meta_objects/ohos_defaults/qml_module），打包库 hygiene strict 15 项全裸名、测试二进制 resolved 10 项全可解析。

## 去重记录（与相近条目划界）

- **E537**：机理 + 生产侧 link-time 修复（IMPORTED_SONAME/target_link_directories）。本条 = **消费端配方守卫模式与断言分级**，不含其机理叙事，互补不重复。
- **E077**：post-install 四步重签流程。本条把它作为 rec 的收尾环节引用，不重复其流程定义。
- **E517 / DRAFT-ohos-signed-so-inplace-rewrite-dlopen-denied**：改写不重签的反模式与判别实验。本条 forbid_1 引用之，增量在消费端归一化的完整模式。
- **E505**：加载器路径优先级（LD_LIBRARY_PATH vs DT_RPATH）。邻接加载语义，非本条模式。
- **DRAFT-cmake-harmonyos-platform-soname-flag**：生产侧 soname flag。本条 fallback_1 引用，方向相反（生产侧 vs 消费侧）。
- **DRAFT-musl-relative-soname-downstream-cwd**：relative-soname（`./` 前缀）下游消费陷阱。同族不同案（其案为依赖打相对 soname，本条为无 soname 烘绝对路径 + 兄弟库相对前缀），共用"musl 含 / NEEDED 无回退"前提。
- 检索复核：`grep '_normalize_ohos_needed_names|NUL-padd|NUL padding' knowledge/` = 0 命中（模式未被图收录）；pre-scan-rules.yaml 无 NEEDED/SONAME 规则（走 kv 形态）。

## 关系

similar_to: E537, E077, E517, E505, DRAFT-ohos-signed-so-inplace-rewrite-dlopen-denied, DRAFT-cmake-harmonyos-platform-soname-flag, DRAFT-musl-relative-soname-downstream-cwd, DRAFT-ohos-dlopen-own-dt-needed-closure
principles: P-SIGN-001, P-PACK-001, P-RUNTIME-002
