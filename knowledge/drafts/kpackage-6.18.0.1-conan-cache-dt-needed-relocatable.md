# DRAFT: Conan cache absolute DT_NEEDED leakage -> relocatable SONAME/link repair

> Contributor: pc1-34 (kpackage 6.18.0.1 R05) | Status: Draft | Updated: 2026-08-28
> Source: kpackage 6.18.0.1 R05 可重定位消费闭合（conan cache 绝对 DT_NEEDED 泄漏修复）

## 现象

KDE Frameworks 6（KF6）依赖库（如 kcoreaddons / karchive / ki18n）发布时**没有 DT_SONAME**。
下游库（如 `libKF6Package.so`）链接这些依赖时，CMake 将依赖的 **Conan 缓存绝对路径**
（`IMPORTED_LOCATION`，形如 `/storage/Users/currentUser/.conan2/p/...` 或更早的
`/storage/Users/currentUser/.cache/conan2/p/...`）传给链接器。由于依赖库无 SONAME，ld
把该机器私有绝对路径直接写入产物的 `DT_NEEDED`：

```text
NEEDED [/storage/Users/currentUser/.cache/conan2/p/kcore…/libKF6CoreAddons.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/karch…/libKF6Archive.so]
NEEDED [/storage/Users/currentUser/.cache/conan2/p/ki18n…/libKF6I18n.so]
```

在缓存布局不同的消费者机器上，该绝对路径不存在，加载器无法解析依赖 → 已发布制品不可消费。
事后用 `patchelf` 改写 ELF 可移除这些路径，但 OHOS HMDFS 缓存文件系统在运行时拒绝
patchelf 改写后的文件（`Permission denied` / `mmap PROT_EXEC`），因此修复必须发生在**链接期**。

## 根因（跨库模式）

- 依赖库无 `DT_SONAME` → 其 CMake 导入目标带 `IMPORTED_NO_SONAME(TRUE)`（及 per-config
  `IMPORTED_NO_SONAME_RELEASE TRUE`）。
- 链接时以绝对路径传参 → ld 在依赖无 SONAME 时记录"命令行给出的路径"（绝对路径）。
- 结果：`DT_NEEDED` 含机器私有缓存路径，跨缓存布局不可重定位。
- 事后改写修复在 HMDFS 上不可运行（patchelf 改写文件被拒绝 mmap PROT_EXEC）。

## 方案（链接期，1 级推荐）

1. 在依赖导入目标上清除 `IMPORTED_NO_SONAME`/`IMPORTED_NO_SONAME_RELEASE` 并设置
   `IMPORTED_SONAME`，让 CMake 以 `-L<dir> -l:libKF6CoreAddons.so` 形式链接；
2. 或更稳健：`target_link_directories(KF6Package PUBLIC ${KPACKAGE_DEP_LIB_DIRS})` +
   以裸 `-lKF6CoreAddons` / `-lKF6Archive` / `-lKF6I18n` 链接，并显式补回 `Qt6::Core`
   （其自带 SONAME，不引入私有路径）以保留 Qt 运行时链接，同时把依赖目标的
   `INTERFACE_INCLUDE_DIRECTORIES`（含 Qt6::Core include）复制回本目标，保持头文件可用；
3. 产物用 `-Wl,-soname,libKF6Package.so` 打稳定 SONAME。

### 验证

```bash
readelf -d bin/libKF6Package.so | grep -E 'NEEDED|SONAME'
# 期望：NEEDED 全为 SONAME 形式（libKF6CoreAddons.so 等），无 `.conan2`/`.cache` 绝对路径，
# SONAME=libKF6Package.so；独立消费者（不同 Conan cache 布局）可编译/链接/加载 KPackage。
```

实测（R05 worker 重建）：`libKF6Package.so` 的 NEEDED 全部为
`libKF6CoreAddons.so / libKF6Archive.so / libKF6I18n.so / libQt6Core.so.6`，
SONAME=libKF6Package.so，sha256 已记录；独立缓存布局下消费者 `consumer_r05` 运行
`consumer loaded: valid`（exit 0，日志 + SHA-256 可追溯）。

## 适用边界

- 适用：任何链接"无 SONAME 导入共享库"的 Conan 包；KF6（kpackage 及其链接
  kcoreaddons/karchive/ki18n 的下游）与类似 Conan 生态。
- 不适用：不要在 HMDFS 上以 patchelf 改写后的 .so 作为发布制品（运行时被拒）。

## 与现有知识的关系

本仓并无 `dependency-package-consumability.kv/.md` 基线条目可作 prior art（已核验：
worktree `git ls-files` 与分析端数据目录均无该文件）；本 DRAFT 作为独立的跨库
模式草稿提出，待人工审核后决定并入正式条目或扩展相关 E 编号。未伪造既有引用。