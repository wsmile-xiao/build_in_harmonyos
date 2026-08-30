# DRAFT-ohos-kf6-abs-dt-needed-relocatable-link — KF6 共享库无 DT_SONAME 导致 DT_NEEDED 嵌入绝对 Conan cache 路径

> **候选**: 路径 B 知识库沉淀（knewstuff 6.29.0 R03 / kpackage 6.18.0.1 实证）
> **状态**: DRAFT | **日期**: 2026-08-29 | **入库方式**: 同一 stem 成对 `.kv` + `.md`
> **关联库**: knewstuff / kpackage（KDE Frameworks 6 生态，可复用于其他 OHOS KF6/Qt 库）

## error_signature

```text
readelf -d <artifact> | grep NEEDED
NEEDED [/storage/Users/currentUser/.conan2/p/<short>/p/lib/libKF6CoreAddons.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/<short>/p/lib/libKF6I18n.so]   # 发布机布局
# 或运行时：
Error loading shared library /storage/Users/currentUser/.cache/conan2/...: (needed by <consumer>)
```

### 触发条件

- 消费方通过 CMake **导入目标名**（`KF6::CoreAddons` 等 PUBLIC/INTERFACE 传播，或静态库
  PUBLIC 链接）引用一个**发布时无 DT_SONAME** 的 KF6/共享库。
- 该库位于 Conan 缓存（本机 `.conan2/p/...` 或发布机 `.cache/conan2/p/...`）。
- 换机 / 换 Conan home 布局后，动态加载器按绝对路径查找失败（`Error loading shared library`
  ——绝对 NEEDED 不回退 LD_LIBRARY_PATH）。

## root_cause

KF6 依赖库发布时 ELF 无 `DT_SONAME`（`readelf -d` 无 SONAME 行）。这导致：凡以
“导入目标绝对位置”（IMPORTED_LOCATION）参与链接的路径都会被 ld **原样记入**产物
`DT_NEEDED`；而 CMake 通过目标名引用导入库时传递的正是这个绝对位置。于是产物 DT_NEEDED
出现机器私有绝对路径（`.conan2`/`.cache/conan2`），换环境即损坏——与 kpackage/6.18.0
发布二进制缺陷同根。

补充根因变体：
- 项目内“自有库”按相对/绝对路径链接（如 `../../../bin/libKF6NewStuffCore.so`），
  同样使打包产物不可移植，需显式 SONAME。
- 静态库（`knscore_jobs_static`）的 PUBLIC KF6 依赖会把绝对位置传到最终链接。
- 导出目标的 INTERFACE 放 KF6 依赖目标名会把绝对路径传染给下游消费方。

## solution（CMake/recipe 层）

1. **自有共享库设显式 SONAME**：
   ```cmake
   target_link_options(KF6NewStuffCore PRIVATE "-Wl,-soname,libKF6NewStuffCore.so")
   ```
2. **KF6 依赖改 `-l` 裸名 + 私有 `-L`**（避免导入目标绝对位置）：
   ```cmake
   target_link_directories(<target> PRIVATE ${KNEWSTUFF_DEP_LIB_DIRS})
   target_link_libraries(<target> PRIVATE -lKF6CoreAddons -lKF6I18n ...)
   ```
   `KNEWSTUFF_DEP_LIB_DIRS` 由 `conanfile.py::generate()` 注入各依赖 `package_folder/lib`。
3. **静态库同样改 PRIVATE `-l`**（静态库 PRIVATE 依赖传播到最终链接，记录基名）。
4. **导出 INTERFACE 不放 KF6 依赖**（避免传染绝对路径）；include 由消费方自身提供，或在
   recipe 用 `CMAKE_CXX_STANDARD_INCLUDE_DIRECTORIES` 注入各依赖 `include/KF6/<Module>`
   （KF6 头在 `include/KF6/<Module>/`，仅加 `<pkg>/include` 不够）。
