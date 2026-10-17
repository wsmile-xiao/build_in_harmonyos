# 已发布版本的适配修复重出（dot-revision）须恢复基础配方曾有的平台修复

- **草稿 ID**: DRAFT-fontconfig-2.18.3.2-downstream-revision-must-restore-signing-and-backend
- **来源**: fontconfig/2.18.3.2 适配修复重出（任务 14245）
- **分类**: ohos / c / abi / shared-library / meson / version-bump / signing
- **状态**: 草稿（随 PR 提交，待审核）

## 问题 / 错误签名

- OHOS 侧 `dlopen libfontconfig.so` 报 `Permission denied`（`.codesign` 段失效）。
- `readelf -d libfontconfig.so` 的 `DT_NEEDED` 出现**绝对路径**，如
  `/…/.conan2/p/…/lib/libexpat.so` 或 `/storage/…/libexpat.so` —— 产物不可重定位，
  换 worker / 清 cache 后报 `Error loading shared library` 与一串 `XML_* symbol not found`。
- 构建期误跑 aarch64 `fc-cache`（缺 `cache-build=disabled`）。

## 根因

对**已发布**的上游版本创建适配修复修订（`X.Y.Z → X.Y.Z.n`）时，若直接以更简的
**上游基础配方**（`fontconfig/2.18.3`）为准，会丢掉此前 dot-revision
（`fontconfig/2.18.1.1`）已验证确立的两项平台修复：

1. **重签缺失**：`package()` 没有 `_sign_shared_libs()`。`meson install` 重写 rpath 会改动
   链接后的 `.so`，使链接器自签失效，OHOS XPM `dlopen` 报 `Permission denied`。
2. **XML 后端回归**：`2.18.3` 声明 `libxml2` 却未设 `xml-backend`，meson 自动探测到**系统 expat**，
   链接期把 expat 的绝对路径写进本包 `DT_NEEDED`（`2.18.1.1` 已修复过的同源问题回归）。
   修复须改用**有 SONAME 的** `expat/2.8.2.1` + 显式 `-Dxml-backend=expat`。
3. 附带：`2.18.3` 在 `build()` 里以 `os.environ["AR"]/["PATH"]` 硬编码（R33 违规），
   且缺 `doc/nls/tests/tools/cache-build=disabled`。

## 最小修复方案

在 `archives/f/fontconfig/2.18.3.2/**` 范围内，以最近一次验证通过的 dot-revision
（`fontconfig/2.18.1.1`）为基线重建配方，而非照抄 `2.18.3`：

1. `package()` 后调用 `_sign_shared_libs()`：`llvm-objcopy --remove-section .codesign` 剥旧签，
   再 `binary-sign-tool -selfSign 1` 重签。
2. `generate()`：`xml-backend=expat`，`requirements()` 用 `expat/2.8.2.1`（有 SONAME）；
   `doc/nls/tests/cache-build=disabled`，并按包级 `commands.json`（type=tool）以
   `tools=enabled` 交付 CLI、`package_info` 声明 `bindirs=["bin"]`。
3. 从 `tools.build:compiler_executables` 推导 `llvm-ar`/`llvm-ranlib` 全路径并注入
   `conan_meson_native.ini` 的 `[binaries]`（替代硬编码 `os.environ`）。
4. `test_package` 由“仅查文件存在”改回 `dlopen` 实测断言（签名有效性的可观测判据）。

## 验收判据

- `readelf -d <pkg>/lib/libfontconfig.so | grep NEEDED` 全为 SONAME
  （`libexpat.so.1` / `libfreetype.so.6` / `libc.so`），无绝对路径。
- OHOS 侧 `dlopen libfontconfig.so` 成功（`test_package` exit 0）。
