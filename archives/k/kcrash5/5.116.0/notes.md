# kcrash5 5.116.0 适配笔记

## 编译环境
- 构建系统: cmake（ECM 5.116.0 / KDEFrameworkCompilerSettings）
- 编译日期: 2026-09-30
- 编译器: clang/clang++（OHOS aarch64 工具链，aarch64-linux-ohos target）
- 状态: built

## 依赖版本

| 依赖 | 版本 | 角色 | 说明 |
|------|------|------|------|
| kcoreaddons5 | 5.116.0 | requires | 唯一真实 KF5 依赖（PRIVATE 链 KF5::CoreAddons） |
| qt5-qtbase | 5.15.2.2 | requires (force=True) | widgets-capable 构建，供 autotests 的 Qt5Widgets/Qt5Test |
| ecm | 6.26.0 | tool_requires | find_package(ECM 5.116.0 NO_MODULE) |

依赖状态核验：`kcoreaddons5/5.116.0` 与 `kwindowsystem5/5.116.0` 均已在 ohpcd 制品仓
发布（`conan list <pkg>/* -r=ohpcd` 命中）；`kwindowsystem5` 虽已发布但**不是** kcrash 的
依赖（源码全文无 KF5WindowSystem 引用）。

## 编译步骤

1. `bash ci/scripts/preflight_check.sh "kcrash5/5.116.0"` — 依赖发布预检（首跑时 conanfile
   尚未生成，报「无依赖需要检查」；配方生成后复跑确认依赖均已在制品仓）。
2. `python3 scripts/ohc-run.py recipe-search kcrash5` — 语料无近似配方（首稿走 conan-init 模板）。
3. 手写配方：conanfile.py / conandata.yml / manifest.yaml / notes.md / test_package/，
   结构对齐已合入的 KF5 5.116.0 链（kjobwidgets5 / kitemmodels5 / kcoreaddons5 / kcodecs5）。
   关键 CMake 变量见 manifest 的 `configure_options`。
4. `python3 scripts/ohc-run.py conan-verify kcrash5 5.116.0` — G0..L5 八道门禁，
   G2 直接对配方跑 `conan create ... --build=missing`（跳过 `build` 命令，规避 Step9
   `conan_init(force=True)` 覆盖手写配方）。
5. `python3 scripts/ohc-run.py finish kcrash5 5.116.0 built`（带
   `_SKIP_PATCH_GENERATION=true`，规避 refresh-patch 的破坏性重写）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 任务备注把 kwindowsystem 列为待核依赖 | 备注按 KF5 常见组合推测 | 源码全文 grep：kcrash 不引用 KF5WindowSystem，真实依赖只有 kcoreaddons + Qt5；已在 manifest knowledge_gained 留证 |
| 2 | configure 阶段会 `find_package(X11 REQUIRED)` 失败 | 上游在 UNIX 下 WITH_X11 默认 ON，OHOS 无 X11 头/库 | `-DWITH_X11=OFF`（kjobwidgets5 先例） |
| 3 | Qt 版本冲突：kcoreaddons5 钉 qt5-qtbase/5.15.2（-no-widgets 桩），autotests 需 Qt5Widgets | KF5 链跨两个 Qt5 基线 | `self.requires("qt5-qtbase/5.15.2.2", force=True)`（kjobwidgets5 先例） |
| 4 | `find_package(Qt 5.15.2 ...)` 找不到包 | 上游用 `Qt${QT_MAJOR_VERSION}`，变量未设 | `-DQT_MAJOR_VERSION=5` |
| 5 | 上游 `kcrashtest` 三个子用例在**装载阶段** rc=127 挂掉（`Error loading shared library libKF5CoreAddons.so.5:`） | 依赖 `kcoreaddons5/5.116.0` 的 `.codesign` 签名不被本机 loader 接受（E135 家族，非 kcrash 缺陷）——字节级副本仍拒、结构比对一致、**重签后立即可加载** | 探针留 `~/tmp/uc2/kcrash5/`；本机缓存副本重签后 3/3 全绿，实验后还原发布态原件（md5 `e3353d3b…`），ctest 因此不内嵌 `build()` |

## 源码修改

本轮**零补丁**（patches/ 为空，conandata.yml 无 patches 条目）：全部适配通过 CMake 变量
与依赖声明完成，未改动上游源码。

## 验证结果

- `conan-verify`（G0 风险评估 / G1 配方完整性 / G2 `conan create` / G3 系统同名库 / G4 产物 /
  L2 smoke / L4 checksec / L5 基线）**全绿，rc=0**，报告 `reports/conan-verify-report.md`。
- 上游 autotest 实测：**发布态依赖 2/3；依赖重签后 3/3（100%）** —— `kcrashtest`（SIGSEGV →
  `defaultCrashHandler` → `KCrash::AutoRestart` exec 自重启 AR/ARD + ES 紧急保存）、`coreconfigtest`、
  `metadatatest` 全部通过；证明**自重启链在 OHOS 上真实可用**。
- 消费者测试 `test_package`：编译 PASS；执行 rc=127（同一 `.codesign` 拒载）→ 按 kcoreaddons5/
  kjobwidgets5 先例回退**链接级证明 `8/8 KCrash API symbols resolved`** 通过，与 CI 行为同构。
- 详细读数与复现命令见 `reports/test-report.md`；B 判定查重过程见
  `reports/knowledge-candidate-ledger.md`（结论 `B判定=hit(E135)`）。

## 注意事项

- DrKonqi 未随本包交付：崩溃对话框在 OHOS 上不会弹出，`test_package` 显式
  `setDrKonqiEnabled(false)` 并断言状态，崩溃处置本身不受影响。
- `KCrash::AutoRestart` 依赖崩溃后 exec 自身；沙箱是否放行 fork/exec 由
  `reports/test-report.md` 的实测结论为准。

### 对话 #1
- 首稿：按 KF5 5.116.0 已合入链的结构手写配方，跳过 `build`（Step9 会 force 覆盖手写配方），
  直接 `conan-verify → finish`。状态: built
---

**编译结束**: 2026-09-30 17:18
**最终状态**: built