5. **为 -l 提供 -L**：`CMAKE_EXE/SHARED_LINKER_FLAGS=-L<dep libs>`；QtQuick 插件（MODULE）
   还需 `CMAKE_MODULE_LINKER_FLAGS`。
6. **全产物 `readelf -d` 扫描**确认无绝对/相对 NEEDED + **真实消费方（test_package）
   链接并运行**验证可重定位。
7. **禁用 `patchelf --replace-needed` 后处理**：本环境 patchelf 0.15.5 实测会破坏
   `.gnu.hash/.hash` 符号解析（`Error relocating ...: symbol not found`）。

## verification（knewstuff 6.29.0 R03 实证）

- 全产物扫描：`readelf -d` → `NO absolute/relative NEEDED entries in any artifact`
  （前后对比：`reports/absolute-path-r03-before.md` → `reports/absolute-path-r03-after.md`）。
- 消费方验证：test_package 完成 configure/compile/link/run（ctest 1/1 + 直接运行
  `PASS: KNewStuffCore Entry API smoke test`）；打包 `knewstuff-dialog6 --help`
  在 OHOS 运行时执行成功（RC=0）；上游 CTest 4/4。
- 补丁：`patches/0004-ohos-relocatable-soname-link.patch`（4 文件：core/widgets/qtquick/dialog）。
- 先例：`kpackage/6.18.0.1` 的 `libKF6Package.so`（SONAME 修复后发布；
  `readelf -d` NEEDED 全为纯 SONAME，R02 消费验证通过）。

## scope / limitations（适用边界）

- **适用**：KF6/KDE Frameworks / 其他“发布时无 DT_SONAME 共享库”在 OHOS/Conan 下打包；
  静态库 + INTERFACE 传递场景；QtQuick MODULE 插件；多库依赖链（karchive/kconfig/
  kcoreaddons/ki18n/kpackage/kwidgetsaddons/attica 等）。
- **已知限制**：
  1) 不能修改已发布依赖库的 SONAME，只能从消费方链接层解决；
  2) `patchelf --replace-needed` 在本环境禁用（破坏符号表）；
  3) `-l` 裸名若出现在导出 INTERFACE，下游消费方必须自带 `-L`（推荐 INTERFACE 不导出，
     消费方按需 `-l`）；
  4) 不适用于纯静态链接或单二进制分发。
- **与既有条目差异（查重）**：E042（RPATH/patchelf 扩展模块）、E088（musl namespace 忽略
  RUNPATH/LD_LIBRARY_PATH）、E207（同项目相对路径链接）、E274（打包时 SONAME 符号链接缺失）、
  E273/E236（元数据携带构建路径）、E290/E296（SONAME/NEEDED 检查）均不覆盖“发布库无
  SONAME → 目标名链接嵌入绝对 DT_NEEDED + CMake/recipe 层修复 + 消费方验证”这一完整链路。

## evidence_paths

- `/storage/Users/currentUser/junshi_liu/worktrees/pc1-32-knewstuff-6.29.0/archives/k/knewstuff/6.29.0/`
  - `reports/absolute-path-r03-before.md`
  - `reports/absolute-path-r03-after.md`
  - `reports/upstream-tests-ledger.md`
  - `patches/0004-ohos-relocatable-soname-link.patch`
- R03 打包产物目录：`/storage/Users/currentUser/.conan2/p/b/knews0f0e33591aa70/p`
- 先例：`kpackage/6.18.0.1` 包内 `libKF6Package.so`

## 恢复条件 / recovery

出现绝对路径 DT_NEEDED 时：`readelf -d` 定位来源 → 按 solution 1)-5) 逐目标改 `-l` 裸名 +
私有 `-L` + 显式 SONAME → 全产物 readelf 扫描 + 消费方运行验证。禁止用 `--build=missing`
掩盖（不得隐式重建缺失依赖）。